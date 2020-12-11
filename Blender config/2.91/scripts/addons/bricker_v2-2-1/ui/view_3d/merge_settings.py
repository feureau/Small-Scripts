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


class VIEW3D_PT_bricker_merge_settings(BrickerPanel, Panel):
    bl_label       = "Merging"
    bl_idname      = "VIEW3D_PT_bricker_merge_settings"
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
        return mergable_brick_type(cm.brick_type)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        layout.active = cm.instance_method != "POINT_CLOUD"
        internals_exist = check_if_internals_exist(cm)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "merge_type", text="")
        if cm.merge_type == "RANDOM":
            col = layout.column(align=True)
            col.prop(cm, "merge_seed")
        if internals_exist:
            col = layout.column(align=True)
            col.label(text="Merge Shell with Internals:")
            col.prop(cm, "merge_internals", text="")


class VIEW3D_PT_bricker_merge_alignment(BrickerPanel, Panel):
    bl_label       = "Alignment"
    bl_idname      = "VIEW3D_PT_bricker_merge_alignment"
    bl_parent_id   = "VIEW3D_PT_bricker_merge_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return mergable_brick_type(cm.brick_type) and cm.brick_type == "BRICKS_AND_PLATES"

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        layout.active = cm.instance_method != "POINT_CLOUD"

        col = layout.column(align=True)
        row = col.row(align=True)
        right_align(row)
        row.prop(cm, "align_bricks")
        if cm.align_bricks:
            col = layout.column(align=True)
            col.prop(cm, "offset_brick_layers")
