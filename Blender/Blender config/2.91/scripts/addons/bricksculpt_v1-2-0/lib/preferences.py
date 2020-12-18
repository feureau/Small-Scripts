# Copyright (C) 2018 Christopher Gearhart
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

# Blender imports
import bpy
from bpy.types import AddonPreferences
from bpy.props import *

# updater import
from ..functions.common import *


class BRICKSCULPT_AP_preferences(AddonPreferences):
    bl_idname = __package__[:__package__.index(".lib")]

    # general prefs
    ui_text_color = FloatVectorProperty(
        name="Text Color",
        description="Color of the BrickSculpt interface text drawn to the 3D viewport",
        subtype="COLOR",
        size=4,
        min=0, max=1,
        default=(1, 1, 1, 1),
    )
    ui_text_scale = FloatProperty(
        name="Text Scale",
        description="Color of the BrickSculpt interface text drawn to the 3D viewport",
        min=0.5, max=2,
        default=1.3,
    )
    auto_append_abs_materials = BoolProperty(
        name="Auto-Append ABS Materials",
        description="Automatically import ABS Plastic Materials (if installed) when starting BrickSculpt session",
        default=False,
    )
    merge_inconsistent_mats = BoolProperty(
        name="Merge Inconsistent Materials",
        description="Merge bricks together even if they have different colors",  # (the most prominent color will be chosen)",
        default=False,
    )
    allow_editing_of_internals = BoolProperty(
        name="Allow Editing of Internals",
        description="Allow BrickSculpt to create bricks on the inside of your model (disabled by default, as this may cause unwanted behavior when drawing on the outer shell as the cursor passes between bricks)",
        default=False,
    )
    enable_layer_soloing = BoolProperty(
        name="Enable Layer Soloing",
        description="Enable the 'ctrl' shortcut to solo a layer of the model",
        default=False,
    )

	# addon updater preferences
    auto_check_update = BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months = IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0, min=0)
    updater_intrval_days = IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7, min=0)
    updater_intrval_hours = IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        min=0, max=23,
        default=0)
    updater_intrval_minutes = IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        min=0, max=59,
        default=0)

    def draw(self, context):
        layout = self.layout
        right_align(layout)

        col = layout.column()
        col.prop(self, "ui_text_color")
        col.prop(self, "ui_text_scale")
        col = layout.column(align=True)
        col.prop(self, "auto_append_abs_materials")
        col.prop(self, "merge_inconsistent_mats")
        col.prop(self, "allow_editing_of_internals")
        col.prop(self, "enable_layer_soloing")
