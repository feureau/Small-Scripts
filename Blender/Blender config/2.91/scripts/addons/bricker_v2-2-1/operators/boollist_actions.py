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
import os
import json
from zipfile import ZipFile

# Blender imports
import bpy
from bpy.props import *
from bpy.types import Operator

# Module imports
from ..functions import *


# ui list item actions
class BRICKER_OT_bool_list_action(Operator):
    bl_idname = "bricker.bool_list_action"
    bl_label = "Boolean List Action"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    # @classmethod
    # def poll(self, context):
    #     scn = context.scene
    #     for cm in scn.cmlist:
    #         if cm.animated:
    #             return False
    #     return True

    def execute(self, context):
        try:
            scn, cm, _ = get_active_context_info(context)
            idx = cm.boolean_index

            try:
                item = cm.booleans[idx]
            except IndexError:
                pass

            if self.action == "REMOVE" and len(cm.booleans) > 0 and idx >= 0:
                self.remove_item(context, idx)

            elif self.action == "ADD":
                self.add_item(context)

            elif self.action == "DOWN" and idx < len(cm.booleans) - 1:
                self.move_down(context, item)

            elif self.action == "UP" and idx >= 1:
                self.move_up(context, item)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ###################################################
    # class variables

    action = EnumProperty(
        name="Action",
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("REMOVE", "Remove", ""),
            ("ADD", "Add", ""),
        ),
        default="ADD",
    )

    #############################################
    # class methods

    @staticmethod
    def add_item(context):
        # scn = context.scene
        # active_object = context.active_object
        # if active_object:
        #     # if active object isn't on visible layer, don't set it as default source for new model
        #     if not is_obj_visible_in_viewport(active_object):
        #         active_object = None
        #     # if active object is already the source for another model, don't set it as default source for new model
        #     elif any([cm.source_obj is active_object for cm in scn.cmlist]):
        #         active_object = None
        scn, cm, _ = get_active_context_info(context)
        item = cm.booleans.add()
        # switch to new cmlist item
        cm.boolean_index = len(cm.booleans) - 1
        # set item properties
        item.idx = cm.boolean_index
        item.name = f"Boolean {item.idx}"
        item.id = max([bool.id for bool in cm.booleans]) + 1

    def remove_item(self, context, idx):
        scn, cm, _ = get_active_context_info(context)
        if len(cm.booleans) - 1 == scn.cmlist_index:
            cm.boolean_index -= 1
        cm.booleans.remove(idx)
        if cm.boolean_index == -1 and len(cm.booleans) > 0:
            cm.boolean_index = 0
        # else:
        #     # run update function of the property
        #     cm.boolean_index = cm.boolean_index
        self.update_idxs(cm.booleans)

    def move_down(self, context, item):
        scn, cm = get_active_context_info(context)
        cm.booleans.move(cm.boolean_index, cm.boolean_index + 1)
        cm.boolean_index += 1
        self.update_idxs(cm.booleans)

    def move_up(self, context, item):
        scn, cm = get_active_context_info(context)
        cm.booleans.move(cm.boolean_index, cm.boolean_index - 1)
        cm.boolean_index -= 1
        self.update_idxs(cm.booleans)

    @staticmethod
    def update_idxs(list):
        for i, item in enumerate(list):
            item.idx = i

    #############################################
