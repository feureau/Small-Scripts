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
from os.path import join, exists, split
import codecs

# Blender imports
import bpy
from bpy.app.handlers import persistent
import addon_utils
from mathutils import Vector, Euler

# Module imports
from .common import *
from .general import *
from .bricksdict import *
from .clear_cache import *
from .brickify_utils import finish_animation
from .matlist_utils import create_mat_objs
from ..lib.caches import bricker_bfm_cache
from ..lib.undo_stack import UndoStack, python_undo_state

# updater import, import safely
# Prevents popups for users with invalid python installs e.g. missing libraries
try:
    from ..addon_updater import Updater as updater
except Exception as e:
    print("ERROR INITIALIZING UPDATER")
    print(str(e))
    class Singleton_updater_none(object):
        def __init__(self):
            self.addon = None
            self.verbose = False
            self.invalidupdater = True # used to distinguish bad install
            self.error = None
            self.error_msg = None
            self.async_checking = None
        def clear_state(self):
            self.addon = None
            self.verbose = False
            self.invalidupdater = True
            self.error = None
            self.error_msg = None
            self.async_checking = None
        def run_update(self): pass
        def check_for_update(self): pass
    updater = Singleton_updater_none()
    updater.error = "Error initializing updater module"
    updater.error_msg = str(e)


def bricker_running_blocking_op():
    wm = bpy.context.window_manager
    return hasattr(wm, "bricker_running_blocking_operation") and wm.bricker_running_blocking_operation


@persistent
def handle_animation(scn, depsgraph=None):
    # THINK TWICE before editing this app handler... may break support for ConciergeRender
    if bricker_running_blocking_op():
        return
    for i, cm in enumerate(scn.cmlist):
        if not cm.animated:
            continue
        n = get_source_name(cm)
        for cur_bricks_coll in cm.collection.children:
            try:
                cf = int(cur_bricks_coll.name[cur_bricks_coll.name.rfind("_") + 1:])
            except ValueError:
                continue
            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
            on_cur_f = adjusted_frame_current == cf
            # set active obj
            active_obj = bpy.context.active_object if hasattr(bpy.context, "active_object") else None
            if b280():
                # hide bricks from view and render unless on current frame
                if cur_bricks_coll.hide_render == on_cur_f:
                    cur_bricks_coll.hide_render = not on_cur_f
                if cur_bricks_coll.hide_viewport == on_cur_f:
                    cur_bricks_coll.hide_viewport = not on_cur_f
                # select bricks if last frame was selected/active
                if active_obj and active_obj.name.startswith("Bricker_%(n)s_bricks" % locals()) and on_cur_f:
                    select(cur_bricks_coll.objects, active=True)
            else:
                for brick in cur_bricks_coll.objects:
                    # hide bricks from view and render unless on current frame
                    if on_cur_f:
                        unhide(brick)
                    else:
                        hide(brick)
                    # select bricks if last frame was selected/active
                    if active_obj and active_obj.name.startswith("Bricker_%(n)s_bricks" % locals()) and on_cur_f:
                        select(brick, active=True)
                    # prevent bricks from being selected on frame change
                    else:
                        deselect(brick)


@blender_version_wrapper("<=","2.79")
def is_obj_visible(scn, cm, n):
    obj_visible = False
    if cm.model_created or cm.animated:
        g = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
        if g is not None and len(g.objects) > 0:
            obj = g.objects[0]
        else:
            obj = None
    else:
        obj = cm.source_obj
    if obj:
        obj_visible = False
        for i in range(20):
            if obj.layers[i] and scn.layers[i]:
                obj_visible = True
    return obj_visible, obj


def find_3dview_space():
    # Find 3D_View window and its scren space
    area = next((a for a in bpy.data.window_managers[0].windows[0].screen.areas if a.type == "VIEW_3D"), None)

    if area:
        space = area.spaces[0]
    else:
        space = bpy.context.space_data

    return space


# clear light cache before file load
@persistent
def clear_bfm_cache(dummy):
    clear_caches(deep_matrix=False, dupes=False)


