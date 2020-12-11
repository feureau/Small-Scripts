# Copyright (C) 2020 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
import bpy

# Blender imports
from mathutils import Euler

# Module imports
# from .bevel_bricks import *
from .common import *
from .general import *
from .smoke_sim import *
# from .cmlist_utils import *
# from .logo_obj import *
# from .make_bricks_point_cloud import *
# from .make_bricks import *
from .smoke_cache import *
# from .transform_data import *


def get_duplicate_object(cm, source, created_objects=None):
    source_dup = bpy.data.objects.get(source.name + "__dup__")
    if source_dup is None:
        # duplicate source
        source_dup = duplicate(source, link_to_scene=True)
        source_dup.name = source.name + "__dup__"
        source_dup.stored_parents.clear()
        if cm.use_local_orient:
            source_dup.rotation_mode = "XYZ"
            source_dup.rotation_euler = Euler((0, 0, 0))
        if created_objects is not None:
            created_objects.append(source_dup.name)
        # remove modifiers and constraints
        for mod in source_dup.modifiers:
            source_dup.modifiers.remove(mod)
        for constraint in source_dup.constraints:
            source_dup.constraints.remove(constraint)
        # remove source_dup parent
        if source_dup.parent:
            parent_clear(source_dup)
        # handle smoke
        if cm.is_smoke:
            store_smoke_data(source, source_dup)
        else:
            # send to new mesh
            source_dup.data = new_mesh_from_object(source)
        # apply transformation data
        apply_transform(source_dup)
        source_dup.animation_data_clear()
    # if duplicate not created, source_dup is just original source
    return source_dup or source


def get_duplicate_objects(scn, cm, action, start_frame, stop_frame, updated_frames_only):
    """ returns list of duplicates from source with all traits applied """
    source = cm.source_obj
    n = source.name
    orig_frame = scn.frame_current
    soft_body = False
    smoke = False

    # set cm.armature and cm.physics
    for mod in source.modifiers:
        if mod.type == "ARMATURE":
            cm.armature = True
        elif mod.type in ("CLOTH", "SOFT_BODY"):
            soft_body = True
            point_cache = mod.point_cache
        elif is_smoke_domain(mod):
            smoke = True
            point_cache = mod.domain_settings.point_cache

    # step through uncached frames to run simulation
    if soft_body or smoke:
        first_uncached_frame = get_first_uncached_frame(source, point_cache)
        for cur_frame in range(first_uncached_frame, start_frame):
            scn.frame_set(cur_frame)

    denom = stop_frame - start_frame
    update_progress("Applying Modifiers", 0.0)

    duplicates = {}
    for cur_frame in range(start_frame, stop_frame + 1):
        source_dup_name = "Bricker_%(n)s_f_%(cur_frame)s" % locals()
        # retrieve previously duplicated source if possible
        if action == "UPDATE_ANIM":
            source_dup = bpy.data.objects.get(source_dup_name)
            if source_dup is not None:
                duplicates[cur_frame] = source_dup
                link_object(source_dup)
                continue
        # skip unchanged frames
        if frame_unchanged(updated_frames_only, cm, cur_frame):
            continue
        # set active frame for applying modifiers
        scn.frame_set(cur_frame)
        # duplicate source for current frame
        source_dup = duplicate(source, link_to_scene=True)
        # source_dup.use_fake_user = True
        source_dup.name = source_dup_name
        source_dup.stored_parents.clear()
        # remove modifiers and constraints
        for mod in source_dup.modifiers:
            source_dup.modifiers.remove(mod)
        for constraint in source_dup.constraints:
            source_dup.constraints.remove(constraint)
        # apply parent transformation
        if source_dup.parent:
            parent_clear(source_dup)
        # apply animated transform data
        source_dup.matrix_world = source.matrix_world
        source_dup.animation_data_clear()
        # handle smoke
        if smoke:
            store_smoke_data(source, source_dup)
        else:
            # send to new mesh
            source_dup.data = new_mesh_from_object(source)
        # apply transform data
        apply_transform(source_dup)
        # store duplicate to dictionary of dupes
        duplicates[cur_frame] = source_dup
        # update progress bar
        percent = (cur_frame - start_frame + 1) / (denom + 1)
        if percent < 1:
            update_progress("Applying Modifiers", percent)
    # update progress bar
    scn.frame_set(orig_frame)
    depsgraph_update()
    update_progress("Applying Modifiers", 1)
    return duplicates


def frame_unchanged(updated_frames_only, cm, cur_frame):
    return updated_frames_only and cm.last_start_frame <= cur_frame and cur_frame <= cm.last_stop_frame


def update_bool_dupes(cm):
    dupes = set()
    for bool in cm.booleans:
        if bool.type != "OBJECT" or bool.object is None:
            continue
        bool.object_dup = get_duplicate_object(cm, bool.object)
        safe_link(bool.object_dup)
        dupes.add(bool.object_dup)
    return dupes
