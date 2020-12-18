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

# Module imports
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_redraw_bricks(Operator):
    """redraw selected bricks from bricksdict"""
    bl_idname = "bricker.redraw_bricks"
    bl_label = "Redraw Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        objs = context.selected_objects
        # check that at least 1 selected object is a brick
        for obj in objs:
            if obj.is_brick:
                return True
        return False

    def execute(self, context):
        try:
            scn = context.scene
            selected_objects = context.selected_objects
            active_obj = context.active_object
            initial_active_obj_name = active_obj.name if active_obj else ""
            objs_to_select = []

            # iterate through cm_ids of selected objects
            for cm_id in self.obj_names_dict.keys():
                cm = get_item_by_id(scn.cmlist, cm_id)
                # get bricksdict from cache
                bricksdict, _ = self.bricksdicts[cm_id]
                keys_to_update = []

                # add keys for updated objects to simple bricksdict for drawing
                keys_to_update = set(get_dict_key(obj.name) for obj in self.obj_names_dict[cm_id])

                # draw modified bricks
                draw_updated_bricks(cm, bricksdict, keys_to_update)

                # add selected objects to objects to select at the end
                objs_to_select += context.selected_objects
            # select the new objects created
            select(objs_to_select)
            orig_obj = bpy.data.objects.get(initial_active_obj_name)
            set_active_obj(orig_obj)
        except:
            bricker_handle_exception()
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        try:
            selected_objects = bpy.context.selected_objects
            self.obj_names_dict = create_obj_names_dict(selected_objects)
            self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        except:
            bricker_handle_exception()

    ###################################################
    # class variables

    # vars
    bricksdicts = {}
    obj_names_dict = {}

    #############################################
