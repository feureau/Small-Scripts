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
from bpy.types import Operator
from bpy.props import *

# Module imports
from ..delete_model import BRICKER_OT_delete_model
from ...functions import *
from ...lib.undo_stack import *


class OBJECT_OT_delete_override(Operator):
    """OK?"""
    bl_idname = "object.delete"
    bl_label = "Delete"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        # return context.active_object is not None
        return True

    def execute(self, context):
        try:
            self.run_delete(context)
        except:
            bricker_handle_exception()
        return {"FINISHED"}

    def invoke(self, context, event):
        # Run confirmation popup for delete action
        # TODO: support 'self.confirm'
        return context.window_manager.invoke_confirm(self, event)

    ################################################
    # initialization method

    def __init__(self):
        self.undo_stack = UndoStack.get_instance()
        self.iterated_states_at_least_once = False
        self.objs_to_delete = bpy.context.selected_objects
        self.warn_initialize = False
        self.undo_pushed = False

    ###################################################
    # class variables

    use_global = BoolProperty(default=False)
    update_model = BoolProperty(default=True)
    undo = BoolProperty(default=True)
    confirm = BoolProperty(default=True)

    ################################################
    # class methods

    def run_delete(self, context):
        if bpy.props.bricker_initialized:
            for obj in self.objs_to_delete:
                if obj.is_brick:
                    self.undo_stack.undo_push("delete_override")
                    self.undo_pushed = True
                    break
        else:
            # initialize obj_names_dict (key:cm_id, val:list of brick objects)
            obj_names_dict = create_obj_names_dict(self.objs_to_delete)
            # remove brick type objects from selection
            for obj_names_list in obj_names_dict.values():
                if len(obj_names_list) > 0:
                    for obj_name in obj_names_list:
                        self.objs_to_delete.remove(bpy.data.objects.get(obj_name))
                    if not self.warn_initialize:
                        self.report({"WARNING"}, "Please initialize the Bricker [shift+i] before attempting to delete bricks")
                        self.warn_initialize = True
        # run delete_unprotected
        protected = self.delete_unprotected(context, self.use_global, self.update_model)
        # alert user of protected objects
        if len(protected) > 0:
            self.report({"WARNING"}, "Bricker is using the following object(s): " + str(protected)[1:-1])
        # push delete action to undo stack
        if self.undo:
            bpy.ops.ed.undo_push(message="Delete")
        tag_redraw_areas("VIEW_3D")

    def delete_unprotected(self, context, use_global=False, update_model=True):
        scn = context.scene
        protected = []
        obj_names_to_delete = [obj.name for obj in self.objs_to_delete]
        prefs = get_addon_preferences()

        # initialize obj_names_dict (key:cm_id, val:list of brick objects)
        obj_names_dict = create_obj_names_dict(self.objs_to_delete)

        # update matrix
        for i, cm_id in enumerate(obj_names_dict.keys()):
            cm = get_item_by_id(scn.cmlist, cm_id)
            if created_with_unsupported_version(cm):
                continue
            last_blender_state = cm.blender_undo_state
            # get bricksdict from cache
            bricksdict = get_bricksdict(cm)
            if not update_model:
                continue
            if bricksdict is None:
                self.report({"WARNING"}, "Adjacent bricks in model '" + cm.name + "' could not be updated (matrix not cached)")
                continue
            cm.customized = True
            # store cmlist props for quick calling
            last_split_model = cm.last_split_model
            zstep = cm.zstep
            brick_type = cm.brick_type
            merge_internals = "NEITHER" if cm.material_type == "NONE" else cm.merge_internals
            merge_internals_h = merge_internals in ["BOTH", "HORIZONTAL"]
            merge_internals_v = merge_internals in ["BOTH", "VERTICAL"]
            max_width = cm.max_width
            max_depth = cm.max_depth
            draw_threshold = get_threshold(cm)
            keys_to_update = set()

            for obj_name in obj_names_dict[cm_id]:
                # get dict key details of current obj
                dkey = get_dict_key(obj_name)
                dloc = get_dict_loc(bricksdict, dkey)
                # get size of current brick (e.g. [2, 4, 1])
                obj_size = bricksdict[dkey]["size"]

                # for all locations in bricksdict covered by current obj
                keys_in_brick = get_keys_in_brick(bricksdict, obj_size, zstep, key=dkey, loc=dloc)
                # reset bricksdict entries
                reset_bricksdict_entries(bricksdict, keys_in_brick, force_outside=True)
                keys_to_update.discard(dkey)  # don't update adj bricks that are also being removed
                # make adjustments to adjacent bricks
                keys_to_update |= self.update_adj_bricksdicts(bricksdict, zstep, dkey, dloc, draw_threshold, obj_size)[0]
            # dirty_build if it wasn't already
            last_build_is_dirty = cm.build_is_dirty
            if not last_build_is_dirty:
                cm.build_is_dirty = True
            # merge and draw modified bricks
            if len(keys_to_update) > 0:
                # delete those objects
                for k0 in keys_to_update:
                    brick = bpy.data.objects.get(bricksdict[k0]["name"])
                    delete(brick)
                # split up bricks before draw_updated_bricks calls attempt_pre_merge
                for k1 in keys_to_update.copy():
                    keys_to_update |= split_brick(bricksdict, k1, cm.zstep, cm.brick_type)
                # create new bricks at all keys_to_update locations (attempts both pre- and post-merge)
                draw_updated_bricks(cm, bricksdict, keys_to_update, select_created=False)
            if not last_build_is_dirty:
                cm.build_is_dirty = False
            # if undo states not iterated above
            if last_blender_state == cm.blender_undo_state:
                # iterate undo states
                self.undo_stack.iterate_states(cm)
            self.iterated_states_at_least_once = True

        # if nothing was done worth undoing but state was pushed
        if not self.iterated_states_at_least_once and self.undo_pushed:
            # pop pushed value from undo stack
            self.undo_stack.undo_pop_clean()

        # delete bricks
        for obj_name in obj_names_to_delete:
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            if obj.is_brickified_object or obj.is_brick:
                self.delete_brick_object(context, obj, update_model, use_global)
            elif not obj.protected:
                obj_users_scene = len(obj.users_scene)
                if use_global or obj_users_scene == 1:
                    bpy.data.objects.remove(obj, do_unlink=True)
            else:
                print(obj.name + ' is protected')
                protected.append(obj.name)

        tag_redraw_areas("VIEW_3D")

        return protected

    @staticmethod
    def update_adj_bricksdicts(bricksdict, zstep, key, loc, draw_threshold, brick_size=[1, 1, 1]):
        keys_to_update = set()
        new_keys = set()
        brick_d = bricksdict[key]
        # get all adjacent keys not on outside
        neighbor_keys_v = get_keys_neighboring_brick(bricksdict, brick_size, zstep, loc, check_horizontally=False)
        neighbor_keys_h = get_keys_neighboring_brick(bricksdict, brick_size, zstep, loc, check_vertically=False)
        neighbor_keys = set(k for k in neighbor_keys_h.union(neighbor_keys_v) if bricksdict[k]["val"] != 0)
        # update all vals for adj keys onward, recursively
        updated_keys = update_vals_linear(bricksdict, neighbor_keys)
        newly_exposed_keys = set(k for k in updated_keys if bricksdict[k]["val"] == 1)
        # draw new bricks that are now on the shell
        for k0 in updated_keys:
            brick_d0 = bricksdict[k0]
            if not brick_d0["draw"] and brick_d0["val"] >= draw_threshold:
                brick_d0["draw"] = should_draw_brick(brick_d0, draw_threshold)
                brick_d0["size"] = [1, 1, zstep]
                brick_d0["parent"] = "self"
                brick_d0["type"] = get_short_type(brick_d)
                brick_d0["flipped"] = brick_d["flipped"]
                brick_d0["rotated"] = brick_d["rotated"]
                brick_d0["near_face"] = brick_d["near_face"]
                ni = brick_d["near_intersection"]
                brick_d0["near_intersection"] = tuple(ni) if type(ni) in [list, tuple] else ni
                # add key to list for drawing
                keys_to_update.add(k0)
                new_keys.add(k0)
        newly_exposed_keys |= new_keys
        # add neighboring bricks to keys_to_update as their exposure must be re-evaluated
        keys_to_update |= get_neighboring_bricks(bricksdict, brick_size, zstep, loc, check_horizontally=False)
        # return keys updated and new_keys/newly_exposed_keys (for BrickSculpt)
        return keys_to_update, new_keys, newly_exposed_keys

    def delete_brick_object(self, context, obj, update_model=True, use_global=False):
        scn = context.scene
        cm = None
        for cm_cur in scn.cmlist:
            n = get_source_name(cm_cur)
            if not obj.name.startswith("Bricker_%(n)s_brick" % locals()):
                continue
            if obj.is_brickified_object:
                cm = cm_cur
                break
            elif obj.is_brick:
                cur_bricks = cm_cur.collection
                if cur_bricks is not None and len(cur_bricks.objects) < 2:
                    cm = cm_cur
                    break
        if cm and update_model:
            BRICKER_OT_delete_model.run_full_delete(cm=cm)
            deselect(context.active_object)
        else:
            obj_users_scene = len(obj.users_scene)
            if use_global or obj_users_scene == 1:
                bpy.data.objects.remove(obj, do_unlink=True)

    ################################################
