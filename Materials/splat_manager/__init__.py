# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Viewer: inspecting the Splat this add-on just trained.

Training makes one Splat; this package draws it, and the training data behind
it, so the result can be checked before export. It is deliberately not a Splat
editor - nothing here imports, replaces or edits Splats, and a scene holds one
trained Splat rather than a collection of them.

Module map:
    data        reading PLY/npz and packing for the GPU - no Blender, no GPU
    shaders     the four visualization modes, in one shader program
    instance    one Splat: its buffers, its depth sort, its draw call
    registry    every loaded Splat, and the single draw handler over them
    properties  per-Splat settings, stored on the root Empty
    operators   framing, the point cloud, and the training lock
    ui          the Splat Manager panel
"""

import bpy

if "data" in locals():
    from importlib import reload

    data = reload(data)
    shaders = reload(shaders)
    instance = reload(instance)
    properties = reload(properties)
    registry = reload(registry)
    operators = reload(operators)
    ui = reload(ui)
else:
    from . import data
    from . import shaders
    from . import instance
    from . import properties
    from . import registry
    from . import operators
    from . import ui

# Public API used by the rest of the add-on.
from .ui import SPLATRAY_PT_splat_manager  # noqa: F401
from .operators import set_training_lock, unlock_all  # noqa: F401
from .registry import (  # noqa: F401
    active_root,
    collect_training_cameras,
    create_root,
    ensure_point_cloud,
    load_arrays_into,
    load_validation_cloud,
    load_into,
    remove_splat,
    roots,
    set_cameras_visible,
    set_scene_visible,
    tag_redraw,
)

# ui.SPLATRAY_PT_splat_manager is deliberately absent: like the other workflow
# sections it is drawn through a proxy layout, not owned by Blender.
_CLASSES = (*operators.CLASSES,)


def training_root(scene, create=True):
    """The one Splat the live training preview writes into."""
    return registry.active_root(scene, create=create)


def register():
    properties.register()
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    registry.register()


def unregister():
    registry.unregister()
    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    properties.unregister()
