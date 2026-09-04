# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""The Building Data panel.

Two sections, one per operation:

    Building Data
    ├── Rendering Images   camera list, render settings, build, status
    └── Point Cloud        estimate, quality preset, build, status

Everything that produces dataset files lives here. As with the other workflow
sections this class is never registered: the host panel calls ``draw`` through
a proxy layout, so ``self`` is not a panel instance and the drawing work lives
in module-level functions.
"""

from bpy.types import Panel

from .. import theme
from . import manifest as bd_manifest
from . import paths
from . import stages


def _section(layout, cfg, property_name, label, icon, *, custom=None,
             detail=None, state=None):
    from .. import sceneray_splat

    return sceneray_splat._sr_pipeline_section(
        layout, cfg, property_name, label, icon,
        custom=custom, detail=detail, state=state,
    )


# The per-section progress bars are gone. There is exactly one bar, drawn by
# progress.draw_active directly beneath whichever button started the work.


# --------------------------------------------------------------------------
# Rendering Images
# --------------------------------------------------------------------------

def _draw_render_controls(layout, cfg, busy):
    box = layout.box()
    box.enabled = not busy
    box.use_property_split = True
    box.use_property_decorate = False
    theme.heading(
        box,
        "RENDER OUTPUT",
        fallback="OUTPUT",
    )
    box.prop(cfg, "dataset_image_format")
    if cfg.dataset_image_format == "PNG":
        box.prop(cfg, "png_compression")
    else:
        box.prop(cfg, "jpeg_quality")
    # Validity masks are part of Dataset(Default), not optional metadata.
    box.prop(cfg, "dataset_mask_format")


def _outdated_cameras(context, cfg):
    """Cameras whose settings no longer match the image already rendered."""
    from .. import sceneray_splat

    # Same rule as the queue itself: a camera can only be out of date with
    # respect to work that already exists.
    if not sceneray_splat._sr_continuing_existing_dataset(cfg):
        return {}
    output_dir = sceneray_splat._sr_effective_output_path(cfg)
    if output_dir is None:
        return {}
    data = (
        sceneray_splat.read_render_manifest(output_dir)
        or sceneray_splat.read_completed_camera_data(output_dir)
        or {}
    )
    entries = {
        entry.get("name"): entry
        for entry in data.get("cameras", ())
        if isinstance(entry, dict) and entry.get("name")
    }
    if not entries:
        return {}
    try:
        return bd_manifest.outdated_cameras(cfg, entries)
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return {}


def _draw_rendering_images(layout, context, cfg, busy):
    box = _section(
        layout, cfg, "show_render_section", "Render Images", "RENDER_STILL",
        custom="stage_dataset",
    )
    if box is None:
        return
    _draw_render_controls(box, cfg, busy)


def _draw_camera_section(layout, context, cfg):
    """Step one: which cameras the dataset is built from."""
    box = _section(
        layout, cfg, "show_camera_list_section", "Camera List",
        "OUTLINER_OB_CAMERA",
        custom="stage_cameras",
    )
    if box is None:
        return
    from .. import sceneray_splat

    sceneray_splat.SCENERAY_SPLAT_PT_cameras.draw(
        sceneray_splat._SplatGenDrawProxy(box), context
    )


# --------------------------------------------------------------------------
# Point Cloud
# --------------------------------------------------------------------------

def _draw_point_estimate(layout, cfg):
    """What the current settings will produce, as figures rather than prose."""
    from .. import sceneray_splat

    queued = sum(1 for item in cfg.camera_queue if item.camera is not None)
    if not queued:
        return
    estimate = sceneray_splat._sr_estimate_point_cloud(cfg, queued)
    theme.stat(layout, (
        ("Cameras Used",
         f"{estimate['cameras_used']:,} of {estimate['cameras_total']:,}"),
        ("Rays Per Camera", f"{estimate['rays_per_camera']:,}"),
        ("Merge Retention",
         f"{estimate['retained_fraction'] * 100.0:.0f}%"),
        ("Estimated Points", f"~{estimate['final_points']:,}"),
    ))


def _draw_point_quality(layout, cfg, busy):
    box = layout.box()
    box.enabled = not busy
    box.use_property_split = True
    box.use_property_decorate = False
    theme.heading(
        box,
        "POINT QUALITY",
        custom="stage_points",
        fallback="PRESET",
    )
    box.prop(cfg, "point_quality", expand=True)
    if cfg.point_quality != "CUSTOM":
        return
    advanced = box.column(align=True)
    advanced.prop(cfg, "point_camera_usage")
    advanced.prop(cfg, "point_sampling_density")
    advanced.prop(cfg, "point_merging_strength")


def _draw_point_cloud(layout, context, cfg, busy):
    box = _section(
        layout,
        cfg,
        "show_pointcloud_section",
        "Point Cloud",
        "OUTLINER_OB_POINTCLOUD",
        custom="stage_points",
    )
    if box is None:
        return
    _draw_point_quality(box, cfg, busy)

    information = box.box()
    theme.heading(information, "POINT CLOUD INFORMATION", fallback="INFO")
    _draw_point_estimate(information, cfg)

    coverage = box.box()
    theme.heading(coverage, "CAMERA COVERAGE", fallback="VIEWZOOM")
    draw_validate_button(coverage, context, cfg)


# draw_validation is deliberately gone. Coverage validation has one entry
# point - draw_validate_button, immediately above Build Dataset - so the
# workflow reads as validate then build with no second place to start it.


def _draw_build_dataset(layout, context, cfg, busy):
    """Dataset actions that reflect the newest build's on-disk state."""
    layout.separator()
    box = layout.box()

    from .. import sceneray_splat

    from .. import progress

    ready = (not stages.anything_running(context)
             and sceneray_splat._sr_has_queued_camera(cfg))
    report = stages.plan(context, cfg)
    state = report.get("state", "NEW")

    if state == "INCOMPLETE":
        notice = box.box()
        notice.alert = True
        notice.label(text="DATASET INCOMPLETE", icon=theme.STATUS_WAIT)
        notice.label(
            text=(
                f"Rendered: {int(report.get('rendered', 0)):,} / "
                f"{int(report.get('total', 0)):,}  |  "
                f"Pending: {int(report.get('pending', 0)):,}"
            )
        )

        action = box.column()
        action.enabled = ready
        action.scale_y = 1.55
        theme.accent(action, ready)
        resume = action.operator(
            stages.SPLATRAY_OT_build_dataset.bl_idname,
            text="CONTINUE",
            icon="PLAY",
        )
        resume.requested_action = "CONTINUE"

        fresh = box.column()
        fresh.enabled = ready
        fresh.scale_y = 1.35
        new_build = fresh.operator(
            stages.SPLATRAY_OT_build_dataset.bl_idname,
            text="BUILD A NEW DATASET",
            icon="FILE_REFRESH",
        )
        new_build.requested_action = "NEW"
    else:
        action = box.column()
        action.enabled = ready
        action.scale_y = 1.6
        theme.accent(action, ready)
        button = action.operator(
            stages.SPLATRAY_OT_build_dataset.bl_idname,
            text=(
                "BUILD A NEW DATASET"
                if state == "COMPLETE"
                else "BUILD DATASET"
            ),
            icon="FILE_REFRESH" if state == "COMPLETE" else "SEQ_STRIP_META",
        )
        button.requested_action = "NEW" if state == "COMPLETE" else "AUTO"

    # The one progress bar, directly under the button that started it, with
    # this operation's own controls beside it.
    def controls(row):
        progress.control(row, 'STOP', "sceneray_splat.stop_render",
                         "STOP BUILD", "CANCEL")

    progress.draw_active(box, progress.OWNER_BUILD, controls)


