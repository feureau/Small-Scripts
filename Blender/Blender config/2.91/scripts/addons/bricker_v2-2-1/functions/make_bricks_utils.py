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
import copy
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Module imports
from .brick import *
from .bricksdict import *
from .common import *
from .general import *
from .hash_object import hash_object
from .mat_utils import *
from ..lib.caches import bricker_mesh_cache


def draw_brick(cm_id, bricksdict, key, loc, bcoll, clear_existing_collection, parent, dimensions, zstep, brick_size, brick_type, split, custom_meshes, bricks_created, all_meshes, mats, internal_mat, logo, logo_resolution, logo_decimate, logo_type, logo_scale, logo_inset, stud_detail, exposed_underside_detail, hidden_underside_detail, random_rot, random_loc, circle_verts, instance_method, rand_s2, rand_s3):
    """ draws current brick in bricksdict """

    # set up arguments for brick mesh
    brick_d = bricksdict[key]
    use_stud = (brick_d["top_exposed"] and stud_detail != "NONE") or stud_detail == "ALL"
    logo_to_use = logo if use_stud else None
    underside_detail = exposed_underside_detail if brick_d["bot_exposed"] else hidden_underside_detail

    ### CREATE BRICK ###

    # add brick with new mesh data at original location
    if brick_d["type"].startswith("CUSTOM"):
        m = custom_meshes[int(brick_d["type"][-1]) - 1]
    else:
        # get brick mesh
        m = get_brick_data(brick_d, dimensions, brick_type, brick_size, circle_verts, underside_detail, use_stud, logo_to_use, logo_type, logo_inset, logo_scale, logo_resolution, logo_decimate, rand_s3)
    # duplicate data if not instancing by mesh data
    m = m if instance_method == "LINK_DATA" else m.copy()
    # apply random rotation to edit mesh according to parameters
    random_rot_matrix = get_random_rot_matrix(random_rot, rand_s2, brick_size)
    # get brick location
    loc_offset = get_random_loc(random_loc, rand_s2, dimensions["half_width"], dimensions["half_height"])
    brick_loc = get_brick_center(bricksdict, key, zstep, loc) + loc_offset
    # get brick material
    mat = bpy.data.materials.get(brick_d["mat_name"])
    if mat is None:
        mat = internal_mat

    if split:
        brick = bpy.data.objects.get(brick_d["name"])
        if brick:
            # NOTE: last brick object is left in memory (faster)
            # set brick.data to new mesh (resets materials)
            brick.data = m
        else:
            # create new object with mesh data
            brick = bpy.data.objects.new(brick_d["name"], m)
            brick.cmlist_id = cm_id
        # rotate brick by random rotation
        if random_rot_matrix is not None:
            # resets rotation_euler in case object is reused
            brick.rotation_euler = (0, 0, 0)
            brick.rotation_euler.rotate(random_rot_matrix)
        # set brick location
        brick.location = brick_loc
        # set brick material
        set_material(brick, mat)
        # append to bricks_created
        bricks_created.append(brick)
        # set remaining brick info if brick object just created
        brick.parent = parent
        if not brick.is_brick:
            brick.is_brick = True
        # link bricks to brick collection
        if clear_existing_collection or brick.name not in bcoll.objects.keys():
            bcoll.objects.link(brick)
    else:
        # duplicates mesh – prevents crashes in 2.79 (may need to add back if experiencing crashes in b280)
        if not b280():
            m = m.copy()
        # apply rotation matrices to edit mesh
        if random_rot_matrix is not None:
            m.transform(random_rot_matrix)
        # transform brick mesh to coordinate on matrix
        m.transform(Matrix.Translation(brick_loc))

        # keep track of mats already used
        if mat in mats:
            mat_idx = mats.index(mat)
        elif mat is not None:
            mats.append(mat)
            mat_idx = len(mats) - 1

        # set material
        if mat is not None:
            # point all polygons to target material (index will correspond in all_meshes object)
            for p in m.polygons:
                p.material_index = mat_idx

        # append mesh to all_meshes bmesh object
        all_meshes.from_mesh(m)

        # remove mesh in 2.79 (mesh was duplicated above to prevent crashes)
        if not b280():
            bpy.data.meshes.remove(m)
        # NOTE: The following lines clean up the mesh if not duplicated
        else:
            # reset polygon material mapping
            if mat is not None:
                for p in m.polygons:
                    p.material_index = 0

            # reset transformations for reference mesh
            m.transform(Matrix.Translation(-brick_loc))
            if random_rot_matrix is not None:
                random_rot_matrix.invert()
                m.transform(random_rot_matrix)

    return bricksdict


