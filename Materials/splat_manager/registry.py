# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Every loaded Splat in the session, and the one handler that draws them.

The scene owns the Empties; this module owns the GPU data behind them, keyed
by the id stored on each Empty. Keying on the id rather than the object name
means renaming an Empty, or Blender reallocating it, cannot orphan its Splats.

One draw handler walks the registry each frame. Each Splat is drawn with its
own Empty's transform, its own visibility, and its own viewer settings.
"""

from pathlib import Path
import time

import bpy

from . import data
from . import instance as instance_module
from . import properties
from . import shaders

#: splat_id -> SplatInstance
_instances = {}
_draw_handle = None
_last_error = ""

# UI and gizmo drawing can run dozens of times per second. These caches keep
# those read-only draws from rescanning every scene object and touching the
# dataset filesystem on every frame.
_active_root_cache = {}
_viewer_availability_cache = {}
_VIEWER_CACHE_SECONDS = 1.0

#: Collection the root Empty is placed in.
COLLECTION_NAME = "Splats"

#: The dataset point cloud is an instance too, under a fixed id: it is drawn
#: by the same renderer but is not a Splat the user owns. There is exactly one,
#: shared by every part of the add-on that shows the point cloud.
POINT_CLOUD_ID = "__training_point_cloud__"

#: The coverage preview is a separate, throwaway instance: it is a validation
#: read-out, never the cloud training uses.
VALIDATION_CLOUD_ID = "__coverage_preview__"

#: Collection the dataset's training cameras are gathered into.
CAMERA_COLLECTION_NAME = "Training Cameras"


def tag_redraw():
    window_manager = getattr(bpy.context, "window_manager", None)
    for window in getattr(window_manager, "windows", ()):
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type in {"VIEW_3D", "PROPERTIES", "OUTLINER"}:
                area.tag_redraw()


def invalidate_viewer_cache(scene=None):
    """Forget cached Viewer state after an add-on-owned structural change."""
    if scene is None:
        _active_root_cache.clear()
        _viewer_availability_cache.clear()
        return
    try:
        key = scene.as_pointer()
    except (AttributeError, ReferenceError):
        return
    _active_root_cache.pop(key, None)
    _viewer_availability_cache.pop(key, None)


# --------------------------------------------------------------------------
# Scene objects
# --------------------------------------------------------------------------

def splat_collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in {child.name for child in scene.collection.children}:
        try:
            scene.collection.children.link(collection)
        except RuntimeError:
            pass
    return collection


def create_root(scene, name, source_path=""):
    """The Empty that owns the trained Splat.

    It is an ordinary Blender object: moving, rotating, hiding, parenting and
    organising it all work exactly as they do for anything else, and the
    Splats follow.
    """
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 1.0
    group = empty.splatray_splat
    group.is_splat = True
    group.splat_id = properties.new_id()
    group.source_path = str(source_path)
    splat_collection(scene).objects.link(empty)
    invalidate_viewer_cache(scene)
    return empty


def roots(scene):
    """Every Splat root Empty in a scene, in a stable order.

    There is normally exactly one: the add-on trains and inspects a single
    Splat rather than managing a collection of them. The list form is kept so
    a file that somehow holds more than one still draws and can be cleaned up.
    """
    found = [
        obj for obj in getattr(scene, "objects", ())
        if properties.settings_of(obj) is not None
    ]
    found.sort(key=lambda obj: obj.name)
    return found


def active_root(scene, create=False):
    """The one trained Splat in this scene."""
    try:
        key = scene.as_pointer()
        object_count = len(scene.objects)
    except (AttributeError, ReferenceError):
        key = None
        object_count = -1
    cached = _active_root_cache.get(key) if key is not None else None
    if cached is not None and cached[0] == object_count:
        name = cached[1]
        if name is None:
            return create_root(scene, "Trained_Splat") if create else None
        candidate = scene.objects.get(name)
        if candidate is not None and properties.settings_of(candidate) is not None:
            return candidate
    found = roots(scene)
    if found:
        if key is not None:
            _active_root_cache[key] = (object_count, found[0].name)
        return found[0]
    if key is not None:
        _active_root_cache[key] = (object_count, None)
    return create_root(scene, "Trained_Splat") if create else None


def viewer_availability(scene):
    """Cached data availability shared by the panel and viewport gizmos.

    The signature is entirely in-memory and cheap. Filesystem and full-scene
    checks happen at most once per second, while explicit Viewer structural
    changes invalidate the cache immediately.
    """
    root = active_root(scene)
    instance = get(root.splatray_splat.splat_id) if root is not None else None
    cfg = getattr(scene, "SCENERAY_SPLAT", None)
    settings = getattr(scene, "SCENERAY_SPLAT_TRAINING", None)
    splat_loaded = bool(instance is not None and instance.is_loaded())
    coverage_loaded = validation_cloud_loaded()
    try:
        key = scene.as_pointer()
    except (AttributeError, ReferenceError):
        key = id(scene)
    signature = (
        len(scene.objects),
        len(getattr(cfg, "camera_queue", ())) if cfg is not None else 0,
        root.name if root is not None else "",
        splat_loaded,
        coverage_loaded,
        str(getattr(cfg, "active_dataset_dir", "") or ""),
        str(getattr(settings, "dataset_dir", "") or ""),
    )
    now = time.monotonic()
    cached = _viewer_availability_cache.get(key)
    if (
        cached is not None
        and cached[0] == signature
        and now - cached[1] < _VIEWER_CACHE_SECONDS
    ):
        return cached[2]
    result = {
        "splat": splat_loaded,
        "points": point_cloud_source(scene, settings) is not None,
        "coverage": coverage_loaded,
        "cameras": bool(cfg is not None and len(cfg.camera_queue)),
        "scene": any(
            obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}
            for obj in scene.objects
        ),
        "root": root,
    }
    _viewer_availability_cache[key] = (signature, now, result)
    return result


# --------------------------------------------------------------------------
# Training cameras and the source point cloud
# --------------------------------------------------------------------------

def training_cameras(scene):
    """The cameras the dataset render produced, not arbitrary scene cameras."""
    from .. import sceneray_splat

    prefix = sceneray_splat._MANAGED_CAMERA_PREFIX
    queued = {
        item.camera.name
        for item in getattr(getattr(scene, "SCENERAY_SPLAT", None), "camera_queue", ())
        if item.camera is not None
    }
    return [
        obj for obj in getattr(scene, "objects", ())
        if obj.type == "CAMERA"
        and (obj.name.startswith(prefix) or obj.name in queued)
    ]


def camera_collection(scene, create=True):
    """The collection holding the dataset's training cameras."""
    collection = bpy.data.collections.get(CAMERA_COLLECTION_NAME)
    if collection is None:
        if not create:
            return None
        collection = bpy.data.collections.new(CAMERA_COLLECTION_NAME)
    if collection.name not in {child.name for child in scene.collection.children}:
        try:
            scene.collection.children.link(collection)
        except RuntimeError:
            pass
    return collection


