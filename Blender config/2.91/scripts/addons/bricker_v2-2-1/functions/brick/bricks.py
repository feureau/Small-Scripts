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
import bmesh
import random
import time
import numpy as np
from statistics import mean

# Blender imports
from mathutils import Vector, Matrix

# Module imports
from .mesh_generators import *
from .types import *
from ..common import *
from ..general import *

def new_brick_mesh(dimensions:list, brick_type:str, size:list=[1,1,3], type:str="STANDARD", flip:bool=False, rotate90:bool=False, logo=False, logo_type="NONE", logo_scale=100, logo_inset=None, all_vars=False, underside_detail:str="FLAT", stud:bool=True, circle_verts:int=16):
    """ create unlinked Brick at origin """
    # create brick mesh
    if type == "STANDARD" or "CUSTOM" in type:
        brick_bm = make_standard_brick(dimensions, size, type, brick_type, circle_verts=circle_verts, detail=underside_detail, stud=stud)
    elif type in get_round_brick_types():
        brick_bm = make_round_1x1(dimensions, brick_type, circle_verts=circle_verts, type=type, detail=underside_detail)
    elif type in ("TILE", "TILE_GRILL"):
        brick_bm = make_tile(dimensions, brick_type, brick_size=size, circle_verts=circle_verts, type=type, detail=underside_detail)
    elif type in ("SLOPE", "SLOPE_INVERTED", "TALL_SLOPE"):
        # determine brick direction
        directions = ["X+", "Y+", "X-", "Y-"]
        max_idx = size.index(max(size[:2]))
        max_idx -= 2 if flip else 0
        max_idx += 1 if rotate90 else 0
        # make slope brick bmesh
        if type == "SLOPE_INVERTED":
            brick_bm = make_inverted_slope(dimensions, size, brick_type, circle_verts=circle_verts, direction=directions[max_idx], detail=underside_detail, stud=stud)
        else:
            brick_bm = make_slope(dimensions, size, brick_type, circle_verts=circle_verts, direction=directions[max_idx], detail=underside_detail, stud=stud)
    else:
        raise ValueError("'new_mesh' function received unrecognized value for parameter 'type': '" + str(type) + "'")

    # send brick mesh to junk edit mesh
    junk_m = junk_mesh("Bricker_junk_mesh")
    brick_bm.to_mesh(junk_m)

    # set bevel weights
    junk_m.use_customdata_edge_bevel = True
    for e in junk_m.edges:
        e.bevel_weight = 0.0 if e.select else 1.0

    # create list of bmesh variations (logo only, for now)
    if logo and stud and (type in ("STANDARD", "STUD", "SLOPE_INVERTED") or type == "SLOPE" and max(size[:2]) != 1):
        bms = make_logo_variations(dimensions, size, brick_type, directions[max_idx] if type.startswith("SLOPE") else "", all_vars, logo, logo_inset, logo_type, logo_scale)
    else:
        bms = [bmesh.new()]

    # append brick mesh to each bmesh variation
    for bm in bms:
        bm.from_mesh(junk_m)

    # return bmesh objects
    return bms


def split_bricks(bricksdict, zstep, keys):
    for key in keys:
        brick_d = bricksdict[key]
        # set all bricks as unmerged
        if brick_d["draw"]:
            brick_d["parent"] = "self"
            brick_d["size"] = [1, 1, zstep]


