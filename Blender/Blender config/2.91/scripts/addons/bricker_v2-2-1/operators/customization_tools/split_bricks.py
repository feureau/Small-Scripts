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
import marshal

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_split_bricks(Operator):
    """Split selected bricks into 1x1 bricks"""
    bl_idname = "bricker.split_bricks"
    bl_label = "Split Brick(s)"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        scn = context.scene
        objs = context.selected_objects
        # check that at least 1 selected object is a brick
        for obj in objs:
            if not obj.is_brick:
                continue
            # get cmlist item referred to by object
            cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
            if cm.last_brick_type != "CUSTOM":
                return True
        return False

    def execute(self, context):
        self.split_bricks(context, deep_copy_matrix=True)
        return{"FINISHED"}

    def invoke(self, context, event):
        """invoke props popup if conditions met"""
        scn = context.scene
        # iterate through cm_ids of selected objects
        for cm_id in self.obj_names_dict.keys():
            cm = get_item_by_id(scn.cmlist, cm_id)
            if not flat_brick_type(cm.brick_type):
                continue
            bricksdict = self.bricksdicts[cm_id]
            # iterate through names of selected objects
            for obj_name in self.obj_names_dict[cm_id]:
                dkey = get_dict_key(obj_name)
                size = bricksdict[dkey]["size"]
                if size[2] <= 1:
                    continue
                if size[0] + size[1] > 2:
                    return context.window_manager.invoke_props_dialog(self)
                else:
                    self.vertical = True
                    self.split_bricks(context)
                    return {"FINISHED"}
        self.horizontal = True
        self.split_bricks(context)
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        self.undo_stack = UndoStack.get_instance()
        self.orig_undo_stack_length = self.undo_stack.get_length()
        self.vertical = False
        self.horizontal = False
        self.cached_bfm = {}
        # get copy of obj_names_dict and bricksdicts
        selected_objects = bpy.context.selected_objects
        self.obj_names_dict = create_obj_names_dict(selected_objects)
        self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())

    ###################################################
    # class variables

    # variables
    obj_names_dict = {}
    bricksdicts = {}

    # properties
    vertical = bpy.props.BoolProperty(
        name="Vertical (plates)",
        description="Split bricks into plates",
        default=False)
    horizontal = bpy.props.BoolProperty(
        name="Horizontal (1x1s)",
        description="Split bricks into smaller bricks with minimum width and depth",
        default=False)

    #############################################
    # class methods

    def split_bricks(self, context, deep_copy_matrix=False):
        try:
            # revert to last bricksdict
            self.undo_stack.match_python_to_blender_state()
            # push to undo stack
            if self.orig_undo_stack_length == self.undo_stack.get_length():
                self.cached_bfm = self.undo_stack.undo_push("split", affected_ids=list(self.obj_names_dict.keys()))
            # initialize vars
            scn = context.scene
            objs_to_select = []
            # iterate through cm_ids of selected objects
            for cm_id in self.obj_names_dict.keys():
                cm = get_item_by_id(scn.cmlist, cm_id)
                self.undo_stack.iterate_states(cm)
                bricksdict = marshal.loads(self.cached_bfm[cm_id]) if deep_copy_matrix else self.bricksdicts[cm_id]
                keys_to_update = set()
                cm.customized = True

                # iterate through names of selected objects
                for obj_name in self.obj_names_dict[cm_id]:
                    # get dict key details of current obj
                    dkey = get_dict_key(obj_name)
                    dloc = get_dict_loc(bricksdict, dkey)
                    x0, y0, z0 = dloc
                    # get size of current brick (e.g. [2, 4, 1])
                    brick_size = bricksdict[dkey]["size"]
                    # bricksdict[dkey]["type"] = "STANDARD"

                    # skip 1x1 bricks
                    if brick_size[0] + brick_size[1] + brick_size[2] / cm.zstep == 3:
                        continue

                    if self.vertical or self.horizontal:
                        # split the bricks in the matrix and set size of active brick's bricksdict entries to 1x1x[lastZSize]
                        split_keys = split_brick(bricksdict, dkey, cm.zstep, cm.brick_type, loc=dloc, v=self.vertical, h=self.horizontal)
                        # append new split_keys to keys_to_update
                        keys_to_update |= split_keys
                    else:
                        keys_to_update.add(dkey)

                # draw modified bricks
                draw_updated_bricks(cm, bricksdict, keys_to_update)

                # add selected objects to objects to select at the end
                objs_to_select += context.selected_objects
            # select the new objects created
            select(objs_to_select)
        except:
            bricker_handle_exception()

    #############################################
