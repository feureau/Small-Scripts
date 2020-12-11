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
from mathutils import Vector, Euler

# Module imports
from .bevel_bricks import *
from .bricksdict import *
from .bricksdict_getter import *
from .brick.bricks import get_brick_dimensions
from .brick.types import mergable_brick_type
from .common import *
from .general import *
from .cmlist_utils import *
from .logo_obj import *
from .make_bricks_point_cloud import *
from .make_bricks import *
from .model_info import set_model_info
from .smoke_cache import *
from .transform_data import *


def get_action(cm):
    """ gets current action type from passed cmlist item """
    if cm.use_animation:
        return "UPDATE_ANIM" if cm.animated else "ANIMATE"
    else:
        return "UPDATE_MODEL" if cm.model_created else "CREATE"


def get_model_resolution(source, cm):
    res = None
    source_details = bounds(source, use_adaptive_domain=False)
    s = Vector((
        round(source_details.dist.x, 6),
        round(source_details.dist.y, 6),
        round(source_details.dist.z, 6),
    ))
    if cm.brick_type != "CUSTOM":
        dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
        full_d = Vector((
            dimensions["width"],
            dimensions["width"],
            dimensions["height"],
        ))
        res = vec_div(s, full_d)
    else:
        custom_obj = cm.custom_object1
        if custom_obj and custom_obj.type == "MESH":
            custom_details = bounds(custom_obj)
            if 0 not in custom_details.dist.to_tuple():
                mult = cm.brick_height / custom_details.dist.z
                full_d = Vector((
                    custom_details.dist.x * mult,
                    custom_details.dist.y * mult,
                    cm.brick_height,
                ))
                full_d_offset = vec_mult(full_d, cm.dist_offset)
                res = vec_div(s, full_d_offset)
    return res


def should_brickify_in_background(cm, r, action):
    # due to mantaflow issue, force local if is_smoke
    if (is_smoke(cm.source_obj) or is_fluid(cm.source_obj)) and bpy.app.version[:2] >= (2, 82):
        return False
    # return pref value if not set to auto
    brickify_in_background = get_addon_preferences().brickify_in_background
    if brickify_in_background != "AUTO" or r is None:
        return brickify_in_background == "ON"
    # initialize vars
    matrix_dirty = matrix_really_is_dirty(cm)
    source = cm.source_obj
    # return False if model is simple enough to run in active session
    return (
                (   # model resolution
                    r.x * r.y * r.z
                    # accounts for shell thickness
                    * math.sqrt(cm.shell_thickness)
                    # accounts for internal supports
                    * (1.35 if cm.internal_supports != "NONE" else 1)
                    # accounts for costly ray casting
                    * (3 if cm.insideness_ray_cast_dir != "HIGH_EFFICIENCY" else 1)
                    # accounts for merging algorithm
                    * (1.5 if mergable_brick_type(cm.brick_type) else 1)
                    # accounts for source object resolution
                    * len(source.data.vertices)**(1/20)
                    # multiplies per frame
                    * (abs(cm.stop_frame - cm.start_frame) if cm.use_animation else 1)
                    # if using cached matrix, divide by 2
                    / (1 if matrix_dirty else 2)
                ) >= 30000 or
                # no logos
                cm.logo_type != "NONE" or
                # accounts for intricacy of custom object
                (cm.brick_type == "CUSTOM" and (not b280() or len(cm.custom_object1.evaluated_get(bpy.context.view_layer.depsgraph).data.vertices) > 50)) or
                # low exposed underside detail
                cm.exposed_underside_detail not in ("FLAT", "LOW") or
                # no hidden underside detail
                cm.hidden_underside_detail != "FLAT" or
                # not using source materials
                (cm.material_type == "SOURCE" and len(source.data.materials) > 0 and cm.use_uv_map and len(source.data.uv_layers) > 0)
    )


def setup_temp_cmlist_scene(cm):
    # create new scene and set as active
    temp_scene = bpy.data.scenes.new("Bricker Model Settings Container")
    # transfer active cmlist props to new scene
    new_cm = temp_scene.cmlist.add()
    match_properties(new_cm, cm, full_match=True)
    # set active cmlist index
    with Suppressor():
        temp_scene.cmlist_index = 0
    # return scene
    return temp_scene


