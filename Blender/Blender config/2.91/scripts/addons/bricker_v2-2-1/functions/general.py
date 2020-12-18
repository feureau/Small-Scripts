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
import collections
import json
import math
import numpy as np

# Blender imports
import bpy
import addon_utils
from mathutils import Vector, Euler, Matrix
from bpy.types import Object

# Module imports
from .common import *


def get_active_context_info(context=None, cm=None, cm_id=None):
    context = context or bpy.context
    scn = context.scene
    cm = cm or scn.cmlist[scn.cmlist_index]
    return scn, cm, get_source_name(cm)


def bricker_handle_exception():
    handle_exception(log_name="Bricker log", report_button_loc="Bricker > Brick Models > Report Error")


def get_source_name(cm):
    return cm.source_obj.name if cm.source_obj is not None else ""


def is_bricksculpt_installed():
    return hasattr(bpy.props, "bricksculpt_module_name")


def center_mesh_origin(m, dimensions, size):
    # get half width
    d0 = Vector((dimensions["width"] / 2, dimensions["width"] / 2, 0))
    # get scalar for d0 in positive xy directions
    scalar = Vector((
        size[0] * 2 - 1,
        size[1] * 2 - 1,
        0,
    ))
    # calculate center
    center = (vec_mult(d0, scalar) - d0) / 2
    # apply translation matrix to center mesh
    m.transform(Matrix.Translation(-Vector(center)))


def get_anim_adjusted_frame(frame, start_frame, stop_frame, step_frame=1):
    clamped_frame = min(stop_frame, max(start_frame, frame))
    adjusted_frame = clamped_frame - ((clamped_frame - start_frame) % step_frame)
    return adjusted_frame


def get_bricks(cm=None, typ=None):
    """ get bricks in 'cm' model """
    scn, cm, n = get_active_context_info(cm=cm)
    typ = typ or ("MODEL" if cm.model_created else "ANIM")
    bricks = list()
    if typ == "MODEL":
        bcoll = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
        if bcoll:
            bricks = [obj for obj in bcoll.objects if obj.name.startswith("Bricker_") and not (obj.name.endswith("_parent") or "_parent_f_" in obj.name)]
    elif typ == "ANIM":
        for cf in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
            bcoll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
            if bcoll:
                bricks += [obj for obj in bcoll.objects if not (obj.name.endswith("_parent") or "_parent_f_" in obj.name)]
    return bricks


def get_collections(cm=None, typ=None):
    """ get bricks collections in 'cm' model """
    scn, cm, n = get_active_context_info(cm=cm)
    typ = typ or ("MODEL" if cm.model_created else "ANIM")
    if typ == "MODEL":
        cn = "Bricker_%(n)s_bricks" % locals()
        bcolls = [bpy_collections()[cn]]
    if typ == "ANIM":
        bcolls = list()
        for cf in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
            cn = "Bricker_%(n)s_bricks_f_%(cf)s" % locals()
            bcoll = bpy_collections().get(cn)
            if bcoll:
                bcolls.append(bcoll)
    return bcolls


def get_matrix_settings_str(cm=None):
    cm = cm or get_active_context_info()[1]
    # TODO: Maybe remove custom objects from this?
    matrix_settings = {
        "brick_height": round(cm.brick_height, 6),
        "gap": round(cm.gap, 4),
        "brick_type": cm.brick_type,
        "dist_offset": list(cm.dist_offset),
        "include_transparency": cm.include_transparency,
        "custom_object1_name": cm.custom_object1.name if cm.custom_object1 is not None else "",
        "custom_object2_name": cm.custom_object2.name if cm.custom_object2 is not None else "",
        "custom_object3_name": cm.custom_object3.name if cm.custom_object3 is not None else "",
        "use_normals": cm.use_normals,
        "grid_offset": list(cm.grid_offset),
        "insideness_ray_cast_dir": cm.insideness_ray_cast_dir,
        "brick_shell": cm.brick_shell,
        "mat_shell_depth": cm.mat_shell_depth,
        "calc_internals": cm.calc_internals,
        "calculation_axes": cm.calculation_axes,
        "smoke_density": round(cm.smoke_density, 6),
        "smoke_quality": round(cm.smoke_quality, 6),
        "smoke_brightness": round(cm.smoke_brightness, 6),
        "smoke_saturation": round(cm.smoke_saturation, 6),
        "flame_color": vec_round(cm.flame_color, 6, outer_type=list),
        "flame_intensity": round(cm.flame_intensity, 6),
    }
    return json.dumps(matrix_settings)