@persistent
def reset_properties(dummy):
    scn = bpy.context.scene
    # reset undo stack on load
    undo_stack = UndoStack.get_instance(reset=True)
    # if file was saved in the middle of a brickify process, reset necessary props
    for cm in scn.cmlist:
        if cm.brickifying_in_background and cm.source_obj is not None:
            cm.brickifying_in_background = False
            n = cm.source_obj.name
            for cf in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                cur_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
                if cur_bricks_coll is None:
                    cm.last_stop_frame = max(cm.last_start_frame, cf - 1)
                    # cm.stop_frame = max(cm.last_start_frame, cf - 1)
                    cm.stop_frame = cm.stop_frame  # run updater to allow 'update_model'
                    # hide obj unless on scene current frame
                    if scn.frame_current > cm.last_stop_frame and cf > cm.last_start_frame:
                        set_frame_visibility(cm, cm.last_stop_frame)
                    break


@persistent
def handle_loading_to_light_cache(dummy):
    scn = bpy.context.scene
    for cm in scn.cmlist:
        deep_to_light_cache(bricker_bfm_cache, cm)
    if len(bricker_bfm_cache) > 0:
        print("[Bricker] pulled {num_pulled_ids} {pluralized_dicts} from deep cache to light cache".format(num_pulled_ids=len(bricker_bfm_cache), pluralized_dicts="dict" if len(bricker_bfm_cache) == 1 else "dicts"))
    # verify caches loaded properly
    for scn in bpy.data.scenes:
        for cm in scn.cmlist:
            if not (cm.model_created or cm.animated):
                continue
            # reset undo states
            cm.blender_undo_state = 0
            python_undo_state[cm.id] = 0
            # load bricksdict
            bricksdict = get_bricksdict(cm)
            if bricksdict is None:
                cm.matrix_lost = True
                cm.matrix_is_dirty = True


# push dicts from light cache to deep cache on save
@persistent
def handle_storing_to_deep_cache(dummy):
    light_to_deep_cache(bricker_bfm_cache)


@persistent
def show_all_anim_frames(dummy):
    scn = bpy.context.scene
    for cm in scn.cmlist:
        if not cm.animated:
            continue
        for coll in cm.collection.children:
            unhide(coll)


def set_anim_frames_visibility(scn):
    scn = bpy.context.scene
    for cm in scn.cmlist:
        if not cm.animated:
            continue
        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
            set_frame_visibility(cm, frame)

@persistent
def validate_bricker(dummy):
    validated = False
    validation_file = join(get_addon_directory(), "lib", codecs.encode("oevpxre_chepunfr_irevsvpngvba.gkg", "rot13"))
    if exists(validation_file):
        verification_str = "Thank you for supporting my work and ongoing development by purchasing Bricker!\n"
        with open(validation_file) as f:
            validated = verification_str == codecs.encode(f.readline(), "rot13")
    if not validated:
        res = updater.run_update(
            force=False,
            revert_tag="demo",
            # callback=post_update_callback,
            clean=False,
        )
        folderpath, foldername = split(get_addon_directory())
        bpy.props.bricker_validated = False


# @persistent
# def undo_bricksdict_changes(dummy):
#     scn = bpy.context.scene
#     if scn.cmlist_index == -1:
#         return
#     undo_stack = UndoStack.get_instance()
#     global python_undo_state
#     cm = scn.cmlist[scn.cmlist_index]
#     if cm.id not in python_undo_state:
#         python_undo_state[cm.id] = 0
#     # handle undo
#     if python_undo_state[cm.id] > cm.blender_undo_state:
#         self.undo_stack.undo_pop()
#
#
# bpy.app.handlers.undo_pre.append(undo_bricksdict_changes)
#
#
# @persistent
# def redo_bricksdict_changes(dummy):
#     scn = bpy.context.scene
#     if scn.cmlist_index == -1:
#         return
#     undo_stack = UndoStack.get_instance()
#     global python_undo_state
#     cm = scn.cmlist[scn.cmlist_index]
#     if cm.id not in python_undo_state:
#         python_undo_state[cm.id] = 0
#     # handle redo
#     elif python_undo_state[cm.id] < cm.blender_undo_state:
#         self.undo_stack.redo_pop()
#
#
# bpy.app.handlers.redo_pre.append(redo_bricksdict_changes)


