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
import time

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from .brick import *
from .bricksdict import *
from .common import *
from .general import *
from .logo_obj import get_logo
from ..operators.bevel import BRICKER_OT_bevel


def get_available_types(by="SELECTION", include_sizes=None):
    # initialize empty parameters
    if include_sizes is None:
        include_sizes = []
    # initialize vars
    items = []
    legal_bs = bpy.props.bricker_legal_brick_sizes
    scn = bpy.context.scene
    objs = bpy.context.selected_objects if by == "SELECTION" else [bpy.context.active_object]
    obj_names_dict = create_obj_names_dict(objs)
    bricksdicts = get_bricksdicts_from_objs(obj_names_dict.keys())
    invalid_items = []
    for cm_id in obj_names_dict.keys():
        cm = get_item_by_id(scn.cmlist, cm_id)
        brick_type = cm.brick_type
        bricksdict = bricksdicts[cm_id]
        obj_sizes = []
        # check that custom_objects are valid
        for idx in range(3):
            target_type = "CUSTOM " + str(idx + 1)
            warning_msg = custom_valid_object(cm, target_type=target_type, idx=idx)
            if warning_msg is not None and iter_from_type(target_type) not in invalid_items:
                invalid_items.append(iter_from_type(target_type))
        # build items list
        for obj_name in obj_names_dict[cm_id]:
            dkey = get_dict_key(obj_name)
            obj_size = bricksdict[dkey]["size"]
            if obj_size in obj_sizes:
                continue
            obj_sizes.append(obj_size)
            if obj_size[2] not in (1, 3): raise Exception("Custom Error Message: obj_size not in (1, 3)")
            # build items
            items += [iter_from_type(typ) for typ in legal_bs[3] if include_sizes == "ALL" or obj_size[:2] in legal_bs[3][typ] + include_sizes]
            if flat_brick_type(brick_type):
                items += [iter_from_type(typ) for typ in legal_bs[1] if include_sizes == "ALL" or obj_size[:2] in legal_bs[1][typ] + include_sizes]
    # uniquify items
    items = uniquify2(items, inner_type=tuple)
    # remove invalid items
    for item in invalid_items:
        remove_item(items, item)
    # sort items
    items.sort(key=lambda k: k[0])
    # return items, or null if items was empty
    return items if len(items) > 0 else [("NULL", "Null", "")]


def update_brick_size_and_dict(dimensions, source_name, bricksdict, brick_size, key, loc, draw_threshold, dec=0, cur_height=None, cur_type=None, target_height=None, target_type=None, created_from=None):
    brick_d = bricksdict[key]
    assert target_height is not None or target_type is not None
    target_height = target_height or (1 if target_type in get_brick_types(height=1) else 3)
    assert cur_height is not None or cur_type is not None
    cur_height = cur_height or (1 if cur_type in get_brick_types(height=1) else 3)
    # adjust brick size if changing type from 3 tall to 1 tall
    if cur_height == 3 and target_height == 1:
        brick_size[2] = 1
        for x in range(brick_size[0]):
            for y in range(brick_size[1]):
                for z in range(1, cur_height):
                    new_loc = [loc[0] + x, loc[1] + y, loc[2] + z - dec]
                    new_key = list_to_str(new_loc)
                    new_brick_d = bricksdict[new_key]
                    new_brick_d["parent"] = None
                    new_brick_d["draw"] = False
                    set_brick_val(bricksdict, new_loc, new_key, action="REMOVE")
    # adjust brick size if changing type from 1 tall to 3 tall
    elif cur_height == 1 and target_height == 3:
        brick_size[2] = 3
        full_d = Vector((dimensions["width"], dimensions["width"], dimensions["height"]))
        # update bricks dict entries above current brick
        for x in range(brick_size[0]):
            for y in range(brick_size[1]):
                for z in range(1, target_height):
                    new_loc = [loc[0] + x, loc[1] + y, loc[2] + z]
                    new_key = list_to_str(new_loc)
                    # create new bricksdict entry if it doesn't exist
                    if new_key not in bricksdict:
                        bricksdict = create_addl_bricksdict_entry(source_name, bricksdict, key, new_key, full_d, x, y, z)
                    # update bricksdict entry to point to new brick
                    new_brick_d = bricksdict[new_key]
                    new_brick_d["draw"] = should_draw_brick(new_brick_d, draw_threshold)
                    new_brick_d["parent"] = key
                    new_brick_d["created_from"] = created_from
                    new_brick_d["type"] = brick_d["type"]
                    new_brick_d["mat_name"] = brick_d["mat_name"] if new_brick_d["mat_name"] == "" else new_brick_d["mat_name"]
                    new_brick_d["near_face"] = new_brick_d["near_face"] or brick_d["near_face"]
                    new_brick_d["near_intersection"] = new_brick_d["near_intersection"] or tuple(brick_d["near_intersection"])
                    if new_brick_d["val"] == 0:
                        set_brick_val(bricksdict, new_loc, new_key)
    return brick_size


