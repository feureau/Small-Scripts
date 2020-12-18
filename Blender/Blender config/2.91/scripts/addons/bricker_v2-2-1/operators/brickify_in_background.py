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
import random
import time
import bmesh
import os
import sys
import math
import json
import marshal

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Module imports
from .bevel import BRICKER_OT_bevel
from .cache import *
from .brickify import BRICKER_OT_brickify
from ..lib.undo_stack import *
from ..functions import *
from ..subtrees.background_processing.classes.job_manager import JobManager


class BRICKER_OT_brickify_in_background(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        return bpy.props.bricker_initialized and scn.cmlist_index != -1

    def execute(self, context):
        # get active context info
        scn, cm, n = get_active_context_info(context)
        # run brickify for current frame
        if "ANIM" in self.action:
            BRICKER_OT_brickify.brickify_current_frame(self.frame, self.action, in_background=True)
        else:
            BRICKER_OT_brickify.brickify_active_frame(self.action)
        # save last cache to prop temporarily
        bpy.props.bfm_cache_bytes_hex = marshal.dumps(bricker_bfm_cache[cm.id]).hex()
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class variables

    frame = IntProperty(default=-1)
    action = StringProperty(default="CREATE")

    #############################################


class BRICKER_OT_stop_brickifying_in_background(bpy.types.Operator):
    """ Stop the background brickification process """
    bl_idname = "bricker.stop_brickifying_in_background"
    bl_label = "Stop the background brickification process"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        return bpy.props.bricker_initialized and scn.cmlist_index != -1

    def execute(self, context):
        scn, cm, n = get_active_context_info(context)
        cm.stop_background_process = True
        job_manager = JobManager.get_instance(cm.id)
        if "ANIM" in self.action and job_manager.num_completed_jobs() > 0:
            updated_stop_frame = False
            completed_frames = str_to_list(cm.completed_frames)
            # set end frame to last consecutive completed frame and toss non-consecutive frames
            for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                if frame not in completed_frames and not updated_stop_frame:
                    # set end frame to last consecutive completed frame
                    updated_stop_frame = True
                    cm.last_stop_frame = max(cm.last_start_frame, frame - 1)
                    # cm.stop_frame = max(cm.last_start_frame, frame - 1)
                    cm.stop_frame = cm.stop_frame  # run updater to allow 'update_model'
                if frame in completed_frames and updated_stop_frame:
                    # remove frames that cannot be saved
                    bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent_f_%(frame)s" % locals())
                    delete(bricker_parent)
                    bricker_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                    delete(bricker_bricks_coll.objects)
                    bpy_collections().remove(bricker_bricks_coll)
            # hide objs unless on scene current frame
            for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                set_frame_visibility(cm, frame)
            # finish animation and kill running jobs
            finish_animation(cm)
        else:
            bpy.ops.bricker.delete_model()
        cm.brickifying_in_background = False
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        cm = get_active_context_info()[1]
        self.action = get_action(cm)

    #############################################
