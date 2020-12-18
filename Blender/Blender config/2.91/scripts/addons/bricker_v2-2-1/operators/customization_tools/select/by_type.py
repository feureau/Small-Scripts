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
import copy

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Module imports
from ...brickify import *
from ....functions import *


class BRICKER_OT_select_bricks_by_type(Operator):
    """Select bricks of specified type"""
    bl_idname = "bricker.select_bricks_by_type"
    bl_label = "Select Bricks by Type"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        return bpy.props.bricker_initialized and scn.cmlist_index != -1

    def execute(self, context):
        try:
            select_bricks(self.obj_names_dict, self.bricksdicts, brick_type=self.brick_type, all_models=self.all_models, only=self.only, include=self.include)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def check(self, context):
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=False)
        right_align(col)
        col.prop(self, "brick_type")
        if len(context.selected_objects) > 0:
            col.prop(self, "only")
        if len(scn.cmlist) > 1:
            col.prop(self, "all_models")
        if cm.last_shell_thickness > 1 or cm.last_internal_supports != "NONE":
            col.prop(self, "include")

    ################################################
    # initialization method

    def __init__(self):
        self.obj_names_dict = create_obj_names_dict(bpy.data.objects)
        self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        self.brick_type = "NONE"

    ###################################################
    # class variables

    # vars
    obj_names_dict = {}
    bricksdicts = {}

    # get items for brick_type prop
    def get_items(self, context):
        items = get_used_types()
        return items

    # define props for popup
    brick_type = EnumProperty(
        name="Type",
        description="Select all bricks of specified type",
        items=get_items,
    )
    only = BoolProperty(
        name="Only",
        description="Select only bricks of given type",
        default=False,
    )
    all_models = BoolProperty(
        name="All Models",
        description="Select bricks of given type from all models in file",
        default=False,
    )
    include = EnumProperty(
        name="Include",
        description="Include bricks on shell, inside shell, or both",
        items = [
            ("EXT", "Externals", ""),
            ("INT", "Internals", ""),
            ("BOTH", "Both", "")
        ],
        default="BOTH",
    )

    ###################################################
