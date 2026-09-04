# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Checking camera coverage before committing to a build.

A quick, coarse ray cast from every camera in the list, voxelised and coloured
by how many cameras can see each region. It answers one question - *is this
camera setup enough?* - in seconds rather than after a full dataset build.

This is deliberately not the training point cloud. It trades reconstruction
quality for speed: a few hundred rays per camera, snapped to a grid, kept only
as a coverage read-out. Nothing it produces is ever used for training.
"""

import time

import bpy
from bpy.types import Operator

#: Rays per camera along each axis. 24x24 is ~576 casts per camera: coarse
#: enough to stay instant on a large rig, dense enough to expose a gap.
GRID = 24

#: A voxel seen by this many cameras or more counts as well covered.
GOOD_COVERAGE = 3

#: Set by the Stop button beside the progress bar; the modal reads it on its
#: next tick. A flag rather than a direct call, because the operator instance
#: is not reachable from a panel.
_cancel = {"requested": False}


def request_cancel():
    """Ask a running coverage validation to stop at its next step."""
    _cancel["requested"] = True


def _camera_rays(camera, scene, grid):
    """Ray origins and directions across one camera's frustum."""
    frame = camera.data.view_frame(scene=scene)
    matrix = camera.matrix_world
    origin = matrix.translation
    top_right, bottom_right, bottom_left, top_left = frame
    for row in range(grid):
        v = (row + 0.5) / grid
        for column in range(grid):
            u = (column + 0.5) / grid
            top = top_left.lerp(top_right, u)
            bottom = bottom_left.lerp(bottom_right, u)
            local = bottom.lerp(top, v)
            world = matrix @ local
            direction = world - origin
            if direction.length_squared <= 0.0:
                continue
            yield origin, direction.normalized()


def _merge(hits, camera_count, per_camera, np):
    """Snap accumulated hits to a grid and count the cameras that saw each."""
    points = np.asarray([tuple(point) for point in hits], dtype=np.float64)
    owners = list(hits.values())

    # Snap to a grid so hits from different cameras on the same surface become
    # the same sample. The cell is sized from the scene, not hard-coded, so it
    # behaves the same on a tabletop capture and a building.
    extent = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    cell = max(extent / 128.0, 1.0e-6)
    keys = np.floor(points / cell).astype(np.int64)

    merged = {}
    for row, cameras_seen in zip(map(tuple, keys), owners):
        merged.setdefault(row, [np.zeros(3), 0, set()])
        entry = merged[row]
        entry[1] += 1
        entry[2].update(cameras_seen)
    for row, point in zip(map(tuple, keys), points):
        merged[row][0] += point

    positions = np.empty((len(merged), 3), dtype=np.float32)
    counts = np.empty(len(merged), dtype=np.int32)
    for index, entry in enumerate(merged.values()):
        positions[index] = entry[0] / max(1, entry[1])
        counts[index] = len(entry[2])

    stats = {
        "cameras": camera_count,
        "rays": int(sum(found for _name, found in per_camera)),
        "samples": int(positions.shape[0]),
        "weak": int((counts < GOOD_COVERAGE).sum()),
        "unseen": [name for name, found in per_camera if found == 0],
        "per_camera": per_camera,
    }
    return positions, counts, stats


def coverage_colours(counts, np):
    """Three unmistakable bands: poor red, intermediate orange, good green."""
    colours = np.empty((counts.shape[0], 3), dtype=np.float32)
    colours[:] = (1.0, 0.05, 0.02)
    intermediate = (counts > 1) & (counts < GOOD_COVERAGE)
    colours[intermediate] = (1.0, 0.35, 0.02)
    colours[counts >= GOOD_COVERAGE] = (0.05, 0.85, 0.08)
    return colours


def cast_one_camera(context, camera, hits, index, grid=GRID, visible=None):
    """Ray-cast a single camera into the shared hit table.

    Casts into the render-visible BVH rather than the live scene: hidden and
    render-disabled geometry is absent from it, so it can neither be hit nor
    occlude what is behind it, and each ray costs one cast instead of walking
    past unwanted hits.
    """
    from . import raycast

    scene = context.scene
    if visible is None:
        visible = raycast.build(context)
    if visible.is_empty:
        return 0
    found = 0
    for origin, direction in _camera_rays(camera, scene, grid):
        location, _normal, _index, _distance = visible.ray_cast(
            origin, direction
        )
        if location is None:
            continue
        found += 1
        hits.setdefault(location.copy().freeze(), set()).add(index)
    return found


def merge_hits(hits, camera_count, per_camera):
    """Voxelise the accumulated hits into positions and coverage counts."""
    import numpy as np

    if not hits:
        return None, None, {
            "cameras": camera_count, "rays": 0, "per_camera": per_camera,
            "samples": 0, "weak": 0,
            "unseen": [name for name, found in per_camera if found == 0],
        }
    return _merge(hits, camera_count, per_camera, np)


