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
from bpy.props import *
from bpy.types import UIList

# Module imports
from ..functions import *


# ui list item actions
class BRICKER_OT_matlist_actions(bpy.types.Operator):
    bl_idname = "bricker.mat_list_action"
    bl_label = "Mat Slots List Action"

    action = bpy.props.EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("REMOVE", "Remove", ""),
            ("ADD", "Add", ""),
        )
    )

    # @classmethod
    # def poll(self, context):
    #     scn = context.scene
    #     for cm in scn.matlist:
    #         if cm.animated:
    #             return False
    #     return True

    def execute(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
            mat_obj = get_mat_obj(cm)
            idx = mat_obj.active_material_index

            if self.action == "REMOVE":
                self.remove_item(cm, mat_obj, idx)

            elif self.action == "DOWN" and idx < len(scn.cmlist) - 1:
                self.navigate_down(item)

            elif self.action == "UP" and idx >= 1:
                self.move_up(item)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    def remove_item(self, cm, mat_obj, idx):
        if idx >= len(mat_obj.data.materials) or idx < 0 or len(mat_obj.data.materials) == 0:
            return
        mat = mat_obj.data.materials.pop(index=idx)
        if not cm.last_split_model:
            cm.material_is_dirty = True