class SPLATRAY_PT_building_data(Panel):
    """Section 2 of the workflow: everything that produces dataset files."""

    bl_idname = "SPLATRAY_PT_building_data"
    bl_label = "2. Building Data"
    bl_parent_id = "SCENERAY_SPLAT_PT_panel"
    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"
    bl_category = "SplatGen"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.SCENERAY_SPLAT
        busy = stages.is_busy(cfg)
        # Cameras, then the render, then the point cloud: the same order the
        # build itself runs in, so reading the panel top to bottom describes
        # what Build Dataset is about to do.
        # The camera list draws the global settings itself, so this panel and
        # the Camera Placement one stay identical with no duplicated layout.
        _draw_camera_section(layout, context, cfg)
        _draw_rendering_images(layout, context, cfg, busy)
        _draw_point_cloud(layout, context, cfg, busy)
        _draw_build_dataset(layout, context, cfg, busy)


# The host panel keeps the camera list and Build Dataset permanently visible
# and folds the two settings groups away, so it reaches these three pieces
# individually rather than drawing the section as a block.

def draw_build_dataset(layout, context, cfg):
    _draw_build_dataset(layout, context, cfg, stages.is_busy(cfg))


def draw_validate_button(layout, context, cfg):
    """Coverage validation, kept beside Build Dataset rather than folded away.

    Checking placement before rendering is the cheapest fix in the whole
    workflow, so it sits next to the button whose cost it saves.
    """
    from . import validation
    from .. import progress

    row = layout.row()
    row.scale_y = 1.3
    row.enabled = not stages.anything_running(context)
    row.operator(
        validation.SPLATRAY_OT_validate_coverage.bl_idname,
        text="VALIDATE CAMERA COVERAGE",
        icon="VIEWZOOM",
    )

    def controls(bar):
        progress.control(bar, 'STOP', "sceneray_splat.stop_render",
                         "STOP VALIDATION", "CANCEL")

    # The one progress bar, directly under the button that started it, with
    # this operation's own stop control beside it.
    if progress.draw_active(layout, progress.OWNER_VALIDATE, controls):
        return

    from ..splat_manager import registry as splat_registry

    if splat_registry.validation_cloud_loaded():
        theme.stat(layout, (("Camera Coverage", "Validated"),))