def collect_training_cameras(scene):
    """Gather the dataset's cameras into their own collection.

    Called once when a dataset is rendered. The Viewer's toggle then only ever
    changes that collection's visibility - the cameras themselves are the ones
    that produced the images and are never recreated.
    """
    cameras = training_cameras(scene)
    if not cameras:
        return None, 0
    collection = camera_collection(scene)
    moved = 0
    for camera in cameras:
        if collection.name in {c.name for c in camera.users_collection}:
            continue
        for existing in tuple(camera.users_collection):
            try:
                existing.objects.unlink(camera)
            except RuntimeError:
                pass
        try:
            collection.objects.link(camera)
            moved += 1
        except RuntimeError:
            pass
    return collection, moved


def set_cameras_visible(scene, visible):
    """Show or hide the training-camera collection. Creates nothing."""
    collection = camera_collection(scene, create=False)
    if collection is not None:
        collection.hide_viewport = not visible
        collection.hide_render = not visible
    # Cameras from a dataset built before the collection existed are still
    # honoured, so the toggle works on older projects too.
    for camera in training_cameras(scene):
        if collection is not None and collection.name in {
            c.name for c in camera.users_collection
        }:
            continue
        try:
            camera.hide_set(not visible)
        except (AttributeError, ReferenceError, RuntimeError):
            pass
    tag_redraw()


#: Objects the add-on owns, which the Scene toggle must never hide.
def _is_addon_object(obj, scene):
    from .. import sceneray_splat

    if properties.settings_of(obj) is not None:
        return True
    if obj.type == "CAMERA":
        # Training cameras stay: they are part of the inspection, not the
        # scene being inspected.
        return obj in training_cameras(scene)
    return obj.name.startswith(sceneray_splat._MANAGED_CAMERA_PREFIX)