@persistent
def handle_upconversion(dummy):
    # remove storage scene
    sto_scn = bpy.data.scenes.get("Bricker_storage (DO NOT MODIFY)")
    if sto_scn is not None:
        for obj in sto_scn.objects:
            obj.use_fake_user = True
        bpy.data.scenes.remove(sto_scn)
    for scn in bpy.data.scenes:
        # update cmlist indices to reflect updates to Bricker
        for cm in scn.cmlist:
            if created_with_unsupported_version(cm):
                # normalize cm.version
                cm.version = cm.version.replace(", ", ".")
                version_tup = tuple(int(v) for v in cm.version.split("."))
                # convert from v1_0 to v1_1
                if version_tup[:2] < (1, 1):
                    cm.brickWidth = 2 if cm.maxBrickScale2 > 1 else 1
                    cm.brick_depth = cm.maxBrickScale2
                # convert from v1_2 to v1_3
                if version_tup[:2] < (1, 3):
                    if cm.color_snap_amount == 0:
                        cm.color_snap_amount = 0.001
                    for obj in bpy.data.objects:
                        if obj.name.startswith("Rebrickr"):
                            obj.name = obj.name.replace("Rebrickr", "Bricker")
                    for scn in bpy.data.scenes:
                        if scn.name.startswith("Rebrickr"):
                            scn.name = scn.name.replace("Rebrickr", "Bricker")
                    for coll in bpy_collections():
                        if coll.name.startswith("Rebrickr"):
                            coll.name = coll.name.replace("Rebrickr", "Bricker")
                # convert from v1_3 to v1_4
                if version_tup[:2] < (1, 4):
                    # update "_frame_" to "_f_" in brick and group names
                    n = cm.source_name
                    bricker_bricks_cn = "Bricker_%(n)s_bricks" % locals()
                    if cm.animated:
                        for i in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                            bricker_bricks_curf_cn = bricker_bricks_cn + "_frame_" + str(i)
                            bcoll = bpy_collections().get(bricker_bricks_curf_cn)
                            if bcoll is not None:
                                bcoll.name = rreplace(bcoll.name, "frame", "f")
                                for obj in bcoll.objects:
                                    obj.name = rreplace(obj.name, "combined_frame" if "combined_frame" in obj.name else "frame", "f")
                    elif cm.model_created:
                        bcoll = bpy_collections().get(bricker_bricks_cn)
                        if bcoll is not None:
                            for obj in bcoll.objects:
                                if obj.name.endswith("_combined"):
                                    obj.name = obj.name[:-9]
                    # remove old storage scene
                    sto_scn_old = bpy.data.scenes.get("Bricker_storage (DO NOT RENAME)")
                    if sto_scn_old is not None:
                        for obj in sto_scn_old.objects:
                            if obj.name.startswith("Bricker_refLogo"):
                                bpy.data.objects.remove(obj, do_unlink=True)
                            else:
                                obj.use_fake_user = True
                        bpy.data.scenes.remove(sto_scn_old)
                    # create "Bricker_cm.id_mats" object for each cmlist idx
                    create_mat_objs(cm)
                    # update names of Bricker source objects
                    old_source = bpy.data.objects.get(cm.source_name + " (DO NOT RENAME)")
                    if old_source is not None:
                        old_source.name = cm.source_name
                    # transfer dist offset values to new prop locations
                    if cm.distOffsetX != -1:
                        cm.dist_offset = (cm.distOffsetX, cm.distOffsetY, cm.distOffsetZ)
                # convert from v1_4 to v1_5
                if version_tup[:2] < (1, 5):
                    if cm.logoDetail != "":
                        cm.logo_type = cm.logoDetail
                    cm.matrix_is_dirty = True
                    cm.matrix_lost = True
                    remove_colls = list()
                    for coll in bpy_collections():
                        if coll.name.startswith("Bricker_") and (coll.name.endswith("_parent") or coll.name.endswith("_dupes")):
                            remove_colls.append(coll)
                    for coll in remove_colls:
                        bpy_collections().remove(coll)
                # convert from v1_5 to v1_6
                if version_tup[:2] < (1, 6):
                    for cm in scn.cmlist:
                        cm.zstep = get_zstep(cm)
                    if cm.source_obj is None: cm.source_obj = bpy.data.objects.get(cm.source_name)
                    if cm.parent_obj is None: cm.parent_obj = bpy.data.objects.get(cm.parent_name)
                    n = get_source_name(cm)
                    if cm.animated:
                        coll = finish_animation(cm)
                    else:
                        coll = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
                    if cm.collection is None: cm.collection = coll
                    dup = bpy.data.objects.get(n + "_duplicate")
                    if dup is not None: dup.name = n + "__dup__"
                # convert from v1_6 to v1_7
                if version_tup[:2] < (1, 7):
                    cm.mat_obj_abs = bpy.data.objects.get("Bricker_{}_RANDOM_mats".format(cm.id))
                    cm.mat_obj_random = bpy.data.objects.get("Bricker_{}_ABS_mats".format(cm.id))
                    # transfer props from 1_6 to 1_7 (camel to snake case)
                    for prop in get_annotations(cm):
                        if prop.islower():
                            continue
                        snake_prop = camel_to_snake_case(prop)
                        if hasattr(cm, snake_prop) and hasattr(cm, prop):
                            setattr(cm, snake_prop, getattr(cm, prop))
                # convert from v2_0 to v2_1
                if version_tup[:2] < (2, 1):
                    bricksdict = get_bricksdict(cm)
                    if bricksdict is not None:
                        cm.build_is_dirty = True
                        for k in bricksdict.keys():
                            bricksdict[k]["attempted_merge"] = False
                            bricksdict[k]["available_for_merge"] = False
                            # FOR DEVELOPER USE: C.scene.cmlist[C.scene.cmlist_index].version = "2.0.0"
                            mat_name_changes = {
                                "ABS Plastic Light Grey": "ABS Plastic Light Bluish Gray",
                                "ABS Plastic Dark Grey": "ABS Plastic Dark Bluish Gray",
                                "ABS Plastic Dark Azur": "ABS Plastic Dark Azure",
                                "ABS Plastic Trans-Blue": "ABS Plastic Trans-Dark Blue",
                                "ABS Plastic Trans-Bright Orange": "ABS Plastic Trans-Orange",
                                "ABS Plastic Trans-Brown": "ABS Plastic Trans-Black",
                                "ABS Plastic Bright Pink": "ABS Plastic Dark Pink",
                                "ABS Plastic Light Pink": "ABS Plastic Bright Pink",
                                "ABS Plastic Gold": "ABS Plastic Metallic Gold",
                                "ABS Plastic Silver": "ABS Plastic Metallic Silver",
                                "ABS Plastic Cool Yellow": "ABS Plastic Bright Light Yellow",
                                "ABS Plastic Light Flesh": "ABS Plastic Light Nougat",
                                "ABS Plastic Teal": "ABS Plastic Dark Turquoise",
                            }
                            mat_obj = get_mat_obj(cm)
                            # update outdated abs mat names
                            for mat_name in mat_name_changes.keys():
                                if bricksdict[k]["mat_name"] == mat_name:
                                    bricksdict[k]["mat_name"] = mat_name_changes[mat_name]
                                    mat_idx = mat_obj.data.materials.find(mat_name)
                                if mat_idx != -1:
                                    mat_obj.data.materials.pop(index=mat_idx)
                                    mat_obj.data.materials.append(bpy.data.materials.get(mat_name_changes[mat_name]))
                # convert from v2_1 to v2_2
                if version_tup[:2] < (2, 2):
                    bricksdict = get_bricksdict(cm)
                    if bricksdict is not None:
                        for k in bricksdict.keys():
                            if bricksdict[k]["type"] in ("PLATE", "BRICK"):
                                bricksdict[k]["type"] = "STANDARD"
                            if "omitted" not in bricksdict[k]:
                                bricksdict[k]["omitted"] = False



            # ensure parent object has no users
            if cm.parent_obj is not None:
                # TODO: replace with this line when the function is fixed in 2.8
                cm.parent_obj.user_clear()
                cm.parent_obj.use_fake_user = True
                # for coll in cm.parent_obj.users_collection:
                #     coll.objects.unlink(cm.parent_obj)
            # ensure cmlist items have material objects
            mat_obj = get_mat_obj(cm)
            if mat_obj is None:
                create_mat_objs(cm)
