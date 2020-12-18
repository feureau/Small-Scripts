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
props = bpy.props

# Module imports
from ..lib.caches import *
from ..lib.undo_stack import *
from ..functions import *


class BRICKER_OT_clear_cache(bpy.types.Operator):
    """Clear brick mesh and matrix cache (Model customizations will be lost)"""
    bl_idname = "bricker.clear_cache"
    bl_label = "Clear Cache"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
            self.undo_stack.iterate_states(cm)
            cm.matrix_is_dirty = True
            clear_caches()
            # clear all duplicated sources for brickified animations
            if cm.animated:
                dup_name_base = "Bricker_%(n)s_f_" % locals()
                dupes = [bpy.data.objects.get(dup_name_base + str(cf)) for cf in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame)]
                delete(dupes)
        except:
            bricker_handle_exception()

        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('clear_cache')

    #############################################
