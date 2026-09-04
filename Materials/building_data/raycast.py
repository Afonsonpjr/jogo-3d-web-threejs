# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""One ray-castable copy of exactly what the render will contain.

Every scene analysis in the add-on - coverage validation, the point cloud,
scene bounds - has to agree with the final images. That means one rule: if an
object would not appear in a render, it does not exist here. Not as a hit, not
as an occluder, not as a contributor to bounds.

The old approach cast into the live scene and then *skipped* unwanted hits,
re-casting up to 64 times per ray to get past hidden geometry. That was both
slow and fragile: an object hidden from the render still blocked the ray until
it was skipped past, and every skip cost another full scene cast.

This builds a BVH from the evaluated meshes of the render-visible objects
only. Visibility is then enforced by construction - hidden geometry is simply
absent - and each ray is a single cast into a tree built once for the whole
operation rather than once per ray.

Evaluated meshes come from the dependency graph, so modifiers, geometry nodes
and instancing are all already applied.
"""

import time

import bpy
from mathutils.bvhtree import BVHTree

#: Rebuilt when the scene changes; a build is far cheaper than the casts it
#: serves, but not cheap enough to repeat per camera.
_cache = {"key": None, "scene": None, "built_at": 0.0}

CACHE_SECONDS = 30.0


class RenderVisibleScene:
    """A BVH over the geometry a render would actually show."""

    def __init__(self, tree, triangle_objects, triangle_materials, objects,
                 minimum, maximum):
        self.tree = tree
        self.triangle_objects = triangle_objects
        self.triangle_materials = triangle_materials
        self.objects = objects
        self.minimum = minimum
        self.maximum = maximum

    @property
    def is_empty(self):
        return self.tree is None

    def ray_cast(self, origin, direction):
        """``(location, normal, index, distance)`` or all-None on a miss.

        A single cast: anything hidden from the render is not in the tree, so
        there is nothing to skip past.
        """
        if self.tree is None:
            return (None, None, None, None)
        return self.tree.ray_cast(origin, direction)

    def object_for(self, index):
        if index is None:
            return None
        if 0 <= index < len(self.triangle_objects):
            return self.triangle_objects[index]
        return None

    def material_for(self, index):
        """Material on the exact evaluated triangle hit by the shared BVH."""
        if index is None:
            return None
        if 0 <= index < len(self.triangle_materials):
            return self.triangle_materials[index]
        return None


def _visible_objects(context, cfg):
    from .. import sceneray_splat

    return sceneray_splat.sr_renderable_mesh_objects(
        context.scene, context.view_layer
    )


def _scene_key(context, objects):
    """Cheap identity for the geometry that would be built."""
    return (
        context.scene.name,
        getattr(context.view_layer, "name", ""),
        tuple(sorted(obj.name for obj in objects)),
    )


def build(context, cfg=None, force=False):
    """The render-visible scene, built or reused from the cache."""
    objects = _visible_objects(context, cfg)
    key = _scene_key(context, objects)
    cached = _cache["scene"]
    if (
        not force
        and cached is not None
        and _cache["key"] == key
        and time.time() - _cache["built_at"] < CACHE_SECONDS
    ):
        return cached

    depsgraph = context.evaluated_depsgraph_get()
    vertices = []
    polygons = []
    triangle_objects = []
    triangle_materials = []
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3

    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        try:
            mesh = evaluated.to_mesh()
        except (RuntimeError, AttributeError):
            continue
        if mesh is None:
            continue
        try:
            mesh.calc_loop_triangles()
            matrix = evaluated.matrix_world
            offset = len(vertices)
            for vertex in mesh.vertices:
                world = matrix @ vertex.co
                vertices.append(world)
                for axis in range(3):
                    if world[axis] < minimum[axis]:
                        minimum[axis] = world[axis]
                    if world[axis] > maximum[axis]:
                        maximum[axis] = world[axis]
            for triangle in mesh.loop_triangles:
                polygons.append(
                    tuple(offset + index for index in triangle.vertices)
                )
                triangle_objects.append(obj)
                material = None
                try:
                    polygon = mesh.polygons[triangle.polygon_index]
                    slot_index = int(polygon.material_index)
                    slots = evaluated.material_slots
                    if 0 <= slot_index < len(slots):
                        material = slots[slot_index].material
                except (AttributeError, IndexError, ReferenceError, RuntimeError):
                    pass
                triangle_materials.append(material)
        finally:
            try:
                evaluated.to_mesh_clear()
            except (RuntimeError, AttributeError):
                pass

    tree = None
    if vertices and polygons:
        tree = BVHTree.FromPolygons(
            [tuple(v) for v in vertices], polygons, all_triangles=True
        )
    if not vertices:
        minimum = maximum = [0.0, 0.0, 0.0]

    scene = RenderVisibleScene(
        tree, triangle_objects, triangle_materials, objects,
        tuple(minimum), tuple(maximum)
    )
    _cache.update({"key": key, "scene": scene, "built_at": time.time()})
    return scene


def invalidate():
    _cache.update({"key": None, "scene": None, "built_at": 0.0})


@bpy.app.handlers.persistent
def _invalidate_on_load(*_args):
    invalidate()


def register():
    if _invalidate_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_invalidate_on_load)


def unregister():
    while _invalidate_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_invalidate_on_load)
    invalidate()
