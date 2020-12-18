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


class VIEW3D_PT_bricker_detailing(BrickerPanel, Panel):
    bl_label       = "Detailing"
    bl_idname      = "VIEW3D_PT_bricker_detailing"
    bl_parent_id   = "VIEW3D_PT_bricker_model_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        return cm.brick_type != "CUSTOM"

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if cm.brick_type == "CUSTOM":
            col = layout.column(align=True)
            col.scale_y = 0.7
            row = col.row(align=True)
            row.label(text="(ignored for custom brick types)")
            layout.active = False
            layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Studs:")
        row = col.row(align=True)
        row.prop(cm, "stud_detail", text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Logo:")
        row = col.row(align=True)
        row.prop(cm, "logo_type", text="")
        if cm.logo_type != "NONE":
            if cm.logo_type == "LEGO":
                row = col.row(align=True)
                row.prop(cm, "logo_resolution", text="Resolution")
                row.prop(cm, "logo_decimate", text="Decimate")
                row = col.row(align=True)
            else:
                row = col.row(align=True)
                row.prop_search(cm, "logo_object", scn, "objects", text="")
                row = col.row(align=True)
                row.prop(cm, "logo_scale", text="Scale")
            row.prop(cm, "logo_inset", text="Inset")
            col = layout.column(align=True)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Underside:")
        row = col.row(align=True)
        col = row.column(align=True)
        col.active = cm.instance_method != "POINT_CLOUD"
        col.prop(cm, "hidden_underside_detail", text="")
        # row = col2.row(align=True)
        row.prop(cm, "exposed_underside_detail", text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Circles:")
        row = col.row(align=True)
        row.prop(cm, "circle_verts", text="Vertices")

        col = layout.column(align=True)
        row1 = col.row(align=True)
        col1 = row1.column(align=True)
        col1.label(text="Bevel:")
        if not (cm.model_created or cm.animated) or cm.brickifying_in_background:
            row = col.row(align=True)
            # right_align(row)
            row.prop(cm, "bevel_added", text="Bevel Bricks")
            return
        try:
            test_brick = get_bricks()[0]
            bevel = test_brick.modifiers[test_brick.name + "_bvl"]
            col2 = row1.column(align=True)
            row = col2.row(align=True)
            row.prop(cm, "bevel_show_render", text="", icon="RESTRICT_RENDER_OFF", toggle=True)
            row.prop(cm, "bevel_show_viewport", text="", icon="RESTRICT_VIEW_OFF", toggle=True)
            row.prop(cm, "bevel_show_edit_mode", text="", icon="EDITMODE_HLT", toggle=True)
            row = col.row(align=True)
            row.prop(cm, "bevel_width", text="Width")
            row = col.row(align=True)
            row.prop(cm, "bevel_segments", text="Segments")
            row = col.row(align=True)
            row.prop(cm, "bevel_profile", text="Profile")
            row = col.row(align=True)
            row.operator("bricker.bevel", text="Remove Bevel", icon="CANCEL")
        except (IndexError, KeyError):
            row = col.row(align=True)
            row.operator("bricker.bevel", text="Bevel bricks", icon="MOD_BEVEL")


# class VIEW3D_PT_bricker_detailing_bevel(BrickerPanel, Panel):
#     bl_label       = "Bevel"
#     bl_idname      = "VIEW3D_PT_bricker_detailing_bevel"
#     bl_parent_id   = "VIEW3D_PT_bricker_detailing"
#     bl_options     = {"DEFAULT_CLOSED"}
#
#     @classmethod
#     def poll(self, context):
#         if not settings_can_be_drawn():
#             return False
#         scn, cm, _ = get_active_context_info()
#         return cm.brick_type != "CUSTOM"
#
#     def draw_header(self, context):
#         scn, cm, _ = get_active_context_info()
#         if not (cm.model_created or cm.animated) or cm.brickifying_in_background:
#             self.layout.prop(cm, "bevel_added", text="")
#
#     def draw(self, context):
#         layout = self.layout
#         scn, cm, _ = get_active_context_info()
#         if not (cm.model_created or cm.animated) or cm.brickifying_in_background:
#             return
#
#         col = layout.column(align=True)
#         try:
#             test_brick = get_bricks()[0]
#             bevel = test_brick.modifiers[test_brick.name + "_bvl"]
#             col2 = row1.column(align=True)
#             row = col2.row(align=True)
#             row.prop(cm, "bevel_show_render", text="", icon="RESTRICT_RENDER_OFF", toggle=True)
#             row.prop(cm, "bevel_show_viewport", text="", icon="RESTRICT_VIEW_OFF", toggle=True)
#             row.prop(cm, "bevel_show_edit_mode", text="", icon="EDITMODE_HLT", toggle=True)
#             row = col.row(align=True)
#             row.prop(cm, "bevel_width", text="Width")
#             row = col.row(align=True)
#             row.prop(cm, "bevel_segments", text="Segments")
#             row = col.row(align=True)
#             row.prop(cm, "bevel_profile", text="Profile")
#             row = col.row(align=True)
#             row.operator("bricker.bevel", text="Remove Bevel", icon="CANCEL")
#         except (IndexError, KeyError):
#             row = col.row(align=True)
#             row.operator("bricker.bevel", text="Bevel bricks", icon="MOD_BEVEL")
