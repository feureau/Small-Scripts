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
# NONE!

# Blender imports
import bpy

# Module imports
from .exposure import *
from .getters import *
from .merge_utils import *
from ..mat_utils import *
from ..matlist_utils import *
from ..brick import *


def update_materials(bricksdict, source_dup, keys, cur_frame=None, action="CREATE"):
    """ sets all mat_names in bricksdict based on near_face """
    scn, cm, n = get_active_context_info()
    use_uv_map = cm.use_uv_map and (len(source_dup.data.uv_layers) > 0 or cm.uv_image is not None)
    # initialize variables
    is_smoke = cm.is_smoke
    material_type = cm.material_type
    mat_shell_depth = cm.mat_shell_depth
    color_snap = cm.color_snap
    uv_image = cm.uv_image
    include_transparency = cm.include_transparency
    trans_weight = cm.transparent_weight
    sss = cm.color_snap_sss
    sssSat = cm.color_snap_sss_saturation
    sat_mat = get_saturation_matrix(sssSat)
    specular = cm.color_snap_specular
    roughness = cm.color_snap_roughness
    ior = cm.color_snap_ior
    transmission = cm.color_snap_transmission
    displacement = cm.color_snap_displacement
    color_depth = cm.color_depth if color_snap == "RGB" else 0
    blur_radius = cm.blur_radius if color_snap == "RGB" else 0
    use_abs_template = cm.use_abs_template and brick_materials_installed()
    last_use_abs_template = cm.last_use_abs_template and brick_materials_installed()
    rgba_vals = []
    # get original mat_names, and populate rgba_vals
    for key in keys:
        brick_d = bricksdict[key]
        # skip irrelevant bricks
        nf = brick_d["near_face"]
        if not brick_d["draw"] or (nf is None and not is_smoke) or (brick_d["custom_mat_name"] and is_mat_shell_val(brick_d["val"], mat_shell_depth)):
            continue
        # get RGBA value at nearest face intersection
        if is_smoke:
            rgba = brick_d["rgba"]
            mat_name = ""
        else:
            ni = Vector(brick_d["near_intersection"])
            rgba, mat_name = get_brick_rgba(source_dup, nf, ni, uv_image, color_depth=color_depth, blur_radius=blur_radius)

        if material_type == "SOURCE":
            # get material with snapped RGBA value
            if rgba is None and use_uv_map:
                mat_name = ""
            elif color_snap == "ABS":
                # if original material was ABS plastic, keep it
                if rgba is None and mat_name in get_colors().keys():
                    pass
                # otherwise, find nearest ABS plastic material to rgba value
                else:
                    mat_obj = get_mat_obj(cm, typ="ABS")
                    assert len(mat_obj.data.materials) > 0
                    mat_name = find_nearest_brick_color_name(rgba, trans_weight, mat_obj)
            elif color_snap == "RGB" or is_smoke:# or use_uv_map:
                mat_name = create_new_material(n, rgba, rgba_vals, sss, sat_mat, specular, roughness, ior, transmission, displacement, use_abs_template, last_use_abs_template, include_transparency, cur_frame)
            if rgba is not None:
                rgba_vals.append(rgba)
        elif material_type == "CUSTOM":
            mat_name = cm.custom_mat.name
        brick_d["mat_name"] = mat_name
    # clear unused materials (left over from previous model)
    mat_name_start = "Bricker_{n}{f}".format(n=n, f="f_%(cur_frame)s" % locals() if cur_frame else "")
    cur_mats = [mat for mat in bpy.data.materials if mat.name.startswith(mat_name_start)]
    # for mat in cur_mats:
    #     if mat.users == 0:
    #         bpy.data.materials.remove(mat)
    #     # else:
    #     #     rgba_vals.append(mat.diffuse_color)
    return bricksdict


