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
import bmesh
import math
import time
import sys
import random
import json
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Module imports
from .brick import *
from .bricksdict import *
from .common import *
from .general import bounds
from .make_bricks_utils import *
from .mat_utils import *
from .matlist_utils import *
from ..lib.caches import bricker_mesh_cache


@timed_call()
def make_bricks(cm, bricksdict, keys_dict, target_keys, parent, logo, dimensions, action, bcoll, num_source_mats, split=False, brick_scale=None, merge_vertical=True, clear_existing_collection=True, frame_num=None, cursor_status=False, print_status=True, placeholder_meshes=False, run_pre_merge=True, redrawing=False):
    # initialize cmlist attributes (prevents 'update' function for each property from running every time)
    n = cm.source_obj.name
    cm_id = cm.id
    align_bricks = cm.align_bricks
    build_is_dirty = cm.build_is_dirty
    brick_height = cm.brick_height
    brick_type = cm.brick_type
    bricks_and_plates = brick_type == "BRICKS_AND_PLATES"
    circle_verts = min(16, cm.circle_verts) if placeholder_meshes else cm.circle_verts
    custom_meshes = (cm.custom_mesh1, cm.custom_mesh2, cm.custom_mesh3)
    mat_dirty = cm.material_is_dirty or cm.matrix_is_dirty or cm.build_is_dirty
    mat_shell_depth = cm.mat_shell_depth
    custom_mat = cm.custom_mat
    exposed_underside_detail = "FLAT" if placeholder_meshes else cm.exposed_underside_detail
    hidden_underside_detail = "FLAT" if placeholder_meshes else cm.hidden_underside_detail
    instance_method = cm.instance_method
    last_split_model = cm.last_split_model
    legal_bricks_only = cm.legal_bricks_only
    logo_type = "NONE" if placeholder_meshes else cm.logo_type
    logo_scale = cm.logo_scale
    logo_inset = cm.logo_inset
    logo_resolution = cm.logo_resolution
    logo_decimate = cm.logo_decimate
    max_width = cm.max_width
    max_depth = cm.max_depth
    material_type = cm.material_type
    if num_source_mats == 0:
        internal_mat = None
    else:
        internal_mat = cm.internal_mat or bpy.data.materials.get("Bricker_%(n)s_internal" % locals()) or bpy.data.materials.new("Bricker_%(n)s_internal" % locals())
    internal_mat_name = internal_mat.name if internal_mat else ""
    merge_internals = "NEITHER" if material_type == "NONE" else cm.merge_internals
    merge_internals_h = merge_internals in ["BOTH", "HORIZONTAL"]
    merge_internals_v = merge_internals in ["BOTH", "VERTICAL"]
    merge_type = cm.merge_type if mergable_brick_type(brick_type) else "NONE"
    merge_seed = cm.merge_seed
    offset_brick_layers = cm.offset_brick_layers
    random_mat_seed = cm.random_mat_seed
    random_rot = 0 if placeholder_meshes else round(cm.random_rot, 6)
    random_loc = 0 if placeholder_meshes else round(cm.random_loc, 6)
    stud_detail = cm.stud_detail
    zstep = cm.zstep
    brick_type_can_be_merged = mergable_brick_type(brick_type, up=cm.zstep == 1) and (max_depth != 1 or max_width != 1)
    internals_exist = check_if_internals_exist(cm)
    # initialize random states
    rand_s1 = None if placeholder_meshes else np.random.RandomState(cm.merge_seed)  # for brick_size calc
    rand_s2 = None if placeholder_meshes else np.random.RandomState(cm.merge_seed + 1)
    rand_s3 = None if placeholder_meshes else np.random.RandomState(cm.merge_seed + 2)
    # initialize other variables
    lowest_z = -1
    denom = sum([len(keys_dict[z0]) for z0 in keys_dict.keys()])
    # set number of times to run through all keys
    num_iters = 2 if brick_type == "BRICKS_AND_PLATES" else 1
    i = 0
    # if merging unnecessary, skip entirely
    if not run_pre_merge:
        # update bricksdict info since build probably changed
        parent_keys = get_parent_keys(bricksdict, target_keys)
    # if unable to merge brick type, simply update bricksdict values
    elif not brick_type_can_be_merged:
        size = [1, 1, cm.zstep]
        for key in target_keys:
            brick_d = bricksdict[key]
            brick_d["parent"] = "self"
            brick_d["size"] = size.copy()
            set_flipped_and_rotated(brick_d, bricksdict, [key])
            if brick_d["type"] == "SLOPE" and brick_type == "SLOPES":
                set_brick_type_for_slope(brick_d, bricksdict, [key])
    else:
        # initialize progress bar around cursor
        old_percent = update_progress_bars(0.0, -1, "Merging", print_status, cursor_status)

        # reset relevant bricksdict info
        for key0 in target_keys:
            brick_d0 = bricksdict[key0]
            # set all keys as available for merge
            brick_d0["available_for_merge"] = True
            # reset material info for internal keys
            if brick_d0["val"] < 1:
                brick_d0["mat_name"] = ""
                brick_d0["custom_mat_name"] = False


        # run merge operations (twice if flat brick type)
        for time_through in range(num_iters):
            # iterate through z locations in bricksdict (bottom to top)
            for z in sorted(keys_dict.keys()):
                # skip second and third rows on first time through
                if num_iters == 2 and align_bricks:
                    # initialize lowest_z if not done already
                    if lowest_z == -0.1:
                        lowest_z = z
                    if skip_this_row(time_through, lowest_z, z, offset_brick_layers):
                        continue
                # calculate build variations for current z level
                num_bricks = 0
                if merge_type == "RANDOM":
                    random.seed(merge_seed + i)
                    cur_keys = list(keys_dict[z])
                    random.shuffle(cur_keys)
                else:
                    cur_keys = keys_dict[z]
                # iterate through keys on current z level
                for key in cur_keys:
                    i += 1
                    brick_d = bricksdict[key]
                    # skip keys that are already drawn or have attempted merge
                    if brick_d["attempted_merge"] or brick_d["parent"] not in (None, "self"):
                        continue

                    # initialize loc
                    loc = get_dict_loc(bricksdict, key)

                    # merge current brick with available adjacent bricks
                    merge_with_adjacent_bricks(brick_d, bricksdict, key, loc, [1, 1, zstep], zstep, rand_s1, build_is_dirty, brick_type, max_width, max_depth, mat_shell_depth, legal_bricks_only, internal_mat_name, merge_internals_h, merge_internals_v, material_type, merge_vertical=merge_vertical)

                    # print status to terminal and cursor
                    cur_percent = (i / denom)
                    old_percent = update_progress_bars(cur_percent, old_percent, "Merging", print_status, cursor_status)

        # reset all keys as unavailable for merge
        for key0 in target_keys:
            bricksdict[key0]["available_for_merge"] = False

        # end 'Merging' progress bar
        update_progress_bars(1, 0, "Merging", print_status, cursor_status, end=True)

    # get all parent keys
    parent_keys = get_parent_keys(bricksdict, target_keys)

    # reset 'attempted_merge' for all items in bricksdict
    for key0 in bricksdict:
        bricksdict[key0]["attempted_merge"] = False

    # update bricksdict info after build changed
    update_bricksdict_after_updated_build(bricksdict, parent_keys, zstep, cm, material_type, mat_shell_depth, custom_mat, random_mat_seed)

    # begin 'Building' progress bar
    old_percent = update_progress_bars(0.0, -1, "Building", print_status, cursor_status)

    # set up internal material for this object
    mats = list()
    if internal_mat is not None and material_type == "SOURCE" and mat_shell_depth < cm.shell_thickness:
        mats.append(internal_mat)
    elif material_type in ("CUSTOM", "NONE"):
        mats.append(custom_mat)

    # initialize vars for brick drawing
    all_meshes = bmesh.new()
    bricks_created = list()

    # draw merged bricks
    i = 0
    for z in sorted(keys_dict.keys()):
        for k2 in keys_dict[z]:
            i += 1
            if bricksdict[k2]["parent"] != "self":
                continue
            loc = get_dict_loc(bricksdict, k2)
            # create brick based on the current brick info
            draw_brick(cm_id, bricksdict, k2, loc, bcoll, clear_existing_collection, parent, dimensions, zstep, bricksdict[k2]["size"], brick_type, split, custom_meshes, bricks_created, all_meshes, mats, internal_mat, logo, logo_resolution, logo_decimate, logo_type, logo_scale, logo_inset, stud_detail, exposed_underside_detail, hidden_underside_detail, random_rot, random_loc, circle_verts, instance_method, rand_s2, rand_s3)
            # print status to terminal and cursor
            old_percent = update_progress_bars(i / denom, old_percent, "Building", print_status, cursor_status)

    # end progress bars
    update_progress_bars(1, 0, "Building", print_status, cursor_status, end=True)

    # combine meshes to a single object, link to scene, and add relevant data to the new Blender MESH object
    if not split:
        name = "Bricker_%(n)s_bricks" % locals()
        if frame_num is not None:
            name = "%(name)s_f_%(frame_num)s" % locals()
        old_mesh = bpy.data.meshes.get(name)
        m = bpy.data.meshes.new(name)
        if old_mesh and old_mesh.users > 0:
            old_mesh.user_remap(m)
        all_meshes.to_mesh(m)
        apply_brick_mesh_settings(m)
        all_bricks_obj = bpy.data.objects.get(name)
        if all_bricks_obj:
            all_bricks_obj.data = m
        else:
            all_bricks_obj = bpy.data.objects.new(name, m)
            all_bricks_obj.cmlist_id = cm_id
        for mat in mats:
            set_material(all_bricks_obj, mat, overwrite=False)
        # set parent
        all_bricks_obj.parent = parent
        # add bricks obj to scene and bricks_created
        if all_bricks_obj.name not in bcoll.objects.keys():
            bcoll.objects.link(all_bricks_obj)
        bricks_created.append(all_bricks_obj)
        # protect all_bricks_obj from being deleted
        all_bricks_obj.is_brickified_object = True

    return bricks_created


