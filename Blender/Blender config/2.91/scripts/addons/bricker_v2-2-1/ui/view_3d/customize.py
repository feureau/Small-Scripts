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
from ...lib.caches import cache_exists
from ...functions import *


class VIEW3D_PT_bricker_customize(BrickerPanel, Panel):
    bl_label       = "Customize Model"
    bl_idname      = "VIEW3D_PT_bricker_customize"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not (cm.model_created or cm.animated):
            return False
        if cm.last_instance_method == "POINT_CLOUD":
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if cm.animated:
            layout.label(text="Not available for animations")
            return
        elif cm.brickifying_in_background:
            col = layout.column(align=True)
            col.label(text="Model is brickifying...")
            return
        elif matrix_really_is_dirty(cm):
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH").split_before_update = True
            if cm.customized and not cm.matrix_lost:
                row = col.row(align=True)
                row.label(text="Prior customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return
        elif not cm.last_split_model:
            col = layout.column(align=True)
            col.label(text="Model must be split to customize:")
            col.operator("bricker.brickify", text="Split & Update Model", icon="FILE_REFRESH").split_before_update = True
            return
        elif not cache_exists(cm):
            layout.label(text="Matrix not cached!", icon="ERROR")
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            if cm.customized:
                row = col.row(align=True)
                row.label(text="Customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return

        # display BrickSculpt tools
        col = layout.column(align=True)
        col.enabled = is_bricksculpt_installed()
        # col.active = False
        col.label(text="BrickSculpt Tools:")
        if is_bricksculpt_installed():
            col.operator("bricksculpt.run_tool", text="Draw/Cut Tool", icon="SCULPTMODE_HLT").mode = "DRAW"
            col.operator("bricksculpt.run_tool", text="Merge/Split Tool", icon="AUTOMERGE_ON").mode = "MERGE_SPLIT"
            row = col.row(align=True)
            row.operator("bricksculpt.run_tool", text="Paintbrush Tool", icon="BRUSH_DATA").mode = "PAINT"
            if bpy.data.texts.find("BrickSculpt (Bricker Addon) log") >= 0:
                split = layout_split(layout, factor=0.9)
                split.operator("bricksculpt__bricker_addon_.report_error", text="Report Error", icon="URL")
                split.operator("bricksculpt__bricker_addon_.close_report_error", text="", icon="PANEL_CLOSE")
            # allow the user to import abs materials from here
            if brick_materials_installed() and not brick_materials_imported():
                layout.operator("abs.append_materials", text="Import Brick Materials", icon="IMPORT")
        else:
            col.operator("bricker.bricksculpt_null", text="Draw/Cut Tool", icon="GREASEPENCIL").mode = "DRAW"
            col.operator("bricker.bricksculpt_null", text="Merge/Split Tool", icon="SCULPTMODE_HLT").mode = "MERGE_SPLIT"
            col.operator("bricker.bricksculpt_null", text="Paintbrush Tool", icon="BRUSH_DATA").mode = "PAINT"
            col = layout.column(align=True)
            col.scale_y = 0.7
            col.label(text="'BrickSculpt' addon not installed")
            col = layout.column(align=True)
            col.operator("wm.url_open", text="View Website", icon="WORLD").url = "http://www.blendermarket.com/products/bricksculpt"
            # row = col.row(align=True)
            # row.scale_y = 0.7
            # row.label(text="BrickSculpt coming soon to")
            # row = col.row(align=True)
            # row.scale_y = 0.7
            # row.label(text="the Blender Market:")
            # col = layout.column(align=True)
            # row = col.row(align=True)
            # row.operator("wm.url_open", text="View Website", icon="WORLD").url = "https://www.blendermarket.com/creators/bricksbroughttolife"
            # layout.split()
            # layout.split()
        col.separator()

        # col1 = layout.column(align=True)
        # col1.label(text="Selection:")
        # split = layout_split(col1, factor=0.5)
        # # set top exposed
        # col = split.column(align=True)
        # col.operator("bricker.select_bricks_by_type", text="By Type")
        # # set bottom exposed
        # col = split.column(align=True)
        # col.operator("bricker.select_bricks_by_size", text="By Size")


class VIEW3D_PT_bricker_legacy_customization_tools(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Legacy Tools"
    bl_parent_id   = "VIEW3D_PT_bricker_customize"
    bl_idname      = "VIEW3D_PT_bricker_legacy_customization_tools"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not cm.model_created:
            return False
        if cm.last_instance_method == "POINT_CLOUD":
            return False
        if matrix_really_is_dirty(cm):
            return False
        if not cm.last_split_model:
            return False
        # if cm.build_is_dirty:
        #     return False
        if cm.brickifying_in_background:
            return False
        if not cache_exists(cm):
            return False
        prefs = get_addon_preferences()
        return prefs.show_legacy_customization_tools

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col1 = layout.column(align=True)
        col1.label(text="Brick Operations:")
        split = layout_split(col1, factor=0.5)
        split.operator("bricker.split_bricks", text="Split")
        split.operator("bricker.merge_bricks", text="Merge")
        col1.operator("bricker.draw_adjacent", text="Draw Adjacent Bricks")
        col1.operator("bricker.change_brick_type", text="Change Type")
        col1.operator("bricker.change_brick_material", text="Change Material")
        # col1.operator("bricker.redraw_bricks")
