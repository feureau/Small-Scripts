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
from bpy.props import StringProperty

# Module imports
from ..functions import *


class BRICKER_OT_redraw_custom_bricks(bpy.types.Operator):
    """Redraw custom bricks with current custom object"""
    bl_idname = "bricker.redraw_custom_bricks"
    bl_label = "Redraw Custom Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
        except IndexError:
            return False
        if cm.matrix_is_dirty:
            return False
        return cm.model_created or cm.animated

    def execute(self, context):
        try:
            self.redraw_custom_bricks(context)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    target_prop = StringProperty(default="")

    #############################################
    # class methods

    def redraw_custom_bricks(self, context):
        cm = get_active_context_info(context)[1]
        bricksdict = get_bricksdict(cm)
        if bricksdict is None:
            return
        keys_to_update = set(k for k in bricksdict if bricksdict[k]["type"] == "CUSTOM " + self.target_prop[-1])
        if len(keys_to_update) != 0:
            draw_updated_bricks(cm, bricksdict, keys_to_update)

    #############################################