# def get_args_for_background_processor(cm, bricker_addon_path, source_dup=None, skip_bfm_cache=False):
#     script = os.path.join(bricker_addon_path, "lib", "brickify_in_background_template.py")
#
#     skip_keys = list()
#     skip_keys.append("active_key")
#     skip_keys.append("booleans")
#     # if skip_bfm_cache:
#     #     skip_keys.append("bfm_cache")
#     cmlist_props, cmlist_pointer_props = dump_cm_props(cm, skip_keys=skip_keys)
#
#     data_blocks_to_send = set()
#     for item in cmlist_pointer_props:
#         name = cmlist_pointer_props[item]["name"]
#         typ = cmlist_pointer_props[item]["type"]
#         data = getattr(bpy.data, typ.lower() + "s")[name]
#         data_blocks_to_send.add(data)
#     data_blocks_to_send.add(source_dup)
#
#     return script, cmlist_props, cmlist_pointer_props, data_blocks_to_send


def draw_updated_bricks(cm, bricksdict, keys_to_update, action="redrawing", select_created=True, run_pre_merge=True, placeholder_meshes=False):
    if len(keys_to_update) == 0: return []
    assert isinstance(keys_to_update, set)
    if action is not None:
        print("[Bricker] %(action)s..." % locals())
    # get arguments for create_new_bricks
    source = cm.source_obj
    source_dup = get_duplicate_object(cm, source)
    source_details, dimensions = get_details_and_bounds(source_dup, cm)
    parent = cm.parent_obj
    action = "UPDATE_MODEL"
    # actually draw the bricks
    keys = keys_to_update if cm.last_split_model else "ALL"
    _, bricks_created = create_new_bricks(source_dup, parent, source_details, dimensions, action, split=cm.last_split_model, cm=cm, bricksdict=bricksdict, keys=keys, clear_existing_collection=False, select_created=select_created, print_status=False, placeholder_meshes=placeholder_meshes, run_pre_merge=run_pre_merge, redrawing=True)
    # link new bricks to scene
    if not b280():
        for brick in bricks_created:
            safe_link(brick)
    # unlink source_dup if linked
    safe_unlink(source_dup)
    # add bevel if it was previously added
    if cm.bevel_added and not placeholder_meshes:
        bricks = get_bricks(cm)
        create_bevel_mods(cm, bricks)
    # refresh model info
    prefs = get_addon_preferences()
    if prefs.auto_refresh_model_info and not placeholder_meshes:
        set_model_info(bricksdict, cm)
    return bricks_created


def create_new_bricks(source_dup, parent, source_details, dimensions, action, split=True, cm=None, cur_frame=None, bricksdict=None, keys="ALL", clear_existing_collection=True, select_created=False, print_status=True, placeholder_meshes=False, run_pre_merge=True, orig_source=None, redrawing=False):
    """ gets/creates bricksdict, runs make_bricks, and caches the final bricksdict """
    # initialization for getting bricksdict
    scn, cm, n = get_active_context_info(cm=cm)
    brick_scale = get_arguments_for_bricksdict(cm, source=source_dup, dimensions=dimensions)
    update_cursor = action in ("CREATE", "UPDATE_MODEL")
    # get bricksdict
    bricksdict, brick_scale = get_bricksdict_for_model(cm, source_dup, source_details, action, cur_frame, brick_scale, bricksdict, keys, redrawing, update_cursor)
    # reset brick_sizes/types_used
    if keys == "ALL":
        cm.brick_sizes_used = ""
        cm.brick_types_used = ""
    # get bricksdict keys
    if keys == "ALL":
        keys = set(bricksdict.keys())
    if len(keys) == 0:
        return "", None
    # get dictionary of keys based on z value
    keys_dict = get_keys_dict(bricksdict, keys)
    # initialization for making bricks
    cm.zstep = get_zstep(cm)
    ref_logo = None if placeholder_meshes else get_logo(scn, cm, dimensions)  # update ref_logo
    model_name = "Bricker_%(n)s_bricks_f_%(cur_frame)s" % locals() if cur_frame is not None else "Bricker_%(n)s_bricks" % locals()
    bcoll = get_brick_collection(model_name, clear_existing_collection)
    merge_vertical = (redrawing and "PLATES" in cm.brick_type) or cm.brick_type == "BRICKS_AND_PLATES"
    # store some key as active key
    if cm.active_key[0] == -1 and len(keys) > 0:
        loc = get_dict_loc(bricksdict, next(iter(keys)))
        cm.active_key = loc
    # make bricks
    if cm.instance_method == "POINT_CLOUD":
        bricks_created = make_bricks_point_cloud(cm, bricksdict, keys_dict, parent, source_details, dimensions, bcoll, frame_num=cur_frame)
    else:
        bricks_created = make_bricks(cm, bricksdict, keys_dict, keys, parent, ref_logo, dimensions, action, bcoll, num_source_mats=len(source_dup.data.materials), split=split, brick_scale=brick_scale, merge_vertical=merge_vertical, clear_existing_collection=clear_existing_collection, frame_num=cur_frame, cursor_status=update_cursor, print_status=print_status, placeholder_meshes=placeholder_meshes, run_pre_merge=run_pre_merge, redrawing=redrawing)
    # select bricks
    if select_created and len(bricks_created) > 0:
        select(bricks_created)
    # remove duplicated logo
    if ref_logo is not None:
        bpy.data.objects.remove(ref_logo)
    # store current bricksdict to cache
    cache_bricks_dict(action, cm, bricksdict, cur_frame=cur_frame)
    # reset some of the dirty attributes
    cm.build_is_dirty = False
    cm.material_is_dirty = False
    cm.model_is_dirty = False
    cm.bricks_are_dirty = False
    return model_name, bricks_created


