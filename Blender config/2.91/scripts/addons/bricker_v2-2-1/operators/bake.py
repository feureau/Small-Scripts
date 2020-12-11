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
import os

# Blender imports
import bpy

# Module imports
from ..functions import *
from .cmlist_actions import *


class BRICKER_OT_bake_model(bpy.types.Operator):
    """Convert model from Bricker model to standard Blender object (applies transformation and clears Bricker data associated with the model; source object will be lost)"""
    bl_idname = "bricker.bake_model"
    bl_label = "Bake Model"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
        except IndexError:
            return False
        if (cm.model_created or cm.animated) and not cm.brickifying_in_background:
            return True
        return False

    def execute(self, context):
        scn, cm, n = get_active_context_info(context)
        cur_f = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
        # set is_brick/is_brickified_object to False
        bricks = get_bricks()
        # apply object transformation
        parent_clear(bricks)
        if cm.last_split_model:
            for brick in bricks:
                brick.is_brick = False
                brick.name = brick.name[8:]
        else:
            active_brick = bricks[0] if cm.model_created else bpy.data.objects.get("Bricker_%(n)s_bricks_f_%(cur_f)s" % locals())
            active_brick.is_brickified_object = False
            active_brick.name = "%(n)s_bricks" % locals()
        # delete parent/source/dup
        objs_to_delete = [bpy.data.objects.get("Bricker_%(n)s_parent" % locals()), cm.source_obj]
        if cm.animated:
            for f in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                objs_to_delete.append(bpy.data.objects.get("Bricker_%(n)s_f_%(f)s" % locals()))
                objs_to_delete.append(bpy.data.objects.get("Bricker_%(n)s_parent_f_%(f)s" % locals()))
                if f != cur_f:
                    objs_to_delete.append(bricks.pop(0 if f < cur_f else 1))
        for obj in objs_to_delete:
            bpy.data.objects.remove(obj, do_unlink=True)
        # clean up brick collection
        if cm.last_split_model:
            # rename brick collection
            cm.collection.name = cm.collection.name.replace("Bricker_", "")
        else:
            # delete brick collection
            brick_coll = cm.collection
            if b280():
                linked_colls = [cn for cn in bpy_collections() if brick_coll.name in cn.children]
                for col in linked_colls:
                    for brick in bricks:
                        col.objects.link(brick)
            if brick_coll is not None:
                bpy_collections().remove(brick_coll, do_unlink=True)
        # remove current cmlist index
        cm.model_created = False
        cm.animated = False
        BRICKER_OT_cm_list_action.remove_item(BRICKER_OT_cm_list_action, context, scn.cmlist_index)
        scn.cmlist_index = -1
        return{"FINISHED"}

    ################################################