class SPLATRAY_OT_validate_coverage(Operator):
    """Ray-cast every camera to preview coverage before building the dataset"""

    bl_idname = "splatray.validate_coverage"
    bl_label = "Validate Camera Coverage"
    bl_description = (
        "Cast a quick grid of rays from every camera in the list and show "
        "which parts of the scene they cover. Poor coverage is red, "
        "intermediate coverage is orange, and good coverage is green. "
        "For validation only - it is not used for training"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        from .. import sceneray_splat

        cfg = getattr(context.scene, "SCENERAY_SPLAT", None)
        return (
            cfg is not None
            and not (cfg.is_rendering or cfg.is_generating_points)
            and sceneray_splat._sr_has_queued_camera(cfg)
        )

    # ------------------------------------------------------------------ setup

    def _begin(self, context):
        from .. import sceneray_splat
        from .. import progress

        cfg = context.scene.SCENERAY_SPLAT
        self.cameras = [
            item.camera
            for item in cfg.camera_queue
            if item.camera is not None and item.camera.type == "CAMERA"
        ]
        if not self.cameras:
            raise ValueError("No cameras are queued to validate.")
        self.cfg = cfg
        self.hits = {}
        self.per_camera = []
        self.index = 0
        self.started = time.time()
        # Visibility is enforced by what goes into the BVH, so the scene is
        # never mutated: nothing to reveal, nothing to put back.
        from . import raycast

        self.visible = raycast.build(context, cfg, force=True)
        self.visibility = None
        # The camera the user was looking through, so it can be put back.
        self.previous_camera = context.scene.camera
        self.previous_selection = [
            obj for obj in context.selected_objects
        ]
        progress.begin("Validate Camera Coverage", ("Validating",))
        progress.update(
            fraction=0.0,
            message="Preparing cameras",
            detail=f"0 of {len(self.cameras)} cameras",
        )

    def _step(self, context):
        """Look through one camera, cast from it, and report where we are."""
        from .. import progress

        camera = self.cameras[self.index]

        # Making it the active camera and selecting it is what turns this from
        # a silent wait into something the user can watch: the viewport moves
        # to each camera in turn as it is checked.
        context.scene.camera = camera
        for obj in context.selected_objects:
            obj.select_set(False)
        camera.select_set(True)
        context.view_layer.objects.active = camera

        found = cast_one_camera(
            context, camera, self.hits, self.index, visible=self.visible
        )
        self.per_camera.append((camera.name, found))
        self.index += 1

        done = self.index
        total = len(self.cameras)
        fraction = done / max(1, total)
        elapsed = time.time() - self.started
        eta = ""
        if done and fraction > 0.0:
            remaining = elapsed / fraction - elapsed
            eta = progress.format_seconds(remaining)
        progress.update(
            fraction=fraction,
            message=f"Ray-casting {camera.name}",
            detail=f"Camera {done} of {total}",
            eta=eta,
        )
        _redraw_viewports()

    def _finish(self, context):
        from .. import sceneray_splat
        from .. import splat_manager
        from .. import progress

        if self.visibility is not None:
            sceneray_splat.restore_geometry_visibility(context, self.visibility)
        context.scene.camera = self.previous_camera
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in self.previous_selection:
            try:
                obj.select_set(True)
            except (ReferenceError, RuntimeError):
                pass

        positions, counts, stats = merge_hits(
            self.hits, len(self.cameras), self.per_camera
        )
        if positions is None:
            progress.end("No camera hit any geometry")
            self.report(
                {"WARNING"},
                "No cameras hit any geometry. Check that they point at the "
                "scene and that it is visible to renders.",
            )
            return {"CANCELLED"}

        import numpy as np

        # Replacing, not adding: a new validation always supersedes the last.
        splat_manager.load_validation_cloud(
            context.scene, positions, coverage_colours(counts, np), np
        )
        message = (
            f"{stats['samples']:,} coverage samples from "
            f"{stats['cameras']} camera(s); {stats['weak']:,} seen by fewer "
            f"than {GOOD_COVERAGE} cameras."
        )
        if stats["unseen"]:
            message += f" {len(stats['unseen'])} camera(s) hit nothing."
        progress.end(message)
        self.report({"INFO"}, message)
        return {"FINISHED"}

    def _abort(self, context, message):
        from .. import sceneray_splat
        from .. import progress

        try:
            if self.visibility is not None:
                sceneray_splat.restore_geometry_visibility(
                    context, self.visibility
                )
            context.scene.camera = self.previous_camera
        except Exception:
            pass
        progress.end(message)

    # ------------------------------------------------------------------- run

    def invoke(self, context, event):
        if bpy.app.background:
            return self.execute(context)
        try:
            self._begin(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        # One camera per timer tick, so Blender keeps drawing and stays
        # responsive instead of freezing for the whole rig.
        self._timer = context.window_manager.event_timer_add(
            0.01, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # Escape, or the Stop button beside the progress bar. Both have to
        # work: the button is what the user sees, Escape is the habit.
        if (_cancel["requested"]
                or (event.type == "ESC" and event.value == "PRESS")):
            _cancel["requested"] = False
            self._cleanup(context)
            self._abort(context, "Coverage validation cancelled")
            self.report({"WARNING"}, "Coverage validation cancelled.")
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        try:
            if self.index < len(self.cameras):
                self._step(context)
                return {"RUNNING_MODAL"}
            self._cleanup(context)
            return self._finish(context)
        except Exception as exc:
            self._cleanup(context)
            self._abort(context, f"Coverage validation failed: {exc}")
            self.report({"ERROR"}, f"Coverage validation failed: {exc}")
            return {"CANCELLED"}

    def _cleanup(self, context):
        timer = getattr(self, "_timer", None)
        if timer is not None:
            context.window_manager.event_timer_remove(timer)
            self._timer = None

    def execute(self, context):
        """Background path: the same work without a modal loop."""
        if not bpy.app.background:
            return self.invoke(context, None)
        try:
            self._begin(context)
            while self.index < len(self.cameras):
                self._step(context)
            return self._finish(context)
        except Exception as exc:
            self._abort(context, str(exc))
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


def _redraw_viewports():
    window_manager = getattr(bpy.context, "window_manager", None)
    for window in getattr(window_manager, "windows", ()):
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type in {"VIEW_3D", "STATUSBAR", "PROPERTIES", "OUTLINER"}:
                area.tag_redraw()


CLASSES = (SPLATRAY_OT_validate_coverage,)