def matrix_really_is_dirty(cm, include_lost_matrix=True):
    return (cm.matrix_is_dirty and cm.last_matrix_settings != get_matrix_settings_str()) or (cm.matrix_lost and include_lost_matrix)


def vec_to_str(vec, separate_by=","):
    return str(list_to_str(list(vec), separate_by=separate_by))


def compress_rgba_vals(lst):
    # return compress_str(list_to_str([item for sublist in lst for item in sublist]))
    return compress_str(json.dumps(lst))


def decompress_rgba_vals(string, channels=4):
    # lst = str_to_list(decompress_str(string), item_type=float)
    # lst_2d = [lst[i:i + channels] for i in range(0, len(lst), channels)]
    # return lst_2d
    return json.loads(decompress_str(string))


def list_to_str(lst, separate_by=","):
    # assert type(lst) in (list, tuple)
    return separate_by.join(map(str, lst))


def str_to_list(string, item_type=int, split_on=","):
    lst = string.split(split_on)
    assert type(string) is str and type(split_on) is str
    lst = list(map(item_type, lst))
    return lst


def str_to_tuple(string, item_type=int, split_on=","):
    return tuple(str_to_list(string, item_type, split_on))


def created_with_unsupported_version(cm):
    return cm.version[:3] != bpy.props.bricker_version[:3]


def created_with_newer_version(cm):
    model_version = cm.version.split(".")
    bricker_version = bpy.props.bricker_version.split(".")
    return (int(model_version[0]) > int(bricker_version[0])) or (int(model_version[0]) == int(bricker_version[0]) and int(model_version[1]) > int(bricker_version[1]))


def get_normal_direction(normal, max_dist=0.77, slopes=False):
    # initialize vars
    min_dist = max_dist
    min_dir = None
    # skip normals that aren't within 0.3 of the z values
    if normal is None or ((-0.2 < normal.z < 0.2) or normal.z > 0.8 or normal.z < -0.8):
        return min_dir
    # set Vectors for perfect normal directions
    if slopes:
        norm_dirs = {
            "^X+":Vector((1, 0, 0.5)),
            "^Y+":Vector((0, 1, 0.5)),
            "^X-":Vector((-1, 0, 0.5)),
            "^Y-":Vector((0, -1, 0.5)),
            "vX+":Vector((1, 0, -0.5)),
            "vY+":Vector((0, 1, -0.5)),
            "vX-":Vector((-1, 0, -0.5)),
            "vY-":Vector((0, -1, -0.5)),
        }
    else:
        norm_dirs = {
            "X+":Vector((1, 0, 0)),
            "Y+":Vector((0, 1, 0)),
            "Z+":Vector((0, 0, 1)),
            "X-":Vector((-1, 0, 0)),
            "Y-":Vector((0, -1, 0)),
            "Z-":Vector((0, 0, -1)),
        }
    # calculate nearest
    for dir,v in norm_dirs.items():
        dist = (v - normal).length
        if dist < min_dist:
            min_dist = dist
            min_dir = dir
    return min_dir


def get_flip_rot(dir):
    flip = dir in ("X-", "Y-")
    rot = dir in ("Y+", "Y-")
    return flip, rot


