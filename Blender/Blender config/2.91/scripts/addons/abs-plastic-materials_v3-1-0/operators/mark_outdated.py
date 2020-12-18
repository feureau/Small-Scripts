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
import os
import time

# Blender imports
import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector

# Module imports
from ..functions import *


class ABS_OT_mark_outdated(Operator):
    """Mark ABS Plastic Materials as outdated"""
    bl_idname = "abs.mark_outdated"
    bl_label = "Mark ABS Plastic Materials Outdated"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    # @classmethod
    # def poll(self, context):
    #     # TODO: Speed this up
    #     mat_names = get_mat_names()
    #     for mat in bpy.data.materials:
    #         if mat.name in mat_names:
    #             return True
    #     return False

    def execute(self, context):
        for mat_n in get_mat_names():
            m = bpy.data.materials.get(mat_n)
            if m is None:
                continue
            cur_version = [int(v) for v in m.abs_plastic_version.split(".")]
            cur_version[-1] -= 1
            m.abs_plastic_version = str(cur_version)[1:-1].replace(", ", ".")
        self.report({"INFO"}, "ABS Plastic Materials were marked as outdated")
        return {"FINISHED"}

    #############################################