def update_bricksdict_after_updated_build(bricksdict, parent_keys, zstep, cm, material_type, mat_shell_depth, custom_mat, random_mat_seed):
    # update cm.brick_sizes_used and cm.brick_types_used
    for k in parent_keys:
        brick_size = bricksdict[k]["size"]
        brick_size_str = list_to_str(sorted(brick_size[:2]) + [brick_size[2]])
        update_brick_sizes_and_types_used(cm, brick_size_str, bricksdict[k]["type"])

    # set brick exposures
    for k in parent_keys:
        set_brick_exposure(bricksdict, zstep, key=k)

    # set brick materials
    update_mat_names_in_bricksdict(bricksdict, cm, zstep, parent_keys, material_type, mat_shell_depth, custom_mat, random_mat_seed)


def update_mat_names_in_bricksdict(bricksdict, cm, zstep, parent_keys, material_type, mat_shell_depth, custom_mat, random_mat_seed):
    brick_mats = get_brick_mats(cm)
    for k in parent_keys:
        brick_d = bricksdict[k]
        brick_size = brick_d["size"]
        mat_name = get_material_name(bricksdict, k, brick_size, zstep, material_type, mat_shell_depth, custom_mat, random_mat_seed, brick_mats=brick_mats)
        if mat_name:
            loc = get_dict_loc(bricksdict, k)
            keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc)
            for k0 in keys_in_brick:
                bricksdict[k0]["mat_name"] = mat_name
