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
from addon_utils import check, paths, enable
import bpy
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..panel_info import *
from ...lib.caches import cache_exists
from ...functions import *



class VIEW3D_PT_bricker_debugging_tools(BrickerPanel, Panel):
    bl_label       = "Debugging Tools"
    bl_idname      = "VIEW3D_PT_bricker_debugging_tools"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        prefs = get_addon_preferences()
        return prefs.show_debugging_tools

    def draw(self, context):
        layout = self.layout
        scn, cm, n = get_active_context_info()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("bricker.clear_cache", text="Clear Cache", icon="CON_TRANSFORM_CACHE")

        source_name = cm.source_obj.name if cm.source_obj else ""
        layout.operator("bricker.generate_brick", icon="MOD_BUILD")
        layout.operator("bricker.debug_toggle_view_source", icon="RESTRICT_VIEW_OFF" if source_name in scn.objects else "RESTRICT_VIEW_ON")


class VIEW3D_PT_bricker_matrix_details(BrickerPanel, Panel):
    """ Display Matrix details for specified brick location """
    bl_label       = "Brick Details"
    bl_idname      = "VIEW3D_PT_bricker_matrix_details"
    bl_parent_id   = "VIEW3D_PT_bricker_debugging_tools"
    bl_options     = {"DEFAULT_CLOSED"}


    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        # if created_with_unsupported_version(cm):
        #     return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if matrix_really_is_dirty(cm):
            layout.label(text="Matrix is dirty!")
            return
        if not cache_exists(cm):
            layout.label(text="Matrix not cached!")
            return

        col1 = layout.column(align=True)
        row = col1.row(align=True)
        row.prop(cm, "active_key", text="")

        if cm.animated:
            bricksdict = get_bricksdict(cm, d_type="ANIM", cur_frame=get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame))
        elif cm.model_created:
            bricksdict = get_bricksdict(cm)
        if bricksdict is None:
            layout.label(text="Matrix not available")
            return
        try:
            dkey = list_to_str(tuple(cm.active_key))
            brick_d = bricksdict[dkey]
        except Exception as e:
            layout.label(text="No brick details available")
            if len(bricksdict) == 0:
                print("[Bricker] Skipped drawing Brick Details")
            elif str(e)[1:-1] == dkey:
                pass
                # print("[Bricker] Key '" + str(dkey) + "' not found")
            elif dkey is None:
                print("[Bricker] Key not set (entered else)")
            else:
                print("[Bricker] Error fetching brick_d:", e)
            return

        col1 = layout.column(align=True)
        split = layout_split(col1, factor=0.35)
        # hard code keys so that they are in the order I want
        keys = [
            "name",
            "val",
            "draw",
            "co",
            "omitted",
            "near_face",
            "near_intersection",
            "near_normal",
            "mat_name",
            "custom_mat_name",
            "rgba",
            "parent",
            "size",
            "attempted_merge",
            "top_exposed",
            "bot_exposed",
            "type",
            "flipped",
            "rotated",
            "created_from",
        ]
        # draw keys
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(text="key:")
        for key in keys:
            row = col.row(align=True)
            row.label(text=key + ":")
        # draw values
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(text=dkey)
        for key in keys:
            try:
                row = col.row(align=True)
                row.label(text=str(brick_d[key]))
            except KeyError:
                continue
