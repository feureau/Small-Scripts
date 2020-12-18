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
import marshal

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_change_brick_material(Operator):
    """Change material for selected bricks"""
    bl_idname = "bricker.change_brick_material"
    bl_label = "Change Material"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        objs = context.selected_objects
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if cm.material_is_dirty or cm.matrix_is_dirty:
        # if cm.material_is_dirty or cm.matrix_is_dirty or cm.build_is_dirty:
            return False
        # check that at least 1 object is selected and is brick
        for obj in objs:
            if not obj.is_brick:
                continue
            return True
        return False

    def check(self, context):
        return self.mat_name is None

    def execute(self, context):
        try:
            # only reference self.mat_name once (runs get_items)
            target_mat_name = self.mat_name
            if target_mat_name == "NONE":
                return {"FINISHED"}
            scn = context.scene
            objs_to_select = []
            # iterate through cm_ids of selected objects
            for cm_id in self.obj_names_dict.keys():
                cm = get_item_by_id(scn.cmlist, cm_id)
                self.undo_stack.iterate_states(cm)
                # initialize vars
                bricksdict = marshal.loads(self.cached_bfm[cm_id])
                keys_to_update = set()
                cm.customized = True

                # iterate through cm_ids of selected objects
                for obj_name in self.obj_names_dict[cm_id]:
                    dkey = get_dict_key(obj_name)
                    # change material
                    keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[dkey]["size"], cm.zstep, key=dkey)
                    for k in keys_in_brick:
                        bricksdict[k]["mat_name"] = target_mat_name
                        bricksdict[k]["custom_mat_name"] = True
                    # add key to keys_to_update
                    keys_to_update.add(dkey)

                # draw modified bricks
                draw_updated_bricks(cm, bricksdict, keys_to_update, run_pre_merge=False)

                # add selected objects to objects to select at the end
                objs_to_select += context.selected_objects
            # select the new objects created
            select(objs_to_select)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        # initialize vars
        selected_objects = bpy.context.selected_objects
        self.obj_names_dict = create_obj_names_dict(selected_objects)
        self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        self.mat_name = "NONE"
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.cached_bfm = self.undo_stack.undo_push("change material", list(self.obj_names_dict.keys()))

    ###################################################
    # class variables

    # get items for mat_name prop
    def get_items(self, context):
        items = [("NONE", "None", "")] + [(k, k, "") for k in bpy.data.materials.keys()]
        return items

    # variables
    bricksdicts = {}
    obj_names_dict = {}

    # properties
    mat_name = bpy.props.EnumProperty(
        name="Material Name",
        description="Choose material to apply to selected bricks",
        items=get_items,
    )

    #############################################
