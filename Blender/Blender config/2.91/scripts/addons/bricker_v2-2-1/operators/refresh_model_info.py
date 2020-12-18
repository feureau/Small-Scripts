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
import os

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..functions import *


class BRICKER_OT_refresh_model_info(Operator):
    """Refresh all model statistics"""
    bl_idname = "bricker.refresh_model_info"
    bl_label = "Refresh Model Info"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return True

    def execute(self, context):
        try:
            if self.bricksdict is None:
                self.report({"WARNING"}, "Could not refresh model info - model is not cached")
                return {"CANCELLED"}
            scn, cm, _ = get_active_context_info(context)
            bricksdict = get_bricksdict(cm, d_type="MODEL" if cm.model_created else "ANIM", cur_frame=scn.frame_current)
            set_model_info(bricksdict, cm)
            return{"FINISHED"}
        except:
            bricker_handle_exception()
            return {"CANCELLED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    ###################################################
    # class variables

    # NONE!

    ################################################
    # class methods

    # NONE!

    ################################################