def create_addl_bricksdict_entry(source_name, bricksdict, source_key, key, full_d, x, y, z):
    brick_d = bricksdict[source_key]
    new_name = "Bricker_%(source_name)s__%(key)s" % locals()
    new_co = (Vector(brick_d["co"]) + vec_mult(Vector((x, y, z)), full_d)).to_tuple()
    bricksdict[key] = create_bricksdict_entry(
        name=              new_name,
        loc=               str_to_list(key),
        co=                new_co,
        near_face=         brick_d["near_face"],
        near_intersection= tuple(brick_d["near_intersection"]),
        mat_name=          brick_d["mat_name"],
    )
    return bricksdict


def get_bricksdicts_from_objs(obj_names):
    scn = bpy.context.scene
    # initialize bricksdicts
    bricksdicts = {}
    for cm_id in obj_names:
        cm = get_item_by_id(scn.cmlist, cm_id)
        if cm is None: continue
        # get bricksdict from cache
        bricksdict = get_bricksdict(cm)
        # add to bricksdicts
        bricksdicts[cm_id] = bricksdict
    return bricksdicts


def update_vals_linear(bricksdict, keys):
    checked_keys = set()
    updated_keys = set()
    next_keys = keys
    while len(next_keys) > 0:
        # initialize structs for this iteration
        cur_keys = next_keys.difference(checked_keys)
        next_keys = set()
        # update vals for all cur_keys and get next_keys
        for k in cur_keys:
            old_val = bricksdict[k]["val"]
            new_val = set_brick_val(bricksdict, key=k)
            if old_val != new_val:
                updated_keys.add(k)
                next_keys |= set(k for k in get_adj_keys(bricksdict, key=k) if bricksdict[k]["val"] != 0)
        # update checked keys
        checked_keys |= cur_keys
    return updated_keys


def get_used_sizes():
    scn = bpy.context.scene
    items = [("NONE", "None", "")]
    for cm in scn.cmlist:
        if not cm.brick_sizes_used:
            continue
        sort_by = lambda k: (str_to_list(k)[2], str_to_list(k)[0], str_to_list(k)[1])
        items += [(s, s, "") for s in sorted(cm.brick_sizes_used.split("|"), reverse=True, key=sort_by) if (s, s, "") not in items]
    return items


def get_used_types():
    scn = bpy.context.scene
    items = [("NONE", "None", "")]
    for cm in scn.cmlist:
        items += [(t.upper(), t.title(), "") for t in sorted(cm.brick_types_used.split("|")) if (t.upper(), t.title(), "") not in items]
    return items


def iter_from_type(typ):
    return (typ.upper(), typ.title().replace("_", " "), "")


def create_obj_names_dict(objs):
    scn = bpy.context.scene
    # initialize obj_names_dict
    obj_names_dict = {}
    # fill obj_names_dict with selected_objects
    for obj in objs:
        if obj is None or not obj.is_brick:
            continue
        # get cmlist item referred to by object
        cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
        if cm is None: continue
        # add object to obj_names_dict
        if cm.id not in obj_names_dict:
            obj_names_dict[cm.id] = [obj.name]
        else:
            obj_names_dict[cm.id].append(obj.name)
    return obj_names_dict


def select_bricks(obj_names_dict, bricksdicts, brick_size="NULL", brick_type="NULL", all_models=False, only=False, include="EXT"):
    scn = bpy.context.scene
    if only:
        deselect_all()
    # split all bricks in obj_names_dict[cm_id]
    for cm_id in obj_names_dict.keys():
        cm = get_item_by_id(scn.cmlist, cm_id)
        if not (cm.idx == scn.cmlist_index or all_models):
            continue
        bricksdict = bricksdicts[cm_id]
        selected_something = False

        for obj_name in obj_names_dict[cm_id]:
            # get dict key details of current obj
            dkey = get_dict_key(obj_name)
            dloc = get_dict_loc(bricksdict, dkey)
            cur_brick_d = bricksdict[dkey]
            siz = cur_brick_d["size"]
            typ = cur_brick_d["type"]
            on_shell = is_on_shell(bricksdict, dkey, loc=dloc, zstep=cm.zstep)

            # get current brick object
            cur_obj = bpy.data.objects.get(obj_name)
            # if cur_obj is None:
            #     continue
            # select brick
            size_str = list_to_str(sorted(siz[:2]) + [siz[2]])
            if (size_str == brick_size or typ == brick_type) and (include == "BOTH" or (include == "INT" and not on_shell) or (include == "EXT" and on_shell)):
                selected_something = True
                select(cur_obj)
            # elif only:
            #     deselect(cur_obj)

        # if no brick_size bricks exist, remove from cm.brick_sizes_used or cm.brick_types_used
        remove_unused_from_list(cm, brick_type=brick_type, brick_size=brick_size, selected_something=selected_something)