def update_brick_sizes(bricksdict, key, loc, brick_sizes, zstep, max_L, height_3_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats=False, merge_vertical=False, mult=(1, 1, 1)):
    """ update 'brick_sizes' with available brick sizes surrounding bricksdict[key] """
    if not merge_vertical:
        max_L[2] = 1
    new_max1 = max_L[1]
    new_max2 = max_L[2]
    break_outer1 = False
    break_outer2 = False
    brick_mat_name = bricksdict[key]["mat_name"]
    # iterate in x direction
    for i in range(max_L[0]):
        # iterate in y direction
        for j in range(max_L[1]):
            # break case 1
            if j >= new_max1: break
            # break case 2
            key1 = list_to_str((loc[0] + (i * mult[0]), loc[1] + (j * mult[1]), loc[2]))
            brick_available, brick_mat_name = brick_avail(bricksdict, key1, brick_mat_name, merge_internals_h, material_type, merge_inconsistent_mats)
            if not brick_available:
                if j == 0: break_outer2 = True
                else:      new_max1 = j
                break
            # else, check vertically
            for k in range(0, max_L[2], zstep):
                # break case 1
                if k >= new_max2: break
                # break case 2
                key2 = list_to_str((loc[0] + (i * mult[0]), loc[1] + (j * mult[1]), loc[2] + (k * mult[2])))
                brick_available, brick_mat_name = brick_avail(bricksdict, key2, brick_mat_name, merge_internals_v, material_type, merge_inconsistent_mats)
                if not brick_available:
                    if k == 0: break_outer1 = True
                    else:      new_max2 = k
                    break
                # bricks with 2/3 height can't exist
                elif k == 1: continue
                # else, append current brick size to brick_sizes
                else:
                    new_size = [(i+1) * mult[0], (j+1) * mult[1], (k+zstep) * mult[2]]
                    if new_size in brick_sizes:
                        continue
                    if not (abs(new_size[2]) == 1 and height_3_only):
                        brick_sizes.append(new_size)
            if break_outer1: break
        break_outer1 = False
        if break_outer2: break


def attempt_pre_merge(bricksdict, key, default_size, zstep, brick_type, max_width, max_depth, mat_shell_depth, legal_bricks_only, internal_mat_name, merge_internals_h, merge_internals_v, material_type, loc=None, axis_sort_order=(2, 0, 1), merge_inconsistent_mats=False, prefer_largest=False, direction_mult=(1, 1, 1), merge_vertical=True, target_type=None, height_3_only=False):
    """ attempt to merge bricksdict[key] with adjacent bricks (assuming available keys are all 1x1s) """
    assert brick_type != "CUSTOM"
    # get loc from key
    loc = loc or get_dict_loc(bricksdict, key)
    brick_sizes = [default_size]
    brick_size = default_size
    keys_in_brick = {key}
    tall_type = get_tall_type(bricksdict[key], target_type)
    short_type = get_short_type(bricksdict[key], target_type)

    # check width-depth and depth-width
    for i in (1, -1) if max_width != max_depth else [1]:
        # iterate through adjacent locs to find available brick sizes
        update_brick_sizes(bricksdict, key, loc, brick_sizes, zstep, [max_width, max_depth][::i] + [3], height_3_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats, merge_vertical=merge_vertical, mult=direction_mult)
    # get largest (legal, if checked) brick size found
    brick_sizes.sort(key=lambda v: -abs(v[0] * v[1] * v[2]) if prefer_largest else (-abs(v[axis_sort_order[0]]), -abs(v[axis_sort_order[1]]), -abs(v[axis_sort_order[2]])))
    target_brick_size = next((sz for sz in brick_sizes if not (legal_bricks_only and not is_legal_brick_size(size=[abs(v) for v in sz], type=tall_type if abs(sz[2]) == 3 else short_type, mat_name=get_most_frequent_mat_name(bricksdict, *get_new_parent_key_loc_and_size_flipped(sz, loc, zstep)[::2], zstep, mat_shell_depth), internal_mat_name=internal_mat_name))))
    assert target_brick_size is not None
    # get new brick_size, loc, and key for largest brick size
    key, loc, brick_size = get_new_parent_key_loc_and_size_flipped(target_brick_size, loc, zstep)
    # update bricksdict for keys merged together
    keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc=loc)
    update_merged_keys_in_bricksdict(bricksdict, key, keys_in_brick, brick_size, brick_type, short_type, tall_type, set_attempted_merge=True)

    return brick_size, key, keys_in_brick


def reset_bricksdict_entries(bricksdict, keys, force_outside=False):
    for k in keys:
        brick_d = bricksdict[k]
        brick_d["draw"] = False
        if force_outside:
            brick_d["val"] = 0
        else:
            set_brick_val(bricksdict, get_dict_loc(bricksdict, k), k, action="REMOVE")
        brick_d["size"] = None
        brick_d["parent"] = None
        brick_d["flipped"] = False
        brick_d["rotated"] = False
        brick_d["bot_exposed"] = None
        brick_d["top_exposed"] = None
        brick_d["created_from"] = None
        brick_d["custom_mat_name"] = None


def set_brick_val(bricksdict, loc=None, key=None, action="ADD"):
    assert loc or key
    loc = loc or get_dict_loc(bricksdict, key)
    key = key or list_to_str(loc)
    adj_keys = get_adj_keys(bricksdict, loc=loc)
    adj_brick_vals = [bricksdict[k]["val"] for k in adj_keys]
    if action == "ADD" and (0 in adj_brick_vals or len(adj_brick_vals) < 6 or min(adj_brick_vals) == 1):
        new_val = 1
    elif action == "REMOVE":
        new_val = 0 if 0 in adj_brick_vals or len(adj_brick_vals) < 6 else (max(adj_brick_vals) - 0.01)
    else:
        new_val = max(adj_brick_vals) - 0.01
    bricksdict[key]["val"] = new_val
    return new_val


