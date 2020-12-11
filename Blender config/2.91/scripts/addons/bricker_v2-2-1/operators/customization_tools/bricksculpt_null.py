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
import bmesh
import math

# Blender imports
import bpy
import bgl
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.types import Operator, SpaceView3D, bpy_struct
from bpy.props import *

# Module imports
# NONE!


class BRICKER_OT_bricksculpt_null(Operator):
    """Run the BrickSculpt editing tool suite"""
    bl_idname = "bricker.bricksculpt_null"
    bl_label = "Run BrickSculpt Tool"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return False

    def execute(self, context):
        self.report({"WARNING"}, "BrickSculpt not installed!")
        return {"CANCELLED"}

    # define props for popup
    mode = EnumProperty(
        items=[
            ("DRAW", "DRAW", ""),
            ("PAINT", "PAINT", ""),
            ("MERGE_SPLIT", "MERGE/SPLIT", ""),
        ],
    )
