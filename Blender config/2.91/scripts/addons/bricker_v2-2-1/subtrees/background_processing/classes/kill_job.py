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
from bpy.types import Operator

# Module imports
from .job_manager import *


class SCENE_OT_kill_job(Operator):
    """ Kills a job """
    bl_idname = "backproc.kill_job"
    bl_label = "Kill Job"
    bl_description = "Kills a job"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    # @classmethod
    # def poll(self, context):
    #     return bpy.context.object is not None

    def execute(self, context):
        if self.job_name not in self.job_manager.get_active_job_names():
            return {"CANCELLED"}
        self.job_manager.kill_job(self.job_name)
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        self.job_manager = JobManager.get_instance(-1)
        self.job_manager.max_workers = 5

    ###################################################
    # class variables

    job_name = StringProperty()

    ################################################
