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
# NONE!

# Blender imports
import bpy
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..panel_info import *
from ...functions import *


class VIEW3D_PT_bricker_model_info(BrickerPanel, Panel):
    """ Display Matrix details for specified brick location """
    bl_label       = "Model Info"
    bl_idname      = "VIEW3D_PT_bricker_model_info"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if int(cm.version.split(".")[0]) < 2:
            return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        prefs = get_addon_preferences()
        if not prefs.auto_refresh_model_info:
            layout.operator("bricker.refresh_model_info", icon="FILE_REFRESH")

        col = layout.column(align=True)
        col.label(text="Piece count:")
        row = col.row(align=True)
        row.enabled = False
        row.prop(cm, "num_bricks_in_model", text="")

        col = layout.column(align=True)
        col.label(text="Material count:")
        row = col.row(align=True)
        row.enabled = False
        row.prop(cm, "num_materials_in_model", text="")

        col = layout.column(align=True)
        col.label(text="Weight (grams):")
        row = col.row(align=True)
        row.enabled = False
        row.prop(cm, "model_weight", text="")

        col = layout.column(align=True)
        col.label(text="Real-world dimensions:")
        row = col.row(align=True)
        row.enabled = False
        col = row.column(align=True)
        col.prop(cm, "real_world_dimensions", text="")
