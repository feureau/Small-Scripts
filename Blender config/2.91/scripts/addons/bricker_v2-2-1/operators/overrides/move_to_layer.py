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
from bpy.props import *

# Module imports
from ...functions.common import *

class OBJECT_OT_move_to_layer_override(Operator):
    """Move to Layer functionality"""
    bl_idname = "bricker.move_to_layer_override"
    bl_label = "Move to Layer Override"
    bl_options = {"REGISTER", "INTERNAL", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        ev = []
        event = self.event
        if event.ctrl:
            ev.append("Ctrl")
        if event.shift:
            ev.append("Shift")
        if event.alt:
            ev.append("Alt")
        if event.oskey:
            ev.append("OS")
        changed = [i for i, (l, s) in
                enumerate(zip(self.layers, self.prev_sel))
                if l != s]

        # print("+".join(ev), event.type, event.value, changed)
        # pick only the changed one
        if not (event.ctrl or event.shift) and changed:
            self.layers = [i in changed for i in range(20)]
        self.prev_sel = self.layers[:]

        self.run_move(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        self.layers = [any(o.layers[i] for o in context.selected_objects)
                      for i in range(20)]
        self.event = event
        self.object_names = [o.name for o in context.selected_objects]
        self.prev_sel = self.layers[:]
        return context.window_manager.invoke_props_popup(self, event)

    def check(self, context):
        return True # thought True updated.. not working

    ###################################################
    # class variables

    layers = BoolVectorProperty(
        name="Layers",
        subtype="LAYER",
        description="Object Layers",
        size=20,
        )
    event = None
    object_names = []
    prev_sel = []

    ################################################
    # class methods

    def run_move(self, context):
        scn = context.scene
        for name in self.object_names:
            obj = scn.objects.get(name)
            obj.layers = self.layers
            if not obj.is_brickified_object or obj.cmlist_id == -1:
                continue
            cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
            if not cm.animated:
                continue
            n = get_source_name(cm)
            for f in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                bricks_cur_f = bpy.data.objects.get("Bricker_%(n)s_bricks_f_%(f)s" % locals())
                if bricks_cur_f is not None and bricks_cur_f.name != obj.name:
                    bricks_cur_f.layers = self.layers

class OBJECT_OT_move_to_layer(bpy.types.Operator):
    """Move to Layer"""
    bl_idname = "object.move_to_layer"
    bl_label = "Move to Layer"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return bpy.ops.bricker.move_to_layer_override("INVOKE_DEFAULT")
