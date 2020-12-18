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
import time
import bmesh
import os
import math
import numpy as np

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler

# Module imports
from ..functions import *


class BRICKER_OT_apply_material(bpy.types.Operator):
    """Apply specified material to all bricks"""
    bl_idname = "bricker.apply_material"
    bl_label = "Apply Material"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not (cm.model_created or cm.animated):
            return False
        return True

    def execute(self, context):
        try:
            self.run_apply_material(context)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        self.set_action()

    #############################################
    # class methods

    def set_action(self):
        """ sets self.action """
        scn, cm, _ = get_active_context_info()
        if cm.material_type == "SOURCE":
            self.action = "INTERNAL"
        elif cm.material_type == "CUSTOM":
            self.action = "CUSTOM"
        elif cm.material_type == "RANDOM":
            self.action = "RANDOM"

    @timed_call(label="Total Time Elapsed")
    def run_apply_material(self, context):

        # set up variables
        scn, cm, _ = get_active_context_info(context)
        bricks = get_bricks()
        cm.last_material_type = cm.material_type
        mat_shell_depth = cm.mat_shell_depth
        last_split_model = cm.last_split_model
        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame) if cm.animated else [-1]:
            # get bricksdict
            bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=frame)
            if bricksdict is None and self.action != "CUSTOM":
                self.report({"WARNING"}, "Materials could not be applied manually. Please run 'Update Model'")
                cm.matrix_is_dirty = True
                return
            # apply random material
            if self.action == "RANDOM":
                self.apply_random_materials(scn, cm, context, bricks, bricksdict)
            # apply custom or internal material
            else:
                # get material
                if self.action == "CUSTOM":
                    mat = cm.custom_mat
                elif self.action == "INTERNAL":
                    mat = cm.internal_mat
                if mat is None:
                    self.report({"WARNING"}, "Specified material doesn't exist")

                for brick in bricks:
                    # update bricksdict mat_name values for split models
                    if last_split_model and bricksdict is not None and self.action == "CUSTOM":
                        cur_key = get_dict_key(brick.name)
                        brick_d = bricksdict[cur_key]
                        if brick_d["custom_mat_name"] and is_mat_shell_val(brick_d["val"], mat_shell_depth):
                            continue
                        brick_d["mat_name"] = mat.name
                    # update the material slots
                    if self.action == "CUSTOM" or (self.action == "INTERNAL" and not is_on_shell(bricksdict, brick.name.split("__")[-1], zstep=cm.zstep, shell_depth=cm.mat_shell_depth) and cm.mat_shell_depth <= cm.last_mat_shell_depth):
                        if len(brick.material_slots) == 0:
                            # Assign material to object data
                            brick.data.materials.append(mat)
                            brick.material_slots[0].link = "OBJECT"
                        elif self.action == "CUSTOM" and len(brick.material_slots) > 1:
                            clear_existing_materials(brick, from_idx=1)
                        # assign material to mat slot
                        brick.material_slots[0].material = mat
                # update bricksdict mat_name values for not split models
                if self.action == "CUSTOM" and not last_split_model and bricksdict is not None:
                    for brick_d in bricksdict.values():
                        if brick_d["draw"] and brick_d["parent"] == "self":
                            brick_d["mat_name"] = mat.name

        tag_redraw_areas(["VIEW_3D", "PROPERTIES", "NODE_EDITOR"])
        cm.material_is_dirty = False
        cm.last_mat_shell_depth = cm.mat_shell_depth

    @classmethod
    def apply_random_materials(self, scn, cm, context, bricks, bricksdict):
        # initialize list of brick materials
        brick_mats = []
        mat_obj = get_mat_obj(cm, typ="RANDOM")
        for mat in mat_obj.data.materials.keys():
            brick_mats.append(mat)
        if len(brick_mats) == 0:
            return
        # initialize variables
        rand_s0 = np.random.RandomState(0)
        random_mat_seed = cm.random_mat_seed
        if cm.last_split_model:
            # apply a random material to each brick
            dkeys = sorted(list(bricksdict.keys()))
            for brick in bricks:
                cur_key = get_dict_key(brick.name)
                brick_d = bricksdict[cur_key]
                if brick_d["custom_mat_name"] and is_mat_shell_val(brick_d["val"], mat_shell_depth):
                    continue
                # iterate seed and set random index
                rand_s0.seed(random_mat_seed + dkeys.index(cur_key))
                rand_idx = rand_s0.randint(0, len(brick_mats)) if len(brick_mats) > 1 else 0
                # Assign random material to object
                mat = bpy.data.materials.get(brick_mats[rand_idx])
                set_material(brick, mat)
                # update bricksdict
                brick_d["mat_name"] = mat.name
        else:
            # apply a random material to each random material slot
            brick = bricks[0]
            last_mat_slots = list(brick.material_slots.keys())
            if len(last_mat_slots) == len(brick_mats):
                for i in range(len(last_mat_slots)):
                    # iterate seed and set random index
                    rand_s0.seed(random_mat_seed + i)
                    rand_idx = 0 if len(brick_mats) == 1 else rand_s0.randint(0, len(brick_mats))
                    # Assign random material to object
                    mat_name = brick_mats.pop(rand_idx)
                    mat = bpy.data.materials.get(mat_name)
                    brick.material_slots[i].material = mat
