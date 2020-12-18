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


class BRICKER_OT_revert_settings(Operator):
    """Revert Matrix settings to save model customizations"""
    bl_idname = "bricker.revert_matrix_settings"
    bl_label = "Revert Matrix Settings"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if matrix_really_is_dirty(cm):
            return True
        return False

    def execute(self, context):
        try:
            self.revert_matrix_settings(context)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # class methods

    def revert_matrix_settings(self, context, cm=None):
        cm = get_active_context_info(context, cm)[1]
        settings = json.loads(cm.last_matrix_settings)
        cm.brick_height = settings["brick_height"]
        cm.gap = settings["gap"]
        cm.brick_type = settings["brick_type"]
        cm.dist_offset = settings["dist_offset"]
        cm.include_transparency = settings["include_transparency"]
        cm.custom_object1 = bpy.data.objects.get(settings["custom_object1_name"])
        cm.custom_object2 = bpy.data.objects.get(settings["custom_object2_name"])
        cm.custom_object3 = bpy.data.objects.get(settings["custom_object3_name"])
        cm.insideness_ray_cast_dir = settings["insideness_ray_cast_dir"]
        cm.use_normals = settings["use_normals"]
        cm.grid_offset = settings["grid_offset"]
        cm.calc_internals = settings["calc_internals"]
        cm.brick_shell = settings["brick_shell"]
        cm.calculation_axes = settings["calculation_axes"]
        if cm.last_is_smoke:
            cm.smoke_density = settings["smoke_density"]
            cm.smoke_quality = settings["smoke_quality"]
            cm.smoke_brightness = settings["smoke_brightness"]
            cm.smoke_saturation = settings["smoke_saturation"]
            cm.flame_color = settings["flame_color"]
            cm.flame_intensity = settings["flame_intensity"]
        cm.matrix_is_dirty = False

    ################################################
