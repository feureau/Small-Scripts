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
import bmesh
import os
import math

# Blender imports
import bpy
from bpy.types import Object
from mathutils import Matrix, Vector
props = bpy.props

# Module imports
from ..functions.common import *
from ..functions.general import *
from ..functions.make_bricks import *
from ..functions.bevel_bricks import *


class BRICKER_OT_bevel(bpy.types.Operator):
    """Bevel brick edges and corners for added realism"""
    bl_idname = "bricker.bevel"
    bl_label = "Bevel Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
        except IndexError:
            return False
        if cm.model_created or cm.animated:
            return True
        return False

    def execute(self, context):
        try:
            cm = get_active_context_info(context)[1]
            # set bevel action to add or remove
            try:
                test_brick = get_bricks()[0]
                test_brick.modifiers[test_brick.name + "_bvl"]
                action = "REMOVE" if cm.bevel_added else "ADD"
            except:
                action = "ADD"
            # get bricks to bevel
            bricks = get_bricks()
            # create or remove bevel
            self.run_bevel_action(bricks, cm, action, set_bevel=True)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    #############################################
    # class methods

    def run_bevel_action(self, bricks, cm, action="ADD", set_bevel=False):
        """ chooses whether to add or remove bevel """
        if action == "REMOVE":
            remove_bevel_mods(bricks)
            cm.bevel_added = False
        elif action == "ADD":
            create_bevel_mods(cm, bricks)
            cm.bevel_added = True

    #############################################
