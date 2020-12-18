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

# Module imports
from .caches import bricker_bfm_cache
from ..functions.common.blender import get_preferences

python_undo_state = {}


class UndoStack():
    bl_category = "Bricker"
    bl_idname = "bricker.undo_stack"
    bl_label = "Undo Stack"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"

    @staticmethod
    def get_instance(reset=False):
        if UndoStack.instance is None or reset:
            UndoStack.new()
        return UndoStack.instance

    @staticmethod
    def new():
        UndoStack.creating = True
        UndoStack.instance = UndoStack()
        del UndoStack.creating
        return UndoStack.instance

    ################################################
    # initialization method

    def __init__(self):
        assert hasattr(UndoStack, "creating"), "Do not create new UndoStack directly!  Use UndoStack.new()"
        self.undo_depth = get_preferences().edit.undo_steps
        self.undo = []  # undo stack of causing actions, FSM state, tool states, and rftargets
        self.redo = []  # redo stack of causing actions, FSM state, tool states, and rftargets

    ###################################################
    # class variables

    instance = None

    ###################################################
    # undo / redo stack operations

    @staticmethod
    def iterate_states(cm):
        """ iterate undo states """
        scn = bpy.context.scene
        global python_undo_state
        bpy.props.bricker_updating_undo_state = True
        if cm.id not in python_undo_state:
            python_undo_state[cm.id] = 0
        python_undo_state[cm.id] += 1
        cm.blender_undo_state += 1
        bpy.props.bricker_updating_undo_state = False

    def match_python_to_blender_state(self):
        scn = bpy.context.scene
        for cm in scn.cmlist:
            python_undo_state[cm.id] = cm.blender_undo_state

    def get_length(self): return len(self.undo)

    def isUpdating(self): return bpy.props.bricker_updating_undo_state

    def _create_state(self, action, bfm_cache):
        return {
            "action":    action,
            "bfm_cache": bfm_cache,
        }

    def _restore_state(self, state, cm_id=None):
        global bricker_bfm_cache
        keys = [cm_id] if cm_id is not None else state["bfm_cache"].keys()
        for key in keys:
            bricker_bfm_cache[key] = marshal.loads(state["bfm_cache"][key])
        return bricker_bfm_cache

    def append_state(self, action, stackType, affected_ids="ALL"):
        global bricker_bfm_cache
        stack = getattr(self, stackType)
        bfm_cached = stack[-1]["bfm_cache"] if len(stack) > 0 else {}
        # perform append state in active Blender session
        new_bfm_cache = {}
        for cm_id in bricker_bfm_cache:
            if affected_ids != "ALL" and cm_id not in affected_ids and cm_id in bfm_cached:
                new_bfm_cache[cm_id] = bfm_cached[cm_id]
            else:
                new_bfm_cache[cm_id] = marshal.dumps(bricker_bfm_cache[cm_id])
        stack.append(self._create_state(action, new_bfm_cache))
        return new_bfm_cache

    def revert_to_last_state(self, cm_id):
        bricker_bfm_cache = self._restore_state(self.undo[-1])
        return bricker_bfm_cache[cm_id]

    def undo_push(self, action, affected_ids="ALL", repeatable=False):
        # skip pushing to undo if action is repeatable and we are repeating actions
        if repeatable and self.undo and self.undo[-1]["action"] == action:
            return
        # skip pushing to undo if bricker not initialized
        if not bpy.props.bricker_initialized:
            return
        new_bfm_cache = self.append_state(action, "undo", affected_ids=affected_ids)
        while len(self.undo) > self.undo_depth:
            self.undo.pop(0)  # limit stack size
        self.redo.clear()
        self.instrument_write(action)
        return new_bfm_cache

    def undo_pop(self):
        if not self.undo:
            return
        self.append_state("undo", "redo")
        self._restore_state(self.undo.pop())
        self.instrument_write("undo")
        # iterate undo states
        global python_undo_state
        scn = bpy.context.scene
        cm = scn.cmlist[scn.cmlist_index]
        python_undo_state[cm.id] -= 1

    def undo_pop_clean(self):
        if not self.undo:
            return
        self.undo.pop()

    def undo_cancel(self):
        self._restore_state(self.undo.pop())
        self.instrument_write("cancel (undo)")

    def redo_pop(self):
        if not self.redo:
            return
        self.append_state("redo", "undo")
        self._restore_state(self.redo.pop())
        self.instrument_write("redo")
        # iterate undo states
        global python_undo_state
        scn = bpy.context.scene
        cm = scn.cmlist[scn.cmlist_index]
        python_undo_state[cm.id] += 1

    def instrument_write(self, action):
        if True:
            return # disabled for now...
        tb_name = "Bricker_instrumentation"
        if tb_name not in bpy.data.texts:
            bpy.data.texts.new(tb_name)
        tb = bpy.data.texts[tb_name]

        target_json = self.rftarget.to_json()
        data = {"action": action, "target": target_json}
        data_str = json.dumps(data, separators=[",", ":"])

        # write data to end of textblock
        tb.write("")        # position cursor to end
        tb.write(data_str)
        tb.write("\n")