default_sort_fn = lambda k: (str_to_list(k)[0] * str_to_list(k)[1] * str_to_list(k)[2])
def merge_bricks(bricksdict, keys, cm, target_type="STANDARD", any_height=False, merge_seed=None, merge_inconsistent_mats=False, direction_mult=(1, 1, 1), sort_fn=default_sort_fn):
    """ attempts to merge bricks in 'keys' parameter with all bricks in bricksdict not marked with 'attempted_merge' """
    # don't to anything if custom brick type
    brick_type = cm.brick_type
    if brick_type == "CUSTOM":
        return set()
    # initialize vars
    updated_keys = set()
    max_width = cm.max_width
    max_depth = cm.max_depth
    legal_bricks_only = cm.legal_bricks_only
    internal_mat_name = cm.internal_mat.name if cm.internal_mat else ""
    mat_shell_depth = cm.mat_shell_depth
    material_type = cm.material_type
    merge_seed = merge_seed or cm.merge_seed
    merge_internals = "NEITHER" if material_type == "NONE" else cm.merge_internals
    merge_internals_h = merge_internals in ["BOTH", "HORIZONTAL"]
    merge_internals_v = merge_internals in ["BOTH", "VERTICAL"]
    rand_state = np.random.RandomState(merge_seed)
    merge_vertical = target_type in get_brick_types(height=3) and "PLATES" in brick_type
    height_3_only = merge_vertical and not any_height

    # sort keys
    if sort_fn is not None:
        if isinstance(keys, set):
            keys = list(keys)
        keys.sort(key=sort_fn)

    # set bricksdict info for all keys passed
    for key in keys:
        brick_d = bricksdict[key]
        # set all keys as to be merged
        brick_d["available_for_merge"] = True
        # reset mat_name for internal keys
        if brick_d["val"] < 1:
            brick_d["mat_name"] == ""

    # attempt to merge all keys together
    for key in keys:
        # skip keys already merged to another brick
        if bricksdict[key]["attempted_merge"]:
            continue
        # attempt to merge current brick with other bricks in keys, according to available brick types
        _, new_key, _ = attempt_pre_merge(bricksdict, key, bricksdict[key]["size"], cm.zstep, brick_type, max_width, max_depth, mat_shell_depth, legal_bricks_only, internal_mat_name, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats=merge_inconsistent_mats, prefer_largest=True, direction_mult=direction_mult, merge_vertical=merge_vertical, target_type=target_type, height_3_only=height_3_only)
        updated_keys.add(new_key)

    # unset all keys as to be merged
    for key in keys:
        bricksdict[key]["available_for_merge"] = False

    return updated_keys


def remove_unused_from_list(cm, brick_type="NULL", brick_size="NULL", selected_something=True):
    item = brick_type if brick_type != "NULL" else brick_size
    # if brick_type/brick_size bricks exist, return None
    if selected_something or item == "NULL":
        return None
    # turn brick_types_used into list of sizes
    lst = (cm.brick_types_used if brick_type != "NULL" else cm.brick_sizes_used).split("|")
    # remove unused item
    if item in lst:
        remove_item(lst, item)
    # convert bTU back to string of sizes split by '|'
    new_list = list_to_str(lst, separate_by="|")
    # store new list to current cmlist item
    if brick_size != "NULL":
        cm.brick_sizes_used = new_list
    else:
        cm.brick_types_used = new_list


def get_adj_locs(cm, bricksdict, dkey):
    # initialize vars for self.adj_locs setup
    x,y,z = get_dict_loc(bricksdict, dkey)
    obj_size = bricksdict[dkey]["size"]
    sX, sY, sZ = obj_size[0], obj_size[1], obj_size[2] // cm.zstep
    adj_locs = [[],[],[],[],[],[]]
    # initialize ranges
    rgs = [range(x, x + sX),
           range(y, y + sY),
           range(z, z + sZ)]
    # set up self.adj_locs
    adj_locs[0] += [[x + sX, y0, z0] for z0 in rgs[2] for y0 in rgs[1]]
    adj_locs[1] += [[x - 1, y0, z0]  for z0 in rgs[2] for y0 in rgs[1]]
    adj_locs[2] += [[x0, y + sY, z0] for z0 in rgs[2] for x0 in rgs[0]]
    adj_locs[3] += [[x0, y - 1, z0]  for z0 in rgs[2] for x0 in rgs[0]]
    adj_locs[4] += [[x0, y0, z + sZ] for y0 in rgs[1] for x0 in rgs[0]]
    adj_locs[5] += [[x0, y0, z - 1]  for y0 in rgs[1] for x0 in rgs[0]]
    return adj_locs


# def install_bricksculpt():
#     if not hasattr(bpy.props, "bricksculpt_module_name"):
#         return False
#     addons_path = bpy.utils.user_resource("SCRIPTS", "addons")
#     bricksculpt_mod_name = bpy.props.bricksculpt_module_name
#     bricker_mod_name = bpy.props.bricker_module_name
#     bricksculpt_path_old = "%(addons_path)s/%(bricksculpt_mod_name)s/bricksculpt_framework.py" % locals()
#     bricksculpt_path_new = "%(addons_path)s/%(bricker_mod_name)s/operators/customization_tools/bricksculpt_framework.py" % locals()
#     f_old = open(bricksculpt_path_old, "r")
#     f_new = open(bricksculpt_path_new, "w")
#     # write META commands
#     lines = f_old.readlines()
#     f_new.truncate(0)
#     f_new.writelines(lines)
#     f_old.close()
#     f_new.close()
#     return True