def transform_bricks(bcoll, cm, parent, source, source_dup_details, action):
    # if using local orientation and creating model for first time
    if cm.use_local_orient and action == "CREATE":
        obj = parent if cm.split_model else bcoll.objects[0]
        source_details = bounds(source)
        last_mode = source.rotation_mode
        obj.rotation_mode = "XYZ"
        source.rotation_mode = "XYZ"
        obj.rotation_euler = source.rotation_euler
        obj.rotation_mode = last_mode
        source["local_orient_offset"] = source_details.mid - source_dup_details.mid
        obj.location += Vector(source["local_orient_offset"])
    # if model was split but isn't now
    if cm.last_split_model and not cm.split_model:
        # transfer transformation of parent to object
        parent.rotation_mode = "XYZ"
        for obj in bcoll.objects:
            obj.location = parent.location
            obj.rotation_mode = parent.rotation_mode
            obj.rotation_euler.rotate(parent.rotation_euler)
            obj.scale = parent.scale
        # reset parent transformation
        parent.location = (0, 0, 0)
        parent.rotation_euler = Euler((0, 0, 0))
        cm.transform_scale = 1
        parent.scale = (1, 1, 1)
    # if model is not split
    elif not cm.split_model:
        # apply stored transformation to bricks
        apply_transform_data(cm, bcoll.objects)
    # if model wasn't split but is now
    elif not cm.last_split_model:
        # apply stored transformation to parent of bricks
        apply_transform_data(cm, parent)
    obj = bcoll.objects[0] if len(bcoll.objects) > 0 else None
    if obj is None:
        return
    # if model contains armature, lock the location, rotation, and scale of created bricks object
    if not cm.split_model and cm.armature:
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale    = (True, True, True)


def store_parent_collections_to_source(cm, source):
    if not b280():
        return
    # clear outdated stored_parents
    source.stored_parents.clear()
    # store parent collections to source
    if len(source.users_collection) > 0:
        # use parent collections of source
        linked_colls = source.users_collection
    else:
        # use parent collections of brick collection
        brick_coll = cm.collection
        if brick_coll is None:
            return
        all_collections = list(bpy_collections()) + [bpy.context.scene.collection]
        linked_colls = [cn for cn in all_collections if brick_coll.name in cn.children]
    for cn in linked_colls:
        source.stored_parents.add().collection = cn


def get_new_parent(name, loc):
    parent = bpy.data.objects.new(name, None)
    parent.location = loc
    return parent


def link_brick_collection(cm, coll):
    cm.collection = coll
    source = cm.source_obj
    if cm.parent_obj.name not in coll.objects:
        coll.objects.link(cm.parent_obj)
    if b280():
        for item in source.stored_parents:
            if coll.name not in item.collection.children:
                item.collection.children.link(coll)
    else:
        [safe_link(obj) for obj in coll.objects]


def get_anim_coll(n):
    anim_coll_name = "Bricker_%(n)s_bricks" % locals()
    anim_coll = bpy_collections().get(anim_coll_name)
    if anim_coll is None:
        anim_coll = bpy_collections().new(anim_coll_name)
    return anim_coll


def finish_animation(cm):
    scn, cm, n = get_active_context_info(cm=cm)
    wm = bpy.context.window_manager
    wm.progress_end()

    # link animation frames to animation collection
    anim_coll = get_anim_coll(n)
    for cn in get_collections(cm, typ="ANIM"):
        if b280():
            if cn.name not in anim_coll.children:
                anim_coll.children.link(cn)
        else:
            for obj in cn.objects:
                safe_link(obj)
                if obj.name not in anim_coll.objects.keys():
                    anim_coll.objects.link(obj)
    return anim_coll


def add_completed_frame(cm, frame):
    if cm.completed_frames != "":
        cm.completed_frames += ", "
    cm.completed_frames += str(frame)
