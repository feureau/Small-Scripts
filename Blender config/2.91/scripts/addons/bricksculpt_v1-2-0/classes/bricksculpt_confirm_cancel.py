# Copyright (C) 2019 Christopher Gearhart
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
import bmesh
import math
import importlib

# Blender imports
import bpy
import bgl
from bpy.types import Operator
from bpy.props import *

# Module imports
from .bricksculpt_framework import *
from .bricksculpt_tools import *
from .bricksculpt_drawing import *
from ..functions import *


class BRICKSCULPT_OT_confirm_cancel(Operator):
    """Are you sure?"""
    bl_idname = "bricksculpt.confirm_cancel"
    bl_label = "Cancel BrickSculpt Session? (changes will be permanently lost)"
    bl_options = {"REGISTER", "INTERNAL"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return context.scene.bricksculpt.running_active_session

    def execute(self, context):
        context.scene.bricksculpt.cancel_session_changes = True
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    ###################################################
