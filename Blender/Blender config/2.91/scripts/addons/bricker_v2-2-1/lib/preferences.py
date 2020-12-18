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

# Blender imports
import bpy
from bpy.types import AddonPreferences
from bpy.props import *

# Module imports
from .. import addon_updater_ops
from ..functions.common import *
from ..functions.property_callbacks import *


class BRICKER_AP_preferences(AddonPreferences):
    bl_idname = __package__[:__package__.index(".lib")]

    # addon preferences
    brick_height_default = bpy.props.EnumProperty(
        name="Default Brick Height Setting",
        description="Method for setting default 'Model Height' value when new model is added",
        items=[
            ("RELATIVE", "Relative (recommended)", "'Model Height' setting defaults to fixed number of bricks tall when new model is added"),
            ("ABSOLUTE", "Absolute", "'Model Height' setting defaults to fixed height in decimeters when new model is added"),
        ],
        default="RELATIVE",
    )
    relative_brick_height = bpy.props.IntProperty(
        name="Model Height (bricks)",
        description="Default height for bricker models in bricks (standard deviation of 1 brick)",
        min=1,
        default=20,
    )
    absolute_brick_height = bpy.props.FloatProperty(
        name="Brick Height (mm)",
        description="Default brick height in millimeters",
        min=0.001,
        precision=3,
        default=9.6,
    )
    brickify_in_background = EnumProperty(
        name="Brickify in Background",
        description="Run brickify calculations in background (if disabled, user interface will freeze during calculation)",
        items=[
            ("AUTO", "Auto", "Automatically determine whether to brickify in background or active Blender window based on model complexity"),
            ("ON", "On", "Run brickify calculations in background"),
            ("OFF", "Off", "Run brickify calculations in active Blender window (user interface will freeze during calculation)"),
        ],
        default="AUTO",
    )
    max_workers = IntProperty(
        name="Max Worker Instances",
        description="Maximum number of Blender instances allowed to run in background for Bricker calculations (larger numbers are faster at a higher CPU load; 0 for local calculation)",
        min=0, max=24,
        update=update_job_manager_properties,
        default=5,
    )
    # CUSTOMIZE SETTINGS
    show_legacy_customization_tools = BoolProperty(
        name="Show Legacy Brick Operations",
        description="Reveal the old brick customization tools in the Bricker UI",
        default=False,
    )
    # Other
    show_debugging_tools = BoolProperty(
        name="Show Debugging Tools",
        description="Show advanced tools for debugging issues with Bricker",
        default=False,
    )
    auto_refresh_model_info = BoolProperty(
        name="Auto Refresh Model Info",
        description="Refresh model info automatically each time the 'Brickify' process is run (may slow down Brickify process slightly)",
        default=True,
    )

	# addon updater preferences
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months = bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0, min=0)
    updater_intrval_days = bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=7, min=0)
    updater_intrval_hours = bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        min=0, max=23,
        default=0)
    updater_intrval_minutes = bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        min=0, max=59,
        default=0)

    def draw(self, context):
        layout = self.layout
        col1 = layout.column(align=True)

        # draw addon prefs
        row = col1.row(align=False)
        split = layout_split(row, factor=0.275)
        col = split.column(align=True)
        col.label(text="Default Brick Height:")
        col = split.column(align=True)
        split = layout_split(col, factor=0.5)
        col = split.column(align=True)
        col.prop(self, "brick_height_default", text="")
        col = split.column(align=True)
        if self.brick_height_default == "RELATIVE":
            col.prop(self, "relative_brick_height")
        else:
            col.prop(self, "absolute_brick_height")
        col1.separator()
        col1.separator()
        row = col1.row(align=False)
        split = layout_split(row, factor=0.275)
        col = split.column(align=True)
        col.label(text="Brickify in Background:")
        col = split.column(align=True)
        col.prop(self, "brickify_in_background", text="")
        if self.brickify_in_background != "OFF":
            col = split.column(align=True)
            col.prop(self, "max_workers", text="Max Worker Instances")
        col1.separator()
        col1.separator()
        row = col1.row(align=True)
        right_align(row)
        col = row.column()
        # col.prop(self, "auto_refresh_model_info")
        col.prop(self, "show_legacy_customization_tools")
        col.prop(self, "show_debugging_tools")
        col1.separator()


        # updater draw function
        addon_updater_ops.update_settings_ui(self,context)