def custom_valid_object(cm, target_type="Custom 0", idx=None):
    for i, custom_info in enumerate([[cm.has_custom_obj1, cm.custom_object1], [cm.has_custom_obj2, cm.custom_object2], [cm.has_custom_obj3, cm.custom_object3]]):
        has_custom_obj, custom_obj = custom_info
        if idx is not None and idx != i:
            continue
        elif not has_custom_obj and not (i == 0 and cm.brick_type == "CUSTOM") and int(target_type.split(" ")[-1]) != i + 1:
            continue
        if custom_obj is None:
            warning_msg = "Custom brick type object {} could not be found".format(i + 1)
            return warning_msg
        elif custom_obj.name == get_source_name(cm) and (not (cm.animated or cm.model_created) or custom_obj.protected):
            warning_msg = "Source object cannot be its own custom brick."
            return warning_msg
        elif custom_obj.type != "MESH":
            warning_msg = "Custom object {} is not of type 'MESH'. Please select another object (or press 'ALT-C to convert object to mesh).".format(i + 1)
            return warning_msg
        custom_details = bounds(custom_obj)
        zero_dist_axis = ""
        if custom_details.dist.x < 0.00001:
            zero_dist_axis += "X"
        if custom_details.dist.y < 0.00001:
            zero_dist_axis += "Y"
        if custom_details.dist.z < 0.00001:
            zero_dist_axis += "Z"
        if zero_dist_axis != "":
            axis_str = "axis" if len(zero_dist_axis) == 1 else "axes"
            warning_msg = "Custom brick type object is to small along the '%(zero_dist_axis)s' %(axis_str)s (<0.00001). Please select another object or extrude it along the '%(zero_dist_axis)s' %(axis_str)s." % locals()
            return warning_msg
    return None


def update_has_custom_objs(cm, typ):
    # update has_custom_obj
    if typ == "CUSTOM 1":
        cm.has_custom_obj1 = True
    if typ == "CUSTOM 2":
        cm.has_custom_obj2 = True
    if typ == "CUSTOM 3":
        cm.has_custom_obj3 = True


def brickify_should_run(cm):
    if ((cm.animated and (not update_can_run("ANIMATION") and not cm.anim_is_dirty))
       or (cm.model_created and not update_can_run("MODEL"))):
        return False
    return True


def update_can_run(typ):
    scn, cm, n = get_active_context_info()
    if created_with_unsupported_version(cm):
        return True
    elif scn.cmlist_index == -1:
        return False
    else:
        common_needs_update = (cm.logo_type != "NONE" and cm.logo_type != "LEGO") or cm.brick_type == "CUSTOM" or cm.model_is_dirty or cm.matrix_is_dirty or cm.internal_is_dirty or cm.build_is_dirty or cm.bricks_are_dirty
        if typ == "ANIMATION":
            return common_needs_update or (cm.material_type != "CUSTOM" and cm.material_is_dirty)
        elif typ == "MODEL":
            return common_needs_update or (cm.collection is not None and len(cm.collection.objects) == 0) or (cm.material_type != "CUSTOM" and (cm.material_type != "RANDOM" or cm.split_model or cm.last_material_type != cm.material_type or cm.material_is_dirty) and cm.material_is_dirty) or cm.has_custom_obj1 or cm.has_custom_obj2 or cm.has_custom_obj3


def get_locs_in_brick(size, zstep, loc):
    x0, y0, z0 = loc
    return [[x0 + x, y0 + y, z0 + z] for z in range(0, size[2], zstep) for y in range(size[1]) for x in range(size[0])]


def get_lowest_locs_in_brick(size, loc):
    x0, y0, z0 = loc
    return [[x0 + x, y0 + y, z0] for y in range(size[1]) for x in range(size[0])]


def get_highest_locs_in_brick(size, zstep, loc):
    x0, y0, z0 = loc
    # add last item in iterator to z0
    for i in range(0, size[2], zstep):
        pass
    z0 += i
    return [[x0 + x, y0 + y, z0] for y in range(size[1]) for x in range(size[0])]