def merge_with_adjacent_bricks(brick_d, bricksdict, key, loc, default_size, zstep, rand_s1, build_is_dirty, brick_type, max_width, max_depth, mat_shell_depth, legal_bricks_only, internal_mat_name, merge_internals_h, merge_internals_v, material_type, merge_vertical=True):
    brick_size = brick_d["size"]
    if (brick_size is None or build_is_dirty) and brick_type != "CUSTOM":
        prefer_largest = 0 < brick_d["val"] < 1
        axis_sort_order = [2, 0, 1] if rand_s1 is not None and rand_s1.randint(0, 2) else [2, 1, 0]
        brick_size, _, keys_in_brick = attempt_pre_merge(bricksdict, key, default_size, zstep, brick_type, max_width, max_depth, mat_shell_depth, legal_bricks_only, internal_mat_name, merge_internals_h, merge_internals_v, material_type, axis_sort_order=axis_sort_order, loc=loc, prefer_largest=prefer_largest, merge_vertical=merge_vertical)
    else:
        keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc=loc)
    return brick_size, keys_in_brick


def skip_this_row(time_through, lowest_z, z, offset_brick_layers):
    if time_through == 0:  # first time
        if (z - offset_brick_layers - lowest_z) % 3 in (1, 2):
            return True
    else:  # second time
        if (z - offset_brick_layers - lowest_z) % 3 == 0:
            return True
    return False


def get_random_loc(random_loc, rand, half_width, half_height):
    """ get random location between (0,0,0) and (width/2, width/2, height/2) """
    loc = Vector((0,0,0))
    if random_loc > 0:
        loc.xy = [rand.uniform(-half_width * random_loc, half_width * random_loc)] * 2
        loc.z = rand.uniform(-half_height * random_loc, half_height * random_loc)
    return loc


def get_random_rot_matrix(random_rot, rand, brick_size):
    """ get rotation matrix randomized by random_rot """
    if random_rot == 0:
        return None
    x, y, z = get_random_rot_angle(random_rot, rand, brick_size)
    # get rotation matrix
    x_mat = Matrix.Rotation(x, 4, "X")
    y_mat = Matrix.Rotation(y, 4, "Y")
    z_mat = Matrix.Rotation(z, 4, "Z")
    combined_mat = mathutils_mult(x_mat, y_mat, z_mat)
    return combined_mat


def get_random_rot_angle(random_rot, rand, brick_size):
    """ get rotation angles randomized by random_rot """
    if random_rot == 0:
        return None
    denom = 0.75 if max(brick_size) == 0 else brick_size[0] * brick_size[1]
    mult = random_rot / denom
    # calculate rotation angles in radians
    x = rand.uniform(-math.radians(11.25) * mult, math.radians(11.25) * mult)
    y = rand.uniform(-math.radians(11.25) * mult, math.radians(11.25) * mult)
    z = rand.uniform(-math.radians(45)    * mult, math.radians(45)    * mult)
    return x, y, z


def apply_brick_mesh_settings(m):
    # set texture space
    m.use_auto_texspace = False
    m.texspace_size = (1, 1, 1)
    # use auto normal smoothing (equivalent to edge split modifier)
    m.use_auto_smooth = True
    m.auto_smooth_angle = math.radians(44)
    m.update()


