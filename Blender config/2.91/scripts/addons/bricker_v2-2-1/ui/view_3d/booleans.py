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


class VIEW3D_PT_bricker_booleans(BrickerPanel, Panel):
    """ Booleans for the Bricker Model """
    bl_label       = "Booleans"
    bl_idname      = "VIEW3D_PT_bricker_booleans"
    bl_parent_id   = "VIEW3D_PT_bricker_model_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        # if created_with_unsupported_version(cm):
        #     return False
        # if not (cm.model_created or cm.animated):
        #     return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        layout.operator("bricker.update_booleans", icon="FILE_REFRESH")

        # draw UI list and list actions
        rows = 2 if len(cm.booleans) < 2 else 4
        row = layout.row()
        row.template_list("BRICKER_UL_booleans", "", cm, "booleans", cm, "boolean_index", rows=rows)

        col = row.column(align=True)
        col.operator("bricker.bool_list_action", text="", icon="ADD" if b280() else "ZOOMIN").action = "ADD"
        col.operator("bricker.bool_list_action", icon="REMOVE" if b280() else "ZOOMOUT", text="").action = "REMOVE"
        # col.menu("BRICKER_MT_specials", icon="DOWNARROW_HLT", text="")
        if len(cm.booleans) > 1:
            col.separator()
            col.operator("bricker.bool_list_action", icon="TRIA_UP", text="").action = "UP"
            col.operator("bricker.bool_list_action", icon="TRIA_DOWN", text="").action = "DOWN"

        if cm.boolean_index == -1:
            return

        active_bool = cm.booleans[cm.boolean_index]

        # layout.prop(active_bool, "type")

        if active_bool.type == "OBJECT":
            layout.prop(active_bool, "object")
        else:
            layout.prop(active_bool, "model_name")