def split_brick(bricksdict, parent_key, zstep, brick_type, loc=None, v=True, h=True):
    """split brick vertically and/or horizontally

    Keyword Arguments:
    bricksdict -- Matrix of bricks in model
    parent_key -- parent key for brick in matrix
    zstep      -- passing cm.zstep through
    brick_type -- passing cm.brick_type through
    loc        -- xyz location of brick in matrix
    v          -- split brick vertically (into pancakes)
    h          -- split brick horizontally (into columns)
    """
    # set up unspecified paramaters
    loc = loc or get_dict_loc(bricksdict, parent_key)
    # initialize vars
    parent_brick_d = bricksdict[parent_key]
    assert parent_brick_d["parent"] == "self"
    target_type = get_brick_type(brick_type)
    size = parent_brick_d["size"]
    new_size = [1, 1, size[2]]
    if flat_brick_type(brick_type):
        if not v:
            zstep = 3
        else:
            new_size[2] = 1
    if not h:
        new_size[0] = size[0]
        new_size[1] = size[1]
    # split brick into individual bricks
    keys_in_brick = get_keys_in_brick(bricksdict, size, zstep, loc=loc)
    for cur_key in keys_in_brick:
        brick_d = bricksdict[cur_key]
        # if only splitting vertically, update 'parent' values all relevant new plates (skips lowest layer and plates above original source)
        if not h and brick_d["loc"][:2] != loc[:2]:
            brick_d["parent"] = list_to_str(loc[:2] + [brick_d["loc"][2]])
            continue
        brick_d["size"] = new_size.copy()
        brick_d["type"] = get_tall_type(brick_d, target_type) if new_size[2] == 3 else get_short_type(brick_d, target_type)
        brick_d["parent"] = "self"
        brick_d["top_exposed"] = parent_brick_d["top_exposed"]
        brick_d["bot_exposed"] = parent_brick_d["bot_exposed"]
    return keys_in_brick


def get_details_and_bounds(obj, cm=None):
    """ returns dimensions and bounds of object """
    cm = cm or get_active_context_info()[1]
    obj_details = bounds(obj)
    dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
    return obj_details, dimensions


def get_brick_dimensions(height=1, z_scale=1, gap_percentage=0.5):
    """
    returns the dimensions of a brick in Blender units

    Keyword Arguments:
    height         -- height of a standard brick in Blender units
    z_scale         -- height of the brick in plates (1: standard plate, 3: standard brick)
    gap_percentage -- gap between bricks relative to brick height
    """

    scale = height / 9.6
    dimensions = {}
    dimensions["height"] = scale * 9.6 * (z_scale / 3)
    dimensions["half_height"] = dimensions["height"] / 2
    dimensions["width"] = scale * 8
    dimensions["half_width"] = dimensions["width"] / 2
    dimensions["gap"] = scale * 9.6 * (gap_percentage / 100)
    dimensions["stud_height"] = scale * 1.8
    dimensions["stud_radius"] = scale * 2.4
    dimensions["thickness"] = scale * 1.6
    dimensions["stud_z_thickness"] = scale * 0.2
    dimensions["stud_cutout_height"] = dimensions["stud_height"] - dimensions["stud_z_thickness"]
    dimensions["stud_cutout_radius"] = scale * 1.2
    dimensions["tube_thickness"] = scale * 0.855
    dimensions["support_width"] = scale * 0.8
    dimensions["support_height"] = dimensions["height"] * 0.65
    dimensions["slope_support_width"] = scale * 0.6  # eyeballed
    dimensions["slope_support_height"] = scale * 2.4  # eyeballed
    dimensions["bar_radius"] = scale * 1.6
    dimensions["logo_width"] = scale * 4.8 # originally scale * 3.74
    dimensions["tick_width"] = scale * 0.6
    dimensions["tick_depth"] = scale * 0.3
    dimensions["slope_tick_depth"] = scale * 0.375
    dimensions["slit_height"] = scale * 0.3
    dimensions["slit_depth"] = scale * 0.3
    dimensions["oblong_support_dist"] = scale
    dimensions["oblong_support_radius"] = scale * 0.6
    dimensions["support_height_triple"] = (dimensions["height"] * 3) * 0.65
    dimensions["logo_offset"] = dimensions["half_height"] + dimensions["stud_height"]
    # round all values in dimensions
    for k in dimensions:
        dimensions[k] = round(dimensions[k], 8)

    return dimensions


