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

# Module imports
from ..functions import *


class BRICKER_OT_debug_toggle_view_source(bpy.types.Operator):
    """ Expose/hide source object (for dubugging purposes) """
    bl_idname = "bricker.debug_toggle_view_source"
    bl_label = "View Source Obj"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, n = get_active_context_info(context)
        return cm.animated or cm.model_created

    def execute(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
            if cm.source_obj.name in scn.objects:
                safe_unlink(cm.source_obj)
            else:
                safe_link(cm.source_obj)
            return {"FINISHED"}
        except:
            bricker_handle_exception()
            return {"CANCELLED"}

    #############################################