def set_scene_visible(scene, visible):
    """Hide the artist's own objects without touching the add-on's.

    Meshes, lights, empties and everything else in the scene are hidden so the
    Splats can be inspected on their own. The Splat roots, the training
    cameras and anything else the add-on created stay exactly as they were, so
    this never has to be undone through the Outliner.
    """
    hidden = 0
    for obj in getattr(scene, "objects", ()):
        if _is_addon_object(obj, scene):
            continue
        try:
            obj.hide_set(not visible)
            hidden += 1
        except (AttributeError, ReferenceError, RuntimeError):
            pass
    tag_redraw()
    return hidden


def load_point_cloud(scene, points_path, np):
    """Load the dataset's own point cloud for display beside the Gaussians.

    It is packed as Splats so the existing renderer can draw it, but it stays
    a separate instance: showing the training cloud never disturbs, replaces
    or is confused with the Gaussian centres.
    """
    from .. import sceneray_splat

    source = Path(points_path)
    if not source.is_file():
        raise ValueError(f"No point cloud at {source}")
    xyz, rgb = sceneray_splat.read_colmap_points3D(source)
    positions = np.asarray(xyz, dtype=np.float32)
    count = int(positions.shape[0])
    if count <= 0:
        raise ValueError("The point cloud is empty")
    colours = np.asarray(rgb, dtype=np.float32).reshape(count, 3)
    if float(colours.max()) > 1.0:
        colours = colours / 255.0

    scales = np.full((count, 3), 1.0e-4, dtype=np.float32)
    quaternions = np.zeros((count, 4), dtype=np.float32)
    quaternions[:, 0] = 1.0
    opacities = np.ones(count, dtype=np.float32)
    sh = ((colours - 0.5) / data.SH_C0).reshape(count, 1, 3)

    target = attach(POINT_CLOUD_ID, "Training Point Cloud")
    target.set_arrays(positions, scales, quaternions, opacities, sh, np)
    target.source_path = str(source)
    # Both colourings are kept so switching between them is instant and never
    # re-reads the file.
    target.true_colour_sh = sh
    target.coverage_sh = data.coverage_colours(positions, np)
    ensure_draw_handler()
    tag_redraw()
    return target


def load_validation_cloud(scene, positions, colours, np):
    """Publish a coverage preview, replacing whatever the last one was.

    Kept apart from the training point cloud on purpose: it is a fast,
    coarse read-out of what the cameras can see, not the cloud training will
    use, and the two must never be mistaken for one another.
    """
    positions = np.asarray(positions, dtype=np.float32)
    count = int(positions.shape[0])
    if count <= 0:
        raise ValueError("The coverage preview is empty")
    colours = np.asarray(colours, dtype=np.float32).reshape(count, 3)

    scales = np.full((count, 3), 1.0e-4, dtype=np.float32)
    quaternions = np.zeros((count, 4), dtype=np.float32)
    quaternions[:, 0] = 1.0
    opacities = np.ones(count, dtype=np.float32)
    sh = ((colours - 0.5) / data.SH_C0).reshape(count, 1, 3)

    # One preview at a time: attaching under a fixed id replaces the previous
    # sample rather than accumulating them.
    target = attach(VALIDATION_CLOUD_ID, "Coverage Preview")
    target.set_arrays(positions, scales, quaternions, opacities, sh, np)
    empty = active_root(scene, create=True)
    empty.splatray_splat.show_validation_cloud = True
    ensure_draw_handler()
    tag_redraw()
    return target


def validation_cloud_instance():
    return _instances.get(VALIDATION_CLOUD_ID)


def validation_cloud_loaded():
    target = _instances.get(VALIDATION_CLOUD_ID)
    return target is not None and target.is_loaded()


def clear_validation_cloud():
    detach(VALIDATION_CLOUD_ID)


def point_cloud_instance():
    return _instances.get(POINT_CLOUD_ID)


def point_cloud_loaded():
    target = _instances.get(POINT_CLOUD_ID)
    return target is not None and target.is_loaded()


