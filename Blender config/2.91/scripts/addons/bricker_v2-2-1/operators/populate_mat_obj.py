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

# Module imports
from ..functions import *


class BRICKER_OT_populate_mat_obj(bpy.types.Operator):
    """Add all ABS Plastic Materials to the list of materials to use for Brickifying object"""
    bl_idname = "bricker.add_abs_plastic_materials"
    bl_label = "Add ABS Plastic Materials"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm, _ = get_active_context_info(context)
            mat_obj = get_mat_obj(cm)
            cm.material_is_dirty = True
            for mat_name in get_abs_mat_names(all=False):
                mat = bpy.data.materials.get(mat_name)
                if mat is not None and mat_name not in mat_obj.data.materials:
                    mat_obj.data.materials.append(mat)

        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
