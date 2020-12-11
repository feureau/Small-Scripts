"""
Copyright (C) 2020 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# System imports
# NONE!

# Blender imports
import bpy
from bpy.app.handlers import persistent

# Module imports
from .app_handlers import bricker_running_blocking_op
from .common import *
from .general import *
from ..lib.undo_stack import UndoStack, python_undo_state


# def is_bricker_obj_visible(scn, cm, n):
#     if cm.model_created or cm.animated:
#         gn = "Bricker_%(n)s_bricks" % locals()
#         if collExists(gn) and len(bpy.data.collections[gn].objects) > 0:
#             obj = bpy.data.collections[gn].objects[0]
#         else:
#             obj = None
#     else:
#         obj = cm.source_obj
#     obj_visible = is_obj_visible_in_viewport(obj)
#     return obj_visible, obj


@persistent
def handle_selections(junk=None):
    if bricker_running_blocking_op():
        return 0.5
    scn = bpy.context.scene
    obj = bpy.context.view_layer.objects.active if b280() else scn.objects.active
    # if active object changes, open Brick Model settings for active object
    cm_obj_names = (scn.bricker_active_object_name, "Bricker_" + scn.bricker_active_object_name + "_bricks", "Bricker_" + scn.bricker_active_object_name + "_parent")
    if obj and len(scn.cmlist) > 0 and obj.name not in cm_obj_names and (scn.cmlist_index == -1 or scn.cmlist[scn.cmlist_index].source_obj is not None) and obj.type == "MESH":
        if obj.name.startswith("Bricker_"):
            using_source = False
            end_idx = obj.name.rfind("_bricks")
            if end_idx == -1:
                end_idx = obj.name.rfind("_parent")
                if end_idx == -1:
                    end_idx = obj.name.rfind("_instancer")
                    if end_idx == -1:
                        end_idx = obj.name.rfind("_brick__")  # for backwards compatibility
                        if end_idx == -1:
                            end_idx = obj.name.rfind("__")
            if end_idx != -1:
                scn.bricker_active_object_name = obj.name[len("Bricker_"):end_idx]
        else:
            using_source = True
            scn.bricker_active_object_name = obj.name
        for i, cm0 in enumerate(scn.cmlist):
            # print(get_source_name(cm0), scn.bricker_active_object_name, using_source, cm0.model_created)
            if get_source_name(cm0) != scn.bricker_active_object_name or (using_source and cm0.model_created):
                continue
            try:
                if scn.cmlist_index != i:
                    bpy.props.manual_cmlist_update = True
                    scn.cmlist_index = i
                if obj.is_brick:
                    if scn.bricker_last_active_object_name != obj.name:
                        # adjust scn.active_brick_detail based on active brick
                        x0, y0, z0 = str_to_list(get_dict_key(obj.name))
                        cm0.active_key = (x0, y0, z0)
                        scn.bricker_last_active_object_name = obj.name
            except AttributeError:
                pass
            tag_redraw_areas("VIEW_3D")
            return 0.05
        # if no matching cmlist item found, set cmlist_index to -1
        scn.cmlist_index = -1
        tag_redraw_areas("VIEW_3D")
    return 0.05


@blender_version_wrapper(">=","2.80")
def handle_undo_stack():
    scn = bpy.context.scene
    undo_stack = UndoStack.get_instance()
    if hasattr(bpy.props, "bricker_updating_undo_state") and not undo_stack.isUpdating() and not bricker_running_blocking_op() and scn.cmlist_index != -1:
        global python_undo_state
        cm = scn.cmlist[scn.cmlist_index]
        if cm.id not in python_undo_state:
            python_undo_state[cm.id] = 0
        # handle undo
        elif python_undo_state[cm.id] > cm.blender_undo_state:
            undo_stack.undo_pop()
            tag_redraw_areas("VIEW_3D")
        # handle redo
        elif python_undo_state[cm.id] < cm.blender_undo_state:
            undo_stack.redo_pop()
            tag_redraw_areas("VIEW_3D")
    return 0.02


@persistent
@blender_version_wrapper(">=","2.80")
def register_bricker_timers(scn, jnk=None):
    timer_fns = (handle_selections, handle_undo_stack)
    for timer_fn in timer_fns:
        if not bpy.app.timers.is_registered(timer_fn):
            bpy.app.timers.register(timer_fn)
