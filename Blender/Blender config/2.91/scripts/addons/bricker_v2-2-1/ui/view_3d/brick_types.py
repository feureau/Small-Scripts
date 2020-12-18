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


class VIEW3D_PT_bricker_brick_types(BrickerPanel, Panel):
    bl_label       = "Brick Types"
    bl_idname      = "VIEW3D_PT_bricker_brick_types"
    bl_parent_id   = "VIEW3D_PT_bricker_model_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        # right_align(layout)
        scn, cm, _ = get_active_context_info()

        # col = layout.column(align=True)
        layout.prop(cm, "brick_type", text="")

        if mergable_brick_type(cm.brick_type):
            col = layout.column(align=True)
            col.label(text="Max Size:")
            row = col.row(align=True)
            col.prop(cm, "max_width", text="Width")
            col.prop(cm, "max_depth", text="Depth")
            col.active = cm.instance_method != "POINT_CLOUD"

            col = layout.column(align=True)
            right_align(col)
            col.prop(cm, "legal_bricks_only")
            col.active = cm.instance_method != "POINT_CLOUD"

        if cm.brick_type == "CUSTOM" or cm.last_split_model:
            col = layout.column(align=True)
            if cm.brick_type == "CUSTOM":
                col.label(text="Brick Type Object:")
            elif cm.last_split_model:
                col.label(text="Custom Brick Objects:")
            for prop in ("custom_object1", "custom_object2", "custom_object3"):
                if prop[-1] == "2" and cm.brick_type == "CUSTOM":
                    col.label(text="Distance Offset:")
                    row = col.row(align=True)
                    row.prop(cm, "dist_offset", text="")
                    if cm.last_split_model:
                        col = layout.column(align=True)
                        col.label(text="Other Objects:")
                    else:
                        break
                split = layout_split(col, factor=0.825)
                col1 = split.column(align=True)
                col1.prop_search(cm, prop, scn, "objects", text="")
                col1 = split.column(align=True)
                col1.operator("bricker.redraw_custom_bricks", icon="FILE_REFRESH", text="").target_prop = prop
