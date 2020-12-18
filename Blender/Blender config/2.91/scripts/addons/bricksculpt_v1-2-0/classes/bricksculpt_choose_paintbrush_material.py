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


class BRICKSCULPT_OT_choose_paintbrush_material(Operator):
    """Choose the material of the active BrickSculpt paintbrush tool"""
    bl_idname = "bricksculpt.choose_paintbrush_material"
    bl_label = "Choose Paintbrush Material"
    bl_options = {"REGISTER", "INTERNAL"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = bpy.context.scene
        return scn.bricksculpt.running_active_session

    def execute(self, context):
        scn = context.scene
        scn.bricksculpt.choosing_material = False
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)#, event)

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        layout.prop(scn.bricksculpt, "paintbrush_mat")

    ###################################################
    # initialization method

    def __init__(self):
        bpy.context.window.cursor_set("DEFAULT")

    ###################################################
    # class variables

    # NONE!

    ###################################################
