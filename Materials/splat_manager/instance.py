# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""One loaded Splat: its data, its GPU resources, and its own depth sort.

Everything that used to be a module global lives on an instance, which is what
lets any number of Splats coexist. Two instances share nothing but the shader
program, so importing one can never disturb another - including one that is
mid-training.
"""

import math
import threading

from . import data
from . import shaders


class SplatInstance:
    """A single Splat set, drawn under its own root Empty."""

    def __init__(self, splat_id, name=""):
        self.splat_id = str(splat_id)
        self.name = name or self.splat_id
        self.source_path = ""

        self.packed = None
        self.positions = None
        self.count = 0
        self.stride = 0
        self.sh_degree = 0
        self.minimum = None
        self.maximum = None

        self._data_texture = None
        self._indices_texture = None
        self._data_dirty = True

        #: The point cloud keeps both colourings so switching between its own
        #: colours and the coverage read-out never re-reads the file.
        self.true_colour_sh = None
        self.coverage_sh = None

        # Each instance sorts on its own thread, so a large Splat re-sorting
        # never blocks a small one from drawing.
        self._sort_lock = threading.Lock()
        self._sort_thread = None
        self._sort_ready = None
        self._last_sort_matrix = None
        self.error = ""

    # ------------------------------------------------------------------ data

    def set_arrays(self, positions, scales, quaternions, opacities, sh, np):
        """Replace this instance's Splats. Safe to call while it is drawing."""
        positions, scales, quaternions, opacities, sh = data.validate(
            positions, scales, quaternions, opacities, sh, np
        )
        packed, stride, degree = data.pack(
            positions, scales, quaternions, opacities, sh, np
        )
        self.packed = packed
        self.positions = positions
        self.count = int(positions.shape[0])
        self.stride = int(stride)
        self.sh_degree = int(degree)
        self.minimum, self.maximum = data.bounds(positions, np)
        self._data_dirty = True
        # The previous order indexes Splats that may no longer exist.
        self._indices_texture = None
        self._last_sort_matrix = None
        with self._sort_lock:
            self._sort_ready = None
        self.error = ""

    def is_loaded(self):
        return self.packed is not None and self.count > 0

    def replace_colours(self, sh, np):
        """Recolour in place, leaving positions and the depth order alone."""
        if self.packed is None:
            return
        sh = np.asarray(sh, dtype=np.float32)
        coefficients = (self.stride - data.HEADER_FLOATS) // 3
        if sh.shape[0] != self.count or sh.shape[1] < 1:
            return
        view = self.packed.reshape(self.count, self.stride)
        view[:, data.HEADER_FLOATS:data.HEADER_FLOATS + 3] = sh[:, 0, :]
        if coefficients > 1:
            view[:, data.HEADER_FLOATS + 3:] = 0.0
        self._data_dirty = True

    def centre_world(self, matrix_world):
        """The middle of this Splat's bounds, in world space.

        Used to order overlapping Splats against each other; the per-Gaussian
        order inside one Splat is handled separately.
        """
        from mathutils import Vector

        if self.minimum is None or self.maximum is None:
            return matrix_world.translation.copy()
        local = Vector(
            (
                (float(self.minimum[0]) + float(self.maximum[0])) * 0.5,
                (float(self.minimum[1]) + float(self.maximum[1])) * 0.5,
                (float(self.minimum[2]) + float(self.maximum[2])) * 0.5,
            )
        )
        return matrix_world @ local

    # ------------------------------------------------------------------- gpu

    def _buffer(self, gpu, values):
        try:
            return gpu.types.Buffer("FLOAT", len(values), values)
        except (TypeError, ValueError):
            return gpu.types.Buffer("FLOAT", len(values), values.tolist())

    def ensure_data_texture(self):
        if self.packed is None:
            return None
        if self._data_texture is not None and not self._data_dirty:
            return self._data_texture

        import gpu
        import numpy as np

        texels = int(math.ceil(self.packed.size / 4.0))
        width = min(16_384, max(1, texels))
        height = max(1, int(math.ceil(texels / width)))
        required = width * height * 4
        flattened = self.packed
        if flattened.size < required:
            padded = np.zeros(required, dtype=np.float32)
            padded[: flattened.size] = flattened
            flattened = padded
        self._data_texture = gpu.types.GPUTexture(
            (width, height), format="RGBA32F", data=self._buffer(gpu, flattened)
        )
        self._data_dirty = False
        return self._data_texture

    # ------------------------------------------------------------- depth sort

    @staticmethod
    def _compute_order(positions, matrix, np):
        """Back-to-front index order. Pure numpy, so it is thread-safe."""
        depths = positions @ matrix[2, :3] + matrix[2, 3]
        order = np.argsort(depths).astype(np.float32, copy=False)
        width = min(16_384, max(1, len(order)))
        height = max(1, int(math.ceil(len(order) / width)))
        required = width * height
        if order.size < required:
            padded = np.zeros(required, dtype=np.float32)
            padded[: order.size] = order
            order = padded
        return order, width, height

    def _upload_order(self, order, width, height):
        import gpu

        self._indices_texture = gpu.types.GPUTexture(
            (width, height), format="R32F", data=self._buffer(gpu, order)
        )

    def _sort_worker(self, positions, matrix, np, redraw):
        try:
            result = self._compute_order(positions, matrix, np)
        except Exception:
            result = None
        with self._sort_lock:
            if result is not None:
                self._sort_ready = (result, matrix)
            self._sort_thread = None
        redraw()

    def update_order(self, model_view_matrix, redraw):
        """Keep the back-to-front order fresh without stalling the viewport.

        Sorting millions of Splats inside the draw handler freezes Blender on
        every camera move, so it runs on a worker thread and the result is
        uploaded when it lands. A re-sort starts as soon as the view has moved
        at all; the thread is what keeps that cheap.
        """
        if self.positions is None:
            return

        import numpy as np

        current = np.asarray(
            [tuple(row) for row in model_view_matrix], dtype=np.float32
        )

        with self._sort_lock:
            ready = self._sort_ready
            self._sort_ready = None
        if ready is not None:
            (order, width, height), matrix = ready
            self._upload_order(order, width, height)
            self._last_sort_matrix = matrix

        # The first order has to be synchronous or nothing draws at all.
        if self._indices_texture is None:
            order, width, height = self._compute_order(
                self.positions, current, np
            )
            self._upload_order(order, width, height)
            self._last_sort_matrix = current
            return

        # Only skip when the view has genuinely not moved; the threshold is
        # float noise, not a performance dial.
        if (
            self._last_sort_matrix is not None
            and float(np.max(np.abs(current - self._last_sort_matrix))) < 1.0e-4
        ):
            return

        with self._sort_lock:
            if self._sort_thread is not None:
                # One is already running; the next redraw supersedes it.
                return
            self._sort_thread = threading.Thread(
                target=self._sort_worker,
                args=(self.positions, current, np, redraw),
                daemon=True,
            )
            self._sort_thread.start()

    # ----------------------------------------------------------------- draw

    def draw(self, model_view_matrix, projection_matrix, viewport, settings, redraw):
        """Draw this Splat with its own settings. Returns True if it drew."""
        if not self.is_loaded():
            return False

        import gpu

        texture = self.ensure_data_texture()
        if texture is None:
            return False
        self.update_order(model_view_matrix, redraw)
        if self._indices_texture is None:
            return False

        shader, batch = shaders.get()
        camera_local = model_view_matrix.inverted_safe().translation
        mode = shaders.MODE_VALUES.get(
            settings.get("mode", "GAUSSIAN"), shaders.MODE_GAUSSIAN
        )
        degree = min(self.sh_degree, int(settings.get("sh_degree", 3)))

        shader.bind()
        shader.uniform_float("ModelViewMatrix", model_view_matrix)
        shader.uniform_float("ProjectionMatrix", projection_matrix)
        shader.uniform_float("camera_local", camera_local)
        shader.uniform_float("viewport", viewport)
        shader.uniform_float("splat_scale", float(settings.get("scale", 1.0)))
        shader.uniform_float("point_size", float(settings.get("point_size", 3.0)))
        shader.uniform_float("ring_width", float(settings.get("ring_width", 0.35)))
        shader.uniform_int("splat_stride", self.stride)
        shader.uniform_int("sh_degree", max(0, degree))
        shader.uniform_int("render_mode", mode)
        shader.uniform_sampler("gaussian_data", texture)
        shader.uniform_sampler("sorted_indices", self._indices_texture)
        batch.draw_instanced(shader, instance_count=self.count)
        return True

    # ---------------------------------------------------------------- teardown

    def free(self):
        """Drop GPU resources. The sort thread is a daemon and ends on its own."""
        self._data_texture = None
        self._indices_texture = None
        self.packed = None
        self.positions = None
        self.count = 0
        with self._sort_lock:
            self._sort_ready = None
