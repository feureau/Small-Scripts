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
import copy

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Module imports
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_merge_bricks(Operator):
    """Merge selected bricks (auto-converts brick type to 'BRICK' or 'PLATE')"""
    bl_idname = "bricker.merge_bricks"
    bl_label = "Merge Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        objs = context.selected_objects
        i = 0
        # check that at least 2 objects are selected and are bricks
        for obj in objs:
            if not obj.is_brick:
                continue
            # get cmlist item referred to by object
            cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
            if cm.last_brick_type == "CUSTOM" or cm.build_is_dirty:
                continue
            i += 1
            if i == 2:
                return True
        return False

    def execute(self, context):
        try:
            scn = context.scene
            objs_to_select = []
            # iterate through cm_ids of selected objects
            for cm_id in self.obj_names_dict.keys():
                cm = get_item_by_id(scn.cmlist, cm_id)
                self.undo_stack.iterate_states(cm)
                # initialize vars
                bricksdict = self.bricksdicts[cm_id]
                all_split_keys = set()
                cm.customized = True
                brick_type = cm.brick_type

                # iterate through cm_ids of selected objects
                for obj_name in self.obj_names_dict[cm_id]:
                    # initialize vars
                    dkey = get_dict_key(obj_name)

                    # split brick in matrix
                    split_keys = split_brick(bricksdict, dkey, cm.zstep, brick_type)
                    all_split_keys |= split_keys
                    # delete the object that was split
                    delete(bpy.data.objects.get(obj_name))

                # run self.merge_bricks
                keys_to_update = merge_bricks(bricksdict, all_split_keys, cm, any_height=True, merge_inconsistent_mats=self.merge_inconsistent_mats)

                # draw modified bricks
                draw_updated_bricks(cm, bricksdict, keys_to_update)

                # add selected objects to objects to select at the end
                objs_to_select += context.selected_objects
            # select the new objects created
            select(objs_to_select)
            bpy.props.bricker_last_selected = [obj.name for obj in context.selected_objects]
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        # initialize vars
        selected_objects = bpy.context.selected_objects
        self.obj_names_dict = create_obj_names_dict(selected_objects)
        self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push("merge", list(self.obj_names_dict.keys()))
        # set merge_inconsistent_mats
        self.merge_inconsistent_mats = bpy.props.bricker_last_selected == [obj.name for obj in selected_objects]

    ###################################################
    # class variables

    # variables
    bricksdicts = {}
    obj_names_dict = {}

    #############################################
    # class methods

    # NONE!

    #############################################