def apply_point_cloud_colouring(coverage):
    """Swap the point cloud between its own colours and a coverage read-out."""
    target = _instances.get(POINT_CLOUD_ID)
    if target is None or not target.is_loaded():
        return False
    replacement = target.coverage_sh if coverage else target.true_colour_sh
    if replacement is None:
        return False
    try:
        import numpy as np

        target.replace_colours(replacement, np)
    except Exception:
        return False
    tag_redraw()
    return True


def point_cloud_source(scene, settings=None):
    """The points3D.txt the viewer should currently be showing.

    The selected training version wins, because choosing one is an explicit
    statement about which dataset is being worked on. Failing that, the build
    the Building Data panel is pointed at - so a freshly built cloud is
    reachable straight away, without visiting the training section first.

    Returns None when there is nothing to show.
    """
    from ..building_data import paths as bd_paths

    if settings is None:
        settings = getattr(scene, "SCENERAY_SPLAT_TRAINING", None)
    cfg = getattr(scene, "SCENERAY_SPLAT", None)

    # The build the add-on is explicitly pointed at *is* the active dataset,
    # and it wins outright. A new build has no cloud until its third step
    # finishes, and answering with the previous dataset's cloud there would be
    # quietly wrong - the viewer would show points belonging to something else.
    #
    # Only an explicitly selected build counts. With none selected the
    # effective path falls back to the project root, which is not a dataset
    # and must not be read as "this dataset has no cloud".
    active = str(getattr(cfg, "active_dataset_dir", "") or "").strip()
    if active:
        try:
            build = Path(bpy.path.abspath(active))
        except (TypeError, ValueError):
            build = None
        if build is not None and build.is_dir():
            candidate = bd_paths.dataset_file(build, bd_paths.POINTCLOUD_FILE)
            return candidate if candidate.is_file() else None

    # No build selected at all: fall back to whatever training is pointed at,
    # so a dataset opened straight into the training section still shows.
    dataset = str(getattr(settings, "dataset_dir", "") or "").strip()
    if dataset:
        # Only ever reachable in Pro: the setting this reads belongs to the
        # training package, which the Standard build does not install. The
        # import is guarded anyway so this stays a fallback rather than a
        # hard dependency of the viewer.
        try:
            from ..splat_training import dataset as dataset_module

            candidate = Path(
                dataset_module.resolve_layout(dataset)["points_txt"])
            if candidate.is_file():
                return candidate
        except Exception:
            pass
    return None


def ensure_point_cloud(scene, settings=None):
    """Load the point cloud the active dataset points at, and keep it current.

    Every point-cloud control in the add-on goes through here, so there is one
    instance and one visualization however it was switched on. The cached
    instance is only reused when it came from the file that is active *now* -
    otherwise the viewer would keep showing the first cloud ever generated
    after the dataset moved on.
    """
    source = point_cloud_source(scene, settings)
    current = _instances.get(POINT_CLOUD_ID)
    if current is not None and current.is_loaded():
        if source is None:
            # Nothing better is known - a cloud loaded directly, or a dataset
            # selection that has since been cleared. Keep showing what is
            # there rather than throwing away a perfectly good cloud.
            return current
        try:
            same = Path(current.source_path) == source
        except (TypeError, ValueError):
            same = False
        if same:
            return current
        # A different dataset is active now. Drop the stale cloud rather than
        # handing back points that belong to another build.
        clear_point_cloud()

    if source is None:
        raise ValueError("No dataset is selected to read points from.")

    import numpy as np

    return load_point_cloud(scene, source, np)


def point_cloud_is_current(scene, settings=None):
    """Whether the loaded cloud still belongs to the active dataset."""
    current = _instances.get(POINT_CLOUD_ID)
    if current is None or not current.is_loaded():
        return False
    source = point_cloud_source(scene, settings)
    if source is None:
        return False
    try:
        return Path(current.source_path) == source
    except (TypeError, ValueError):
        return False


def refresh_point_cloud(scene, settings=None):
    """Re-read the cloud if the active dataset changed under it.

    Called when a build finishes and when the training version changes, so
    the viewer never lingers on a previous session's points.
    """
    current = _instances.get(POINT_CLOUD_ID)
    if current is None or not current.is_loaded():
        return False
    if point_cloud_is_current(scene, settings):
        return False
    was_visible = False
    empty = active_root(scene)
    if empty is not None:
        was_visible = bool(empty.splatray_splat.show_point_cloud)
    clear_point_cloud()
    if not was_visible:
        tag_redraw()
        return True
    try:
        ensure_point_cloud(scene, settings)
    except Exception:
        # The new dataset has no readable cloud; leave the switch off rather
        # than showing the old one.
        if empty is not None:
            empty.splatray_splat["show_point_cloud"] = False
    tag_redraw()
    return True