def get_adj_keys(bricksdict, loc=None, key=None):
    assert loc or key
    x, y, z = loc or get_dict_loc(bricksdict, key)
    adj_keys = set((
        list_to_str((x+1, y, z)),
        list_to_str((x-1, y, z)),
        list_to_str((x, y+1, z)),
        list_to_str((x, y-1, z)),
        list_to_str((x, y, z+1)),
        list_to_str((x, y, z-1)),
    ))
    for k in adj_keys.copy():
        if bricksdict.get(k) is None:
            adj_keys.remove(k)
    return adj_keys


def update_merged_keys_in_bricksdict(bricksdict, key, merged_keys, brick_size, brick_type, short_type, tall_type, set_attempted_merge=False):
    # store the best brick size to origin brick
    brick_d = bricksdict[key]
    brick_d["size"] = brick_size

    # set attributes for merged brick keys
    for k in merged_keys:
        brick_d0 = bricksdict[k]
        if set_attempted_merge:
            brick_d0["attempted_merge"] = True
        if k == key:
            brick_d0["parent"] = "self" if k == key else key
        else:
            brick_d0["parent"] = key
            brick_d0["size"] = None
        # set brick type if necessary
        if flat_brick_type(brick_type):
            brick_d0["type"] = short_type if brick_size[2] == 1 else tall_type
    # set flipped and rotated
    if brick_d["type"] == "SLOPE":
        set_flipped_and_rotated(brick_d, bricksdict, keys_in_brick)
        if brick_type == "SLOPES":
            set_brick_type_for_slope(brick_d, bricksdict, keys_in_brick)


def get_new_parent_key_loc_and_size_flipped(size, loc, zstep):
    # switch to origin brick
    new_loc = loc.copy()
    if size[0] < 0:
        new_loc[0] -= abs(size[0]) - 1
    if size[1] < 0:
        new_loc[1] -= abs(size[1]) - 1
    if size[2] < 0:
        new_loc[2] -= abs(size[2] // zstep) - 1
    new_key = list_to_str(new_loc)

    # store the biggest brick size to origin brick
    new_size = [abs(v) for v in size]

    return new_key, new_loc, new_size


def get_new_parent_key_loc_and_size_added(old_size, size, loc, zstep):
    # switch to origin brick
    new_loc = loc.copy()
    if size[0] < 0:
        new_loc[0] += (old_size[0] - abs(size[0]))
    if size[1] < 0:
        new_loc[1] += (old_size[1] - abs(size[1]))
    if size[2] < 0:
        new_loc[2] += (old_size[2] - abs(size[2]))
    new_key = list_to_str(new_loc)

    # store the biggest brick size to origin brick
    new_size = [abs(v) for v in size]

    return new_key, new_loc, new_size


def should_draw_brick(brick_d, draw_threshold):
    # make sure the bricks are close enough to the shell
    return brick_d["val"] >= draw_threshold and not brick_d["omitted"]


def get_most_common_dir(i_s, i_e, norms):
    return most_common([n[i_s:i_e] for n in norms])


def set_brick_type_for_slope(parent_brick_d, bricksdict, keys_in_brick):
    norms = [bricksdict[k]["near_normal"] for k in keys_in_brick if bricksdict[k]["near_normal"] is not None]
    dir0 = get_most_common_dir(0, 1, norms) if len(norms) != 0 else ""
    if (dir0 == "^" and is_legal_brick_size(size=parent_brick_d["size"], type="SLOPE") and parent_brick_d["top_exposed"]):
        typ = "SLOPE"
    elif (dir0 == "v" and is_legal_brick_size(size=parent_brick_d["size"], type="SLOPE_INVERTED") and parent_brick_d["bot_exposed"]):
        typ = "SLOPE_INVERTED"
    else:
        typ = "STANDARD"
    parent_brick_d["type"] = typ


def set_flipped_and_rotated(parent_brick_d, bricksdict, keys_in_brick):
    norms = [bricksdict[k]["near_normal"] for k in keys_in_brick if bricksdict[k]["near_normal"] is not None]

    dir1 = get_most_common_dir(1, 3, norms) if len(norms) != 0 else ""
    flip, rot = get_flip_rot(dir1)

    # set flipped and rotated
    parent_brick_d["flipped"] = flip
    parent_brick_d["rotated"] = rot
