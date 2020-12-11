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
from ...operators.test_brick_generators import *
from ...functions import *
from ... import addon_updater_ops


class VIEW3D_PT_bricker_advanced(BrickerPanel, Panel):
    bl_label       = "Advanced"
    bl_idname      = "VIEW3D_PT_bricker_advanced"
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
        scn, cm, n = get_active_context_info()

        # Alert user that update is available
        if addon_updater_ops.updater.update_ready:
            col = layout.column(align=True)
            col.scale_y = 0.7
            col.label(text="Bricker update available!", icon="INFO")
            col.label(text="Install from Bricker addon prefs")
            layout.separator()

        # draw test brick generator button (for testing purposes only)
        if BRICKER_OT_test_brick_generators.draw_ui_button():
            col = layout.column(align=True)
            col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")

        # shell property
        col = layout.column(align=True)
        col.label(text="Shell:")
        col.prop(cm, "brick_shell", text="")
        if cm.brick_shell == "OUTSIDE":
            col.prop(cm, "calculation_axes", text="Axes")

        # grid properties
        col = layout.column(align=True)
        col.label(text="Grid Offset:")
        row = col.row(align=True)
        row.prop(cm, "grid_offset", text="")

        col = layout.column(align=True)
        right_align(col)
        col.prop(cm, "use_absolute_grid_anim" if cm.use_animation else "use_absolute_grid")

        # if not cm.animated:
        col = layout.column(align=True)
        col.label(text="Instance Method:")
        col.prop(cm, "instance_method", text="")

        # model orientation property
        if not cm.use_animation and not (cm.model_created or cm.animated):
            # if not b280():
            layout.separator()
            col = layout.column(align=True)
            right_align(col)
            col.prop(cm, "use_local_orient", text="Use Local Orientation")



class VIEW3D_PT_bricker_ray_casting(BrickerPanel, Panel):
    bl_label       = "Ray Casting"
    bl_idname      = "VIEW3D_PT_bricker_ray_casting"
    bl_parent_id   = "VIEW3D_PT_bricker_advanced"

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        # right_align(layout)
        scn, cm, n = get_active_context_info()

        col = layout.column(align=True)
        col.prop(cm, "insideness_ray_cast_dir", text="")

        col = layout.column(align=True)
        right_align(col)
        col.prop(cm, "use_normals")
        col.prop(cm, "calc_internals")