def get_brick_data(brick_d, dimensions, brick_type, brick_size=(1, 1, 1), circle_verts=16, underside_detail="FLAT", use_stud=True, logo_to_use=None, logo_type=None, logo_inset=None, logo_scale=None, logo_resolution=None, logo_decimate=None, rand=None):
    # get bm_cache_string
    bm_cache_string = ""
    if "CUSTOM" not in brick_type:
        custom_logo_used = logo_to_use is not None and logo_type == "CUSTOM"
        bm_cache_string = marshal.dumps((
            dimensions["height"], brick_size, underside_detail,
            logo_resolution if logo_to_use is not None else None,
            logo_decimate if logo_to_use is not None else None,
            logo_inset if logo_to_use is not None else None,
            hash_object(logo_to_use) if custom_logo_used else None,
            logo_scale if custom_logo_used else None,
            logo_type, use_stud, circle_verts,
            brick_d["type"], dimensions["gap"],
            brick_d["flipped"] if brick_d["type"] in ("SLOPE", "SLOPE_INVERTED") else None,
            brick_d["rotated"] if brick_d["type"] in ("SLOPE", "SLOPE_INVERTED") else None,
        )).hex()

    # NOTE: Stable implementation for Blender 2.79
    # check for bmesh in cache
    bms = bricker_mesh_cache.get(bm_cache_string)
    # if not found create new brick mesh(es) and store to cache
    if bms is None:
        # create new brick bmeshes
        bms = new_brick_mesh(dimensions, brick_type, size=brick_size, type=brick_d["type"], flip=brick_d["flipped"], rotate90=brick_d["rotated"], logo=logo_to_use, logo_type=logo_type, logo_scale=logo_scale, logo_inset=logo_inset, all_vars=logo_to_use is not None, underside_detail=underside_detail, stud=use_stud, circle_verts=circle_verts)
        # store newly created meshes to cache
        if brick_type != "CUSTOM":
            bricker_mesh_cache[bm_cache_string] = bms
    # create edit mesh for each bmesh
    meshes = []
    for i,bm in enumerate(bms):
        # check for existing edit mesh in blendfile data
        bmcs_hash = hash_str(bm_cache_string)
        mesh_name = "%(bmcs_hash)s_%(i)s" % locals()
        m = bpy.data.meshes.get(mesh_name)
        # create new edit mesh and send bmesh data to it
        if m is None:
            m = bpy.data.meshes.new(mesh_name)
            bm.to_mesh(m)
            # center mesh origin
            center_mesh_origin(m, dimensions, brick_size)
            # apply brick mesh settings
            apply_brick_mesh_settings(m)
        meshes.append(m)
    # # TODO: Try the following code instead in Blender 2.8 – see if it crashes with the following steps:
    # #     Open new file
    # #     Create new bricker model and Brickify with default settings
    # #     Delete the brickified model with the 'x > OK?' shortcut
    # #     Undo with 'ctrl + z'
    # #     Enable 'Update Model' button by clicking on and off of 'Gap Between Bricks'
    # #     Press 'Update Model'
    # # check for bmesh in cache
    # meshes = bricker_mesh_cache.get(bm_cache_string)
    # # if not found create new brick mesh(es) and store to cache
    # if meshes is None:
    #     # create new brick bmeshes
    #     bms = new_brick_mesh(dimensions, brick_type, size=brick_size, type=brick_d["type"], flip=brick_d["flipped"], rotate90=brick_d["rotated"], logo=logo_to_use, logo_type=logo_type, logo_scale=logo_scale, logo_inset=logo_inset, all_vars=logo_to_use is not None, underside_detail=underside_detail, stud=use_stud, circle_verts=circle_verts)
    #     # create edit mesh for each bmesh
    #     meshes = []
    #     for i,bm in enumerate(bms):
    #         # check for existing edit mesh in blendfile data
    #         bmcs_hash = hash_str(bm_cache_string)
    #         mesh_name = "%(bmcs_hash)s_%(i)s" % locals()
    #         m = bpy.data.meshes.get(mesh_name)
    #         # create new edit mesh and send bmesh data to it
    #         if m is None:
    #             m = bpy.data.meshes.new(mesh_name)
    #             bm.to_mesh(m)
    #             # center mesh origin
    #             center_mesh_origin(m, dimensions, brick_size)
    #         meshes.append(m)
    #     # store newly created meshes to cache
    #     if brick_type != "CUSTOM":
    #         bricker_mesh_cache[bm_cache_string] = meshes

    # pick edit mesh randomly from options
    rand = np.random.RandomState(0) if rand is None else rand
    m0 = meshes[rand.randint(0, len(meshes))] if len(meshes) > 1 else meshes[0]

    return m0


def update_brick_sizes_and_types_used(cm, sz, typ):
    bsu = cm.brick_sizes_used
    btu = cm.brick_types_used
    cm.brick_sizes_used += sz if bsu == "" else ("|%(sz)s" % locals() if sz not in bsu else "")
    cm.brick_types_used += typ if btu == "" else ("|%(typ)s" % locals() if typ not in btu else "")


def get_parent_keys(bricksdict:dict, keys:list=None):
    keys = keys or bricksdict.keys()
    parent_keys = [k for k in keys if bricksdict[k]["parent"] == "self" and bricksdict[k]["draw"]]
    return parent_keys


def get_parent_keys_internal(bricksdict:dict, zstep:int, keys:list=None):
    parent_keys = get_parent_keys(bricksdict, keys)
    internal_keys = list()
    for k in parent_keys:
        keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[k]["size"], zstep, key=k)
        if not any(bricksdict[k0]["val"] == 1 for k0 in keys_in_brick):
            internal_keys.append(k)
    return internal_keys


def generate_brick_object(brick_name="New Brick", brick_size=(1, 1, 1)):
    scn, cm, n = get_active_context_info()
    brick_d = create_bricksdict_entry(
        name=brick_name,
        loc=(1, 1, 1),
        val=1,
        draw=True,
        b_type=get_brick_type(cm.brick_type),
    )
    rand = np.random.RandomState(cm.merge_seed)
    dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
    use_stud = cm.stud_detail != "NONE"
    logo_to_use = get_logo(scn, cm, dimensions) if use_stud and cm.logo_type != "NONE" else None
    m = get_brick_data(brick_d, dimensions, cm.brick_type, brick_size, cm.circle_verts, cm.exposed_underside_detail, use_stud, logo_to_use, cm.logo_type, cm.logo_inset, None, cm.logo_resolution, cm.logo_decimate, rand)
    brick = bpy.data.objects.new(brick_name, m)
    return brick
