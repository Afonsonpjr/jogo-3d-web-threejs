# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Per-Splat settings, stored on the root Empty.

Keeping these on the object rather than in a module means each Splat carries
its own visualization state, they survive save and load, and Blender's own
copy/delete/undo behaviour applies to them for free.

The GPU data itself cannot live in a .blend, so the Empty records where it came
from and the registry reloads it when the file opens.
"""

import uuid

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


def _redraw(self, context):
    from . import registry

    registry.tag_redraw()


def _exclusive_splat_view_update(self, active_name):
    """Allow one Gaussian visualization at a time, or none when toggled off."""
    from . import registry

    if bool(getattr(self, active_name)):
        for name in ("show_gaussians", "show_rings", "show_centers"):
            if name != active_name:
                # ID-property assignment avoids recursively firing updates.
                self[name] = False
    registry.tag_redraw()


def _gaussians_update(self, context):
    _exclusive_splat_view_update(self, "show_gaussians")


def _rings_update(self, context):
    _exclusive_splat_view_update(self, "show_rings")


def _centers_update(self, context):
    _exclusive_splat_view_update(self, "show_centers")


def _cameras_update(self, context):
    """Show or hide the training-camera collection. Nothing is recreated."""
    from . import registry

    registry.set_cameras_visible(context.scene, bool(self.show_cameras))


def _scene_update(self, context):
    """Show or hide the artist's own scene, leaving the add-on's data alone."""
    from . import registry

    registry.set_scene_visible(context.scene, bool(self.show_scene))


def _point_cloud_update(self, context):
    """Switching it on reads the cloud once; after that it only shows it.

    Doing the load here rather than behind a separate button is what lets the
    point cloud be a plain toggle everywhere, so every control in the panel
    behaves the same way.
    """
    from . import registry

    if self.show_point_cloud and not registry.point_cloud_loaded():
        try:
            registry.ensure_point_cloud(context.scene)
            registry.apply_point_cloud_colouring(bool(self.point_cloud_coverage))
        except Exception:
            # Nothing to show: fall back rather than leaving the button lit.
            self["show_point_cloud"] = False
    registry.tag_redraw()


def _coverage_update(self, context):
    """Recolour the existing point cloud; never reload or duplicate it."""
    from . import registry

    registry.apply_point_cloud_colouring(bool(self.point_cloud_coverage))


class SPLATRAY_PG_splat(PropertyGroup):
    """Marks an Empty as a Splat root and holds that Splat's settings."""

    is_splat: BoolProperty(default=False, options={"HIDDEN"})
    splat_id: StringProperty(default="", options={"HIDDEN"})
    source_path: StringProperty(
        name="Source",
        description="File this Splat was loaded from",
        subtype="FILE_PATH",
        options={"HIDDEN"},
    )
    #: Set while training owns this Splat. The Empty is locked so a stray drag
    #: cannot move a Splat the trainer is still writing to.
    training: BoolProperty(default=False, options={"HIDDEN"})

    splat_count: IntProperty(default=0, options={"HIDDEN"})
    available_sh_degree: IntProperty(default=0, options={"HIDDEN"})

    # ------------------------------------------------------------- viewer
    # The three Gaussian inspection modes are exclusive toggles. Selecting a
    # different mode hides the current one; toggling the active mode off leaves
    # all three hidden. Dataset clouds and scene/camera visibility stay fully
    # independent.
    show_gaussians: BoolProperty(
        name="Gaussian Splats",
        description="Show the trained Gaussian Splats",
        default=True,
        update=_gaussians_update,
    )
    show_rings: BoolProperty(
        name="Gaussian Rings",
        description=(
            "Show each Gaussian's 1-sigma contour, for inspecting orientation "
            "and distribution"
        ),
        default=False,
        update=_rings_update,
    )
    show_centers: BoolProperty(
        name="Gaussian Centers",
        description="Show the centre of every Gaussian",
        default=False,
        update=_centers_update,
    )
    sh_degree_preview: EnumProperty(
        name="SH Degree",
        description=(
            "Spherical-harmonic degree used for viewport colour. Preview only: "
            "the trained model is never modified"
        ),
        # Named, not bare digits, so the drop-down reads as a list of degrees
        # rather than a column of single characters.
        items=[
            ("0", "Deg 0", "Diffuse colour only, with no view dependence"),
            ("1", "Deg 1", "Low view-dependent colour"),
            ("2", "Deg 2", "Medium view-dependent colour"),
            ("3", "Deg 3", "Full view-dependent colour"),
        ],
        default="3",
        update=_redraw,
    )
    show_point_cloud: BoolProperty(
        name="Training Point Cloud",
        description=(
            "Show the point cloud the dataset was built from. Independent of "
            "the Gaussian visualization, and not the Gaussian centres"
        ),
        default=False,
        update=lambda self, context: _point_cloud_update(self, context),
    )
    point_cloud_coverage: BoolProperty(
        name="Coverage",
        description=(
            "Colour the point cloud by how densely it was reconstructed. "
            "Sparse and missing regions are the blind spots the cameras did "
            "not cover well enough to train from"
        ),
        default=False,
        update=lambda self, context: _coverage_update(self, context),
    )
    show_validation_cloud: BoolProperty(
        name="Validation Point Cloud",
        description=(
            "Show the coverage preview from Validate Camera Coverage. Red is "
            "seen by one camera, green by several. Validation only - this is "
            "never used for training"
        ),
        default=False,
        update=_redraw,
    )
    show_cameras: BoolProperty(
        name="Cameras",
        description="Show the training cameras rendered for this dataset",
        default=True,
        update=lambda self, context: _cameras_update(self, context),
    )
    show_scene: BoolProperty(
        name="Scene",
        description=(
            "Show the original Blender scene. Turn it off to inspect the "
            "Splats on their own; the training cameras, point cloud and "
            "Splats stay visible"
        ),
        default=True,
        update=lambda self, context: _scene_update(self, context),
    )
    point_size: FloatProperty(
        name="Point Size",
        description="Pixel size of the dots in Point Cloud and Centers modes",
        default=3.0,
        min=1.0,
        max=32.0,
        update=_redraw,
    )
    ring_width: FloatProperty(
        name="Ring Width",
        description="Thickness of the contour drawn in Rings mode",
        default=0.35,
        min=0.02,
        max=2.0,
        update=_redraw,
    )
    splat_scale: FloatProperty(
        name="Splat Scale",
        description="Scales every Gaussian in the viewport preview only",
        default=1.0,
        min=0.01,
        max=5.0,
        update=_redraw,
    )


def settings_of(obj):
    """The Splat settings on an object, or None if it is not a Splat root."""
    group = getattr(obj, "splatray_splat", None)
    if group is None or not group.is_splat:
        return None
    return group


def new_id():
    return uuid.uuid4().hex


def viewer_settings(group, mode="GAUSSIAN"):
    """The dictionary the renderer consumes for one pass."""
    return {
        "mode": str(mode),
        "sh_degree": int(group.sh_degree_preview),
        "point_size": float(group.point_size),
        "ring_width": float(group.ring_width),
        "scale": float(group.splat_scale),
    }


CLASSES = (SPLATRAY_PG_splat,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.splatray_splat = bpy.props.PointerProperty(
        type=SPLATRAY_PG_splat
    )


def unregister():
    if hasattr(bpy.types.Object, "splatray_splat"):
        del bpy.types.Object.splatray_splat
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
