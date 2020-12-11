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


class BRICKER_OT_update_booleans(bpy.types.Operator):
    """Update booleans"""
    bl_idname = "bricker.update_booleans"
    bl_label = "Update Booleans"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if cm.source_obj is None:
            return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def execute(self, context):
        try:
            # initialize vars
            scn, cm, _ = get_active_context_info(context)
            self.undo_stack.iterate_states(cm)

            # reset omitted bricks based on booleans
            bricksdict = get_bricksdict(cm)
            draw_threshold = get_threshold(cm)
            bool_list = cm.booleans
            bool_dupes = update_bool_dupes(cm)
            offset_loc = cm.parent_obj.location
            for k in bricksdict:
                bricksdict[k]["omitted"] = should_omit_brick(Vector(bricksdict[k]["co"]) + offset_loc, bool_list)
                bricksdict[k]["draw"] = should_draw_brick(bricksdict[k], draw_threshold)
            cm.build_is_dirty = True
            delete(bool_dupes)
            self.report({"INFO"}, "Boolean data updated")
        except:
            bricker_handle_exception()

        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('clear_cache')

    #############################################