#
#
# def get_locs_neighboring_brick(size, zstep, loc):
#     x0, y0, z0 = loc
#     all_neighbor_locs = [[x0 + x, y0 + y, z0 + z] for z in range(0, size[2], zstep) for y in set((-1, size[1])) for x in set((-1, size[0]))]
#     existing_neighbor_locs = [l for l in all_neighbor_locs if
#     return existing_neighbor_locs


def get_outer_locs(size, zstep, loc):
    x0, y0, z0 = loc
    outer_locs = [[x0 + x, y0 + y, z0 + z] for z in range(0, size[2], zstep) for y in set((0, size[1] - 1)) for x in set((0, size[0] - 1))]
    return outer_locs


def get_keys_neighboring_brick(bricksdict, size, zstep, loc, check_horizontally=True, check_vertically=True):
    """ get keys where locs neighbor another for a given brick """
    x0, y0, z0 = loc
    neighbored_keys = set()

    # if we're checking for horizontal neighbors
    if check_horizontally:
        # +x check
        neighbored_keys |= set(list_to_str([x0 + size[0], y0 + y, z0 + z]) for z in range(0, size[2], zstep) for y in range(size[1]))
        # -x check
        neighbored_keys |= set(list_to_str([x0 - 1, y0 + y, z0 + z]) for z in range(0, size[2], zstep) for y in range(size[1]))
        # +y check
        neighbored_keys |= set(list_to_str([x0 + x, y0 + size[1], z0 + z]) for z in range(0, size[2], zstep) for x in range(size[0]))
        # -y check
        neighbored_keys |= set(list_to_str([x0 + x, y0 - 1, z0 + z]) for z in range(0, size[2], zstep) for x in range(size[0]))

    # if we're checking for vertical neighbors
    if check_vertically:
        # +z check
        neighbored_keys |= set(list_to_str([x0 + x, y0 + y, z0 + size[1]]) for y in range(0, size[1], zstep) for x in range(size[0]))
        # -z check
        neighbored_keys |= set(list_to_str([x0 + x, y0 + y, z0 - 1]) for y in range(0, size[1], zstep) for x in range(size[0]))

    # only return keys in bricksdict
    neighbored_keys = set(k for k in neighbored_keys if k in bricksdict)

    return neighbored_keys


# def get_neighbored_key_pairs(bricksdict, size, zstep, loc, check_vertically=False):
#     """ get keys where locs neighbor another for a given brick """
#     x0, y0, z0 = loc
#     neighbored_keys = list()
#     # +x check
#     locs = [[x0 + size[0], y0 + y, z0 + z] for z in range(0, size[2], zstep) for y in range(size[1])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0] - 1, loc0[1], loc0[2]]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#     # -x check
#     locs = [[x0 - 1, y0 + y, z0 + z] for z in range(0, size[2], zstep) for y in range(size[1])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0] + 1, loc0[1], loc0[2]]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#     # +y check
#     locs = [[x0 + x, y0 + size[1], z0 + z] for z in range(0, size[2], zstep) for x in range(size[0])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0], loc0[1] - 1, loc0[2]]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#     # -y check
#     locs = [[x0 + x, y0 - 1, z0 + z] for z in range(0, size[2], zstep) for x in range(size[0])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0], loc0[1] + 1, loc0[2]]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#
#     # if we're not checking for vertical neighbors, return early
#     if not check_vertically:
#         return neighbored_keys
#
#     # +z check
#     locs = [[x0 + x, y0 + y, z0 + size[1]] for y in range(0, size[1], zstep) for x in range(size[0])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0], loc0[1], loc0[2] - 1]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#     # -z check
#     locs = [[x0 + x, y0 + y, z0 - 1] for y in range(0, size[1], zstep) for x in range(size[0])]
#     for loc0 in locs:
#         key0 = list_to_str(loc0)
#         if key0 in bricksdict:
#             loc1 = [loc0[0], loc0[1], loc0[2] + 1]
#             key1 = list_to_str(loc1)
#             neighbored_keys.append(key0, key1)
#
#     return neighbored_keys