#: The build's own outputs, and the scene they were built from. Deliberately
#: not the trained-Splat controls: those belong to the Viewer.
_DATASET_PREVIEW = (
    ("show_point_cloud", 'OUTLINER_OB_POINTCLOUD', "points"),
    ("show_validation_cloud", 'VIEWZOOM', "coverage"),
    ("show_cameras", 'CAMERA_DATA', "cameras"),
    ("show_scene", 'SCENE_DATA', "scene"),
)


def draw_dataset_preview(layout, context):
    """Show what this section just produced, where there is no Viewer panel.

    Pro reaches these same four switches through the Viewer. Standard has no
    Viewer, and a build whose point cloud and coverage preview cannot be
    turned back on is a build you can only look at once - so the controls for
    the section's own output live in the section.
    """
    from ..splat_manager import operators as splat_operators
    from ..splat_manager import properties as splat_properties
    from ..splat_manager import registry as splat_registry

    available = splat_registry.viewer_availability(context.scene)
    empty = available.get("root")
    group = splat_properties.settings_of(empty) if empty is not None else None
    if group is None and not available.get("points", False):
        # Nothing has been built or validated yet, and there is no Viewer
        # root to hold the switches. An empty row would say nothing.
        return

    box = layout.box()
    theme.heading(box, "PREVIEW", custom="stage_viewer",
                  fallback='OUTLINER_OB_POINTCLOUD')
    row = box.grid_flow(
        row_major=True,
        columns=len(_DATASET_PREVIEW),
        even_columns=True,
        align=True,
    )
    row.scale_y = 1.25
    for name, icon, requirement in _DATASET_PREVIEW:
        ready = available.get(requirement, False)
        if group is not None and ready:
            row.prop(group, name, text="", icon=icon, toggle=True)
        elif name == "show_point_cloud" and ready:
            # A built dataset owns a point cloud before any Viewer root
            # exists. This operator makes the root, then behaves as above.
            row.operator(
                splat_operators.SPLATRAY_OT_toggle_point_cloud.bl_idname,
                text="",
                icon=icon,
            )
        else:
            cell = row.row(align=True)
            cell.active = False
            cell.operator(
                "sceneray_splat.viewer_shortcut", text="", icon=icon
            ).shortcut = name
    if group is not None and (group.show_point_cloud
                              or group.show_validation_cloud):
        settings = box.column()
        settings.use_property_split = True
        settings.use_property_decorate = False
        settings.prop(group, "point_size")
        if group.show_point_cloud:
            settings.prop(group, "point_cloud_coverage")


def draw_render_settings(layout, context, cfg):
    _draw_rendering_images(layout, context, cfg, stages.is_busy(cfg))


def draw_pointcloud_settings(layout, context, cfg):
    _draw_point_cloud(layout, context, cfg, stages.is_busy(cfg))
