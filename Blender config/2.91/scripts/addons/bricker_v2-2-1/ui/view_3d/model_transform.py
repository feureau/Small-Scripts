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


class VIEW3D_PT_bricker_model_transform(BrickerPanel, Panel):
    bl_label       = "Model Transform"
    bl_idname      = "VIEW3D_PT_bricker_model_transform"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if cm.model_created or cm.animated:
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, n = get_active_context_info()

        col = layout.column(align=True)
        # col.active = cm.animated or cm.last_split_model
        right_align(col)

        row = col.row(align=True)
        row.prop(cm, "apply_to_source_object")

        row = col.row(align=True)
        row.prop(cm, "expose_parent")

        # row = col.row(align=True)
        # parent = bpy.data.objects["Bricker_%(n)s_parent" % locals()]
        # row = layout.row()
        # row.column().prop(parent, "location")
        # if parent.rotation_mode == "QUATERNION":
        #     row.column().prop(parent, "rotation_quaternion", text="Rotation")
        # elif parent.rotation_mode == "AXIS_ANGLE":
        #     row.column().prop(parent, "rotation_axis_angle", text="Rotation")
        # else:
        #     row.column().prop(parent, "rotation_euler", text="Rotation")
        # # row.column().prop(parent, "scale")
        # layout.prop(parent, "rotation_mode")
        # layout.prop(cm, "transform_scale")