def clear_point_cloud():
    detach(POINT_CLOUD_ID)


def find_root(scene, splat_id):
    for obj in roots(scene):
        if obj.splatray_splat.splat_id == splat_id:
            return obj
    return None


# --------------------------------------------------------------------------
# Instances
# --------------------------------------------------------------------------

def get(splat_id):
    return _instances.get(str(splat_id))


def count():
    return len(_instances)


def loaded_ids():
    return set(_instances)


def attach(splat_id, name=""):
    existing = _instances.get(str(splat_id))
    if existing is None:
        existing = instance_module.SplatInstance(splat_id, name)
        _instances[str(splat_id)] = existing
        invalidate_viewer_cache()
    return existing


def detach(splat_id):
    existing = _instances.pop(str(splat_id), None)
    if existing is not None:
        existing.free()
        invalidate_viewer_cache()
    tag_redraw()


def clear():
    for existing in list(_instances.values()):
        existing.free()
    _instances.clear()
    invalidate_viewer_cache()


def load_into(empty, path, np):
    """Load a Gaussian PLY into the instance behind ``empty``.

    Used to restore a trained Splat when its file is reopened, not to bring
    in outside Splats: the add-on only shows what its own training produced.
    """
    group = properties.settings_of(empty)
    if group is None:
        raise ValueError(f"{empty.name} is not a Splat root")
    source = Path(bpy.path.abspath(str(path)))
    if not source.is_file():
        raise ValueError(f"Splat file does not exist: {source}")
    if source.suffix.lower() != ".ply":
        raise ValueError("Expected a Gaussian .ply file")
    arrays = data.load_ply(source, np)
    target = attach(group.splat_id, empty.name)
    target.set_arrays(*arrays, np)
    target.source_path = str(source)
    group.source_path = str(source)
    group.splat_count = target.count
    group.available_sh_degree = target.sh_degree
    ensure_draw_handler()
    tag_redraw()
    return target


def load_arrays_into(empty, arrays, np, source_path=""):
    """Publish arrays straight from the trainer into ``empty``'s instance."""
    group = properties.settings_of(empty)
    if group is None:
        raise ValueError(f"{empty.name} is not a Splat root")
    target = attach(group.splat_id, empty.name)
    target.set_arrays(*arrays, np)
    if source_path:
        target.source_path = str(source_path)
        group.source_path = str(source_path)
    group.splat_count = target.count
    group.available_sh_degree = target.sh_degree
    ensure_draw_handler()
    tag_redraw()
    return target


def remove_splat(scene, empty):
    """Delete a Splat: its GPU data and its Empty."""
    group = properties.settings_of(empty)
    if group is not None:
        detach(group.splat_id)
    try:
        bpy.data.objects.remove(empty, do_unlink=True)
    except (ReferenceError, RuntimeError):
        pass
    tag_redraw()


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def _object_is_visible(obj, context):
    try:
        if obj.hide_viewport:
            return False
        return obj.visible_get(view_layer=context.view_layer)
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        try:
            return not obj.hide_viewport and not obj.hide_get()
        except (AttributeError, ReferenceError, RuntimeError):
            return False


