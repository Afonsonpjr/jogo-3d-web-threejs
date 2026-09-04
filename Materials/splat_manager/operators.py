# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Viewer actions: framing, the point cloud, rendering, and the training lock.

There is no importing, removing or replacing here. The add-on trains one Splat
and lets you inspect it; it is not a Splat editor.
"""

import bpy
from bpy.types import Operator

from . import properties
from . import registry


def active_splat(context):
    """The trained Splat, if this scene has one."""
    return registry.active_root(context.scene)



class SPLATRAY_OT_frame_splat(Operator):
    """Move the viewport to look at the trained Splat"""

    bl_idname = "splatray.frame_splat"
    bl_label = "Frame Splat"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return active_splat(context) is not None

    def execute(self, context):
        empty = active_splat(context)
        for selected in tuple(context.selected_objects):
            selected.select_set(False)
        empty.select_set(True)
        context.view_layer.objects.active = empty
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for region in area.regions:
                if region.type == "WINDOW":
                    with context.temp_override(area=area, region=region):
                        bpy.ops.view3d.view_selected()
                    break
        return {"FINISHED"}


class SPLATRAY_OT_toggle_point_cloud(Operator):
    """Show or hide the training point cloud"""

    bl_idname = "splatray.toggle_point_cloud"
    bl_label = "Training Point Cloud"
    bl_description = (
        "Show or hide the point cloud the dataset was built from. Use it to "
        "check camera coverage before training: sparse and missing regions "
        "are the blind spots"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        # One shared point cloud for the whole add-on. It is read once and
        # then only shown or hidden - never re-imported or duplicated.
        empty = registry.active_root(context.scene, create=True)
        group = properties.settings_of(empty)
        if group.show_point_cloud and registry.point_cloud_loaded():
            group.show_point_cloud = False
            registry.tag_redraw()
            return {"FINISHED"}
        try:
            loaded = registry.ensure_point_cloud(context.scene)
        except Exception as exc:
            self.report({"ERROR"}, f"Could not read the point cloud: {exc}")
            return {"CANCELLED"}
        group.show_point_cloud = True
        registry.apply_point_cloud_colouring(bool(group.point_cloud_coverage))
        registry.tag_redraw()
        self.report({"INFO"}, f"Showing {loaded.count:,} training points.")
        return {"FINISHED"}


# --------------------------------------------------------------------------
# Training lock
# --------------------------------------------------------------------------

def set_training_lock(empty, locked):
    """Lock or unlock a Splat's Empty for the duration of a training run.

    Blender's own per-channel transform locks are used, so the restriction
    holds everywhere - the N panel, gizmos, G/R/S - not only inside this
    add-on's UI.
    """
    group = properties.settings_of(empty)
    if group is None:
        return
    group.training = bool(locked)
    empty.lock_location = (locked, locked, locked)
    empty.lock_rotation = (locked, locked, locked)
    empty.lock_rotation_w = locked
    empty.lock_scale = (locked, locked, locked)
    registry.tag_redraw()


def unlock_all(scene):
    for empty in registry.roots(scene):
        if empty.splatray_splat.training:
            set_training_lock(empty, False)


CLASSES = (
    SPLATRAY_OT_frame_splat,
    SPLATRAY_OT_toggle_point_cloud,
)
