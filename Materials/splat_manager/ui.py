# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""The Viewer panel: inspecting the current training session.

One trained Splat, shown three ways, with the training data that produced it
available alongside. Nothing here imports, replaces or edits a Splat - the
workflow is Dataset -> Training -> Visualization -> Export.

    Viewer
    ├── Gaussians │ Rings │ Centers │ Points │ Coverage │ Cameras │ Scene
    ├── Frame Splat
    └── display settings for whatever is switched on

Every control is a visibility switch over data that already exists. Nothing
here duplicates a scene object, and turning one view on never turns another
off - the Gaussians, their rings and their centres are three readings of the
same buffer.

The control row is permanent. It draws with the same buttons in the same
places before a Splat exists, while one is training and after it is loaded, so
the panel never reflows underneath a click. A button whose data has not been
produced yet is dimmed but still pressable: pressing it names the step that
would create it, which is the only way that prerequisite is ever discovered.

The layout deliberately uses one plain aligned row at default width instead of
scaled, centred, individually boxed cells. Blender lays an aligned row out in
a single pass at any panel width; the previous scale_x/scale_y arrangement had
to be re-fitted on every redraw and was what made the section flicker and drag
the rest of the interface with it.

Drawn through a proxy layout like the other workflow sections, so the drawing
work lives in module-level functions rather than methods.
"""

from bpy.types import Panel

from .. import theme
from . import operators
from . import properties
from . import registry

#: Every quick-access control, in one row. Same kind of button throughout: a
#: square icon toggle that shows or hides something already in the scene. The
#: third entry is the availability key this control reads.
_TOGGLES = (
    ("show_gaussians", "SHADING_RENDERED", "splat"),
    ("show_rings", "MESH_CIRCLE", "splat"),
    ("show_centers", "DOT", "splat"),
    ("show_point_cloud", "OUTLINER_OB_POINTCLOUD", "points"),
    ("show_validation_cloud", "VIEWZOOM", "coverage"),
    ("show_cameras", "CAMERA_DATA", "cameras"),
    ("show_scene", "SCENE_DATA", "scene"),
)


def _placeholder(layout, name, icon):
    """A dimmed but pressable stand-in for a control with no data yet.

    Dimmed rather than disabled: a dead button teaches nothing, while this one
    reports the step that would bring it to life.
    """
    cell = layout.row(align=True)
    cell.active = False
    cell.operator(
        "sceneray_splat.viewer_shortcut", text="", icon=icon
    ).shortcut = name


def _draw_toggles(layout, group, available):
    """The visualization controls. Nothing here creates a scene object."""
    # A fixed-column grid rather than a row of scaled cells: every button gets
    # an equal share of whatever width the panel has, so the group stays
    # balanced in the Properties tab, the sidebar and the Outliner popover
    # without Blender having to re-fit it on each redraw.
    row = layout.grid_flow(
        row_major=True,
        columns=len(_TOGGLES),
        even_columns=True,
        align=True,
    )
    row.scale_y = 1.25
    for name, icon, requirement in _TOGGLES:
        if group is not None and available.get(requirement, False):
            # The real property, so this row and the rest of the add-on drive
            # one control rather than two that can drift apart.
            row.prop(group, name, text="", icon=icon, toggle=True)
        elif name == "show_point_cloud" and available.get(requirement, False):
            # A built dataset can own a point cloud before any Splat is
            # trained. This operator makes the shared Viewer root, then
            # behaves exactly like the toggle above.
            row.operator(
                operators.SPLATRAY_OT_toggle_point_cloud.bl_idname,
                text="",
                icon=icon,
            )
        else:
            _placeholder(row, name, icon)

    # Framing is an action rather than a switch, so it gets its own labelled
    # row instead of hiding as an unlabelled icon at the end of the toggles.
    frame = layout.row(align=True)
    if available.get("splat", False):
        frame.operator(
            operators.SPLATRAY_OT_frame_splat.bl_idname,
            text="Frame Splat",
            icon="ZOOM_SELECTED",
        )
    else:
        frame.active = False
        frame.operator(
            "sceneray_splat.viewer_shortcut",
            text="Frame Splat",
            icon="ZOOM_SELECTED",
        ).shortcut = "show_gaussians"


def _draw_sh_preview(layout, group):
    """The spherical-harmonic preview, as one drop-down row.

    A viewport preview switch does not need a titled block of its own. It is a
    single choice, so it draws as a single labelled drop-down and only speaks
    up when the chosen degree is more than the Splat actually stores.
    """
    row = layout.row(align=True)
    row.enabled = group.show_gaussians or group.show_rings
    row.use_property_split = True
    row.use_property_decorate = False
    row.prop(group, "sh_degree_preview", text="SH Degree")


def _draw_settings(layout, group):
    body = layout.column()
    body.use_property_split = True
    body.use_property_decorate = False
    if group.show_centers or group.show_point_cloud:
        body.prop(group, "point_size")
    if group.show_rings:
        body.prop(group, "ring_width")
    if group.show_gaussians or group.show_rings:
        body.prop(group, "splat_scale")
    if group.show_point_cloud:
        body.prop(group, "point_cloud_coverage")


def _draw_export(layout, context):
    """Exporting the trained Splat: the final step of the whole workflow.

    Drawn here rather than in the training section so it is the last button in
    the add-on, in the order the work actually happens.
    """
    from ..splat_training import ui as training_ui

    layout.separator()
    box = layout.box()
    theme.heading(
        box,
        "EXPORT",
        custom="stage_export",
        fallback="EXPORT",
    )
    training_ui.draw_export(box, context)


def draw_manager(layout, context):
    # One cached read per draw. Every availability question below answers from
    # it, so a redraw never rescans the scene or the dataset folder more than
    # once - see registry.viewer_availability.
    available = registry.viewer_availability(context.scene)
    empty = available.get("root")
    group = properties.settings_of(empty) if empty is not None else None

    box = layout.box()
    header = box.row(align=True)
    title = empty.name if empty is not None else "Viewer Controls"
    custom_id = theme.custom_icon("stage_viewer")
    if custom_id:
        header.label(text=title, icon_value=custom_id)
    else:
        header.label(text=title, icon="OUTLINER_OB_POINTCLOUD")

    _draw_toggles(box, group, available)
    if group is not None:
        _draw_sh_preview(box, group)
        _draw_settings(box, group)

    # Export belongs to the trainer's half of the add-on, so it only exists
    # where the trainer does. Standard never draws this panel at all; the
    # guard keeps the dependency honest rather than relying on that.
    from .. import edition
    if edition.has_training():
        _draw_export(layout, context)


class SPLATRAY_PT_splat_manager(Panel):
    """Section 4 of the workflow: inspecting the trained Splat."""

    bl_idname = "SPLATRAY_PT_splat_manager"
    bl_label = "4. Viewer"
    bl_parent_id = "SCENERAY_SPLAT_PT_panel"
    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"
    bl_category = "SplatGen"
    bl_order = 3

    def draw(self, context):
        draw_manager(self.layout, context)