def visible_in_view_order(scene, context, view_matrix):
    """Splats to draw, furthest first.

    Splats are alpha-blended with depth writes off, so whichever is drawn last
    wins where they overlap. Drawing in name order therefore made one Splat
    disappear behind another depending on what they happened to be called.
    Ordering by the distance of each Splat's centre from the camera composites
    them correctly, the same way each Splat's own Gaussians are ordered.
    """
    drawable = []
    entries = []
    for empty in roots(scene):
        group = properties.settings_of(empty)
        splats = _instances.get(group.splat_id)
        # One Gaussian inspection mode is drawn at a time. The ``elif`` chain
        # also safely normalizes old .blend files that stored multiple modes.
        if group.show_gaussians:
            entries.append((empty, group, splats, "GAUSSIAN"))
        elif group.show_rings:
            entries.append((empty, group, splats, "RINGS"))
        elif group.show_centers:
            entries.append((empty, group, splats, "CENTERS"))
        # The dataset's own point cloud rides on the same Empty, so it moves
        # with the Splats it produced, but keeps its own instance.
        if group.show_point_cloud:
            entries.append(
                (empty, group, _instances.get(POINT_CLOUD_ID), "POINTS")
            )
        # The coverage preview is its own instance, so it can be shown with or
        # without the training cloud and never replaces it.
        if group.show_validation_cloud:
            entries.append(
                (empty, group, _instances.get(VALIDATION_CLOUD_ID), "POINTS")
            )

    for empty, group, target, mode in entries:
        if target is None or not target.is_loaded():
            continue
        if not _object_is_visible(empty, context):
            continue
        centre = target.centre_world(empty.matrix_world)
        # Blender's view space looks down -Z, so the further a centre is, the
        # more negative its z. Ascending z is therefore back to front.
        depth = (view_matrix @ centre.to_4d()).z
        drawable.append((depth, empty, group, target, mode))
    drawable.sort(key=lambda entry: entry[0])
    return [
        (empty, group, target, mode)
        for _depth, empty, group, target, mode in drawable
    ]


def _draw():
    global _last_error
    if not _instances:
        return
    context = bpy.context
    scene = getattr(context, "scene", None)
    if scene is None:
        return

    region_data = getattr(context, "region_data", None)
    if region_data is None:
        space_data = getattr(context, "space_data", None)
        region_data = getattr(space_data, "region_3d", None)
    if region_data is None:
        return

    import gpu

    drew_any = False
    try:
        view_matrix = region_data.view_matrix.copy()
        projection_matrix = region_data.window_matrix.copy()
        viewport = gpu.state.viewport_get()
        size = (max(1.0, float(viewport[2])), max(1.0, float(viewport[3])))

        for empty, group, target, mode in visible_in_view_order(
            scene, context, view_matrix
        ):
            if not drew_any:
                gpu.state.blend_set("ALPHA")
                gpu.state.depth_test_set("LESS_EQUAL")
                gpu.state.depth_mask_set(False)
                drew_any = True
            # The Empty's world matrix is the Splat's model matrix, which is
            # what makes move/rotate/scale/parent work with no extra code.
            model_view = view_matrix @ empty.matrix_world
            target.draw(
                model_view,
                projection_matrix,
                size,
                properties.viewer_settings(group, mode),
                tag_redraw,
            )
        _last_error = ""
    except Exception as exc:
        _last_error = str(exc)
    finally:
        if drew_any:
            try:
                gpu.state.depth_mask_set(True)
                gpu.state.depth_test_set("NONE")
                gpu.state.blend_set("NONE")
            except Exception:
                pass


def ensure_draw_handler():
    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw, (), "WINDOW", "POST_VIEW"
        )
    tag_redraw()


def remove_draw_handler():
    global _draw_handle
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        except (ValueError, RuntimeError):
            pass
        _draw_handle = None


def last_error():
    return _last_error


# --------------------------------------------------------------------------
# File lifecycle
# --------------------------------------------------------------------------

@bpy.app.handlers.persistent
def reload_after_file_load(*_args):
    """Rebuild instances from the Empties in the freshly opened file.

    GPU data cannot be stored in a .blend, so each Empty remembers its source
    file and the Splats are read back here. An Empty whose file has moved is
    kept, with a count of zero, so the user can point it somewhere else rather
    than silently losing the object.
    """
    clear()
    try:
        import numpy as np
    except ImportError:
        return
    for scene in getattr(bpy.data, "scenes", ()):
        for empty in roots(scene):
            group = empty.splatray_splat
            # A run that was training when the file was saved is not training
            # now; nothing should stay locked to a worker that is gone.
            group.training = False
            source = str(group.source_path or "").strip()
            if not source:
                continue
            try:
                load_into(empty, source, np)
            except Exception:
                group.splat_count = 0
    tag_redraw()


def register():
    invalidate_viewer_cache()
    if reload_after_file_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(reload_after_file_load)
    # Reserve the scene-data layer now, before camera_overlay registers the
    # Viewer plate. Later Splat loads reuse this handle, preserving the fixed
    # scene -> plate -> gizmo ordering for every viewport redraw.
    ensure_draw_handler()


def unregister():
    while reload_after_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(reload_after_file_load)
    remove_draw_handler()
    clear()
    invalidate_viewer_cache()
    shaders.release()