def is_on_shell(bricksdict, key, loc=None, zstep=None, shell_depth=1):
    """ check if any locations in brick are on the shell """
    size = bricksdict[key]["size"]
    loc = loc or get_dict_loc(bricksdict, key)
    brick_keys = get_keys_in_brick(bricksdict, size, zstep, loc=loc)
    for k in brick_keys:
        if bricksdict[k]["val"] >= 1 - (shell_depth - 1) / 100:
            return True
    return False


def get_brick_center(bricksdict, key, zstep=1, loc=None):
    loc = loc or get_dict_loc(bricksdict, key)
    brick_keys = get_keys_in_brick(bricksdict, bricksdict[key]["size"], zstep, loc=loc)
    coords = [bricksdict[k0]["co"] for k0 in brick_keys]
    coord_ave = Vector((mean([co[0] for co in coords]), mean([co[1] for co in coords]), mean([co[2] for co in coords])))
    return coord_ave


def get_num_rots(direction, size):
    return 1 if direction != "" else (4 if size[0] == 1 and size[1] == 1 else 2)


def get_rod_add(direction, size):
    if direction != "":
        directions = ["X+", "Y+", "X-", "Y-"]
        rot_add = 90 * (directions.index(direction) + 1)
    else:
        rot_add = 180 if (size[0] == 2 and size[1] > 2) or (size[0] == 1 and size[1] > 1) else 90
    return rot_add


def make_logo_variations(dimensions, size, brick_type, direction, all_vars, logo, logo_inset, logo_type, logo_scale):
    # get logo rotation angle based on size of brick
    rot_vars = get_num_rots(direction, size)
    rot_mult = 90 if size[0] == 1 and size[1] == 1 else 180
    rot_add = get_rod_add(direction, size)
    # set z_rot to random rotation angle
    if all_vars:
        z_rots = [i * rot_mult + rot_add for i in range(rot_vars)]
    else:
        random_seed = int(time.time()*10**6) % 10000
        rand_s0 = np.random.RandomState(random_seed)
        z_rots = [rand_s0.randint(0,rot_vars) * rot_mult + rot_add]
    # get duplicate of logo mesh
    m = logo.data.copy()

    # create new bmeshes for each logo variation
    bms = [bmesh.new() for z_rot in z_rots]
    # get loc offsets
    z_offset = dimensions["logo_offset"] + (dimensions["height"] if flat_brick_type(brick_type) and size[2] == 3 else 0)
    lw = dimensions["logo_width"] * (0.78 if logo_type == "LEGO" else (logo_scale / 100))
    dist_max = max(logo.dimensions.xy)
    z_offset += ((logo.dimensions.z * (lw / dist_max)) / 2) * (1 - logo_inset / 50)
    xy_offset = dimensions["width"] + dimensions["gap"]
    # cap x/y ranges so logos aren't created over slopes
    x_range_start = size[0] - 1 if direction == "X-" else 0
    y_range_start = size[1] - 1 if direction == "Y-" else 0
    x_range_end = 1 if direction == "X+" else size[0]
    y_range_end = 1 if direction == "Y+" else size[1]
    # add logos on top of each stud
    for i,z_rot in enumerate(z_rots):
        m0 = m.copy()
        # rotate logo around stud
        if z_rot != 0: m0.transform(Matrix.Rotation(math.radians(z_rot), 4, 'Z'))
        # create logo for each stud and append to bm
        gap_base = dimensions["gap"] * Vector(((x_range_end - x_range_start - 1) / 2, (y_range_end - y_range_start - 1) / 2))
        for x in range(x_range_start, x_range_end):
            for y in range(y_range_start, y_range_end):
                # create duplicate of rotated logo
                m1 = m0.copy()
                # adjust gap based on distance from first stud
                gap = gap_base + dimensions["gap"] * Vector((x / x_range_end, y / y_range_end))
                # translate logo into place
                m1.transform(Matrix.Translation((x * xy_offset - gap.x, y * xy_offset - gap.y, z_offset)))
                # add transformed mesh to bm mesh
                bms[i].from_mesh(m1)
                bpy.data.meshes.remove(m1)
        bpy.data.meshes.remove(m0)
    return bms
