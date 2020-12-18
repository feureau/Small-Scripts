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
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..panel_info import *
from ...functions import *


class VIEW3D_PT_bricker_smoke_settings(BrickerPanel, Panel):
    bl_label       = "Smoke Settings"
    bl_idname      = "VIEW3D_PT_bricker_smoke_settings"
    bl_parent_id   = "VIEW3D_PT_bricker_model_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        source = cm.source_obj
        if source is None:
            return False
        return is_smoke(source)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        source = cm.source_obj

        col = layout.column(align=True)
        if is_smoke(source):
            row = col.row(align=True)
            row.prop(cm, "smoke_density", text="Density")
            row = col.row(align=True)
            row.prop(cm, "smoke_quality", text="Quality")

        if is_smoke(source):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Smoke Color:")
            row = col.row(align=True)
            row.prop(cm, "smoke_brightness", text="Brightness")
            row = col.row(align=True)
            row.prop(cm, "smoke_saturation", text="Saturation")
            row = col.row(align=True)
            row.label(text="Flame Color:")
            row = col.row(align=True)
            row.prop(cm, "flame_color", text="")
            row = col.row(align=True)
            row.prop(cm, "flame_intensity", text="Intensity")