def get_neighboring_bricks(bricksdict, size, zstep, loc, check_horizontally=True, check_vertically=True):
    neighboring_keys = get_keys_neighboring_brick(bricksdict, size, zstep, loc, check_horizontally, check_vertically)
    neighboring_bricks = set()
    for key in neighboring_keys:
        parent_key = bricksdict[key]["parent"]
        if parent_key == "self":
            neighboring_bricks.add(key)
        elif parent_key is not None:
            neighboring_bricks.add(parent_key)
    return neighboring_bricks


# loc param is more efficient than key, but one or the other must be passed
def get_keys_in_brick(bricksdict, size, zstep:int, loc:list=None, key:str=None):
    x0, y0, z0 = loc or get_dict_loc(bricksdict, key)
    return set(list_to_str((x0 + x, y0 + y, z0 + z)) for z in range(0, size[2], zstep) for y in range(size[1]) for x in range(size[0]))


def get_keys_dict(bricksdict, keys=None, parents_only=False):
    """ get dictionary of bricksdict keys based on z value """
    keys = keys or set(bricksdict.keys())
    # if len(keys) > 1:
    #     keys.sort(key=lambda x: (get_dict_loc(bricksdict, x)[0], get_dict_loc(bricksdict, x)[1]))
    keys_dict = {}
    for k0 in keys:
        if not bricksdict[k0]["draw"] or (parents_only and bricksdict[k0]["parent"] != "self"):
            continue
        z = get_dict_loc(bricksdict, k0)[2]
        if z in keys_dict:
            keys_dict[z].add(k0)
        else:
            keys_dict[z] = {k0}  # initialize set
    return keys_dict


def get_parent_key(bricksdict, key):
    try:
        brick_d = bricksdict[key]
    except KeyError:
        return None
    parent_key = key if brick_d["parent"] in ("self", None) else brick_d["parent"]
    return parent_key


def get_dict_key(name):
    """ get dict key from end of obj name """
    dkey = name.split("__")[-1]
    return dkey


def get_dict_loc(bricksdict, key):
    """ get dict loc from bricksdict key """
    try:
        loc = bricksdict[key]["loc"]
    except KeyError:
        loc = str_to_list(key)
    return loc


def get_rgba_vals(cm):
    if cm.id not in bricker_rgba_vals_cache or bricker_rgba_vals_cache[cm.id] is None:
        bricker_rgba_vals_cache[cm.id] = cm.rgba_vals
    return bricker_rgba_vals_cache[cm.id]


def settings_can_be_drawn():
    scn = bpy.context.scene
    if scn.cmlist_index == -1:
        return False
    if bversion() < "002.079":
        return False
    if not bpy.props.bricker_initialized:
        return False
    if scn.cmlist[scn.cmlist_index].linked_from_external:
        return False
    if not bpy.props.bricker_validated:
        return False
    return True


def set_frame_visibility(cm, frame):
    scn, cm, n = get_active_context_info(cm=cm)
    cur_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
    if cur_bricks_coll is None:
        return
    adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
    if b280():
        cur_bricks_coll.hide_viewport = frame != adjusted_frame_current
        cur_bricks_coll.hide_render   = frame != adjusted_frame_current
    elif frame != adjusted_frame_current:
        [hide(obj) for obj in cur_bricks_coll.objects]
    else:
        [unhide(obj) for obj in cur_bricks_coll.objects]


def get_brick_collection(model_name, clear_existing_collection=True):
    """get existing or create new brick collection"""
    bcoll = bpy_collections().get(model_name)
    # create new collection if no existing collection found
    if bcoll is None:
        bcoll = bpy_collections().new(model_name)
    # else, replace existing collection
    elif clear_existing_collection:
        for obj0 in bcoll.objects:
            bcoll.objects.unlink(obj0)
    cm = get_active_context_info()[1]
    return bcoll


def check_if_internals_exist(cm):
    return cm.calc_internals and (cm.shell_thickness > 1 or cm.internal_supports != "NONE")
