# Copyright (C) 2019 Christopher Gearhart
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
from bpy.app.handlers import persistent
from bpy.types import Object, Scene, ViewLayer


def get_anim_adjusted_frame(frame, bricks_coll):
    frame_coll_names = list(bricks_coll.children.keys())
    frame_coll_nums = set(int(n[n.rfind("_") + 1:]) for n in frame_coll_names)
    start_frame = min(frame_coll_nums)
    stop_frame = max(frame_coll_nums)
    step_frame = round((start_frame - stop_frame) / len(frame_coll_nums))
    clamped_frame = min(stop_frame, max(start_frame, frame))
    adjusted_frame = clamped_frame - ((clamped_frame - start_frame) % step_frame)
    return adjusted_frame


def confirm_iter(object):
    """ if single item passed, convert to list """
    try:
        iter(object)
    except TypeError:
        object = [object]
    return object


def hide(objs:list, viewport:bool=True, render:bool=True):
    # confirm objs is an iterable of objects
    objs = confirm_iter(objs)
    # hide objects in list
    for obj in objs:
        if not obj.hide_viewport and viewport:
            obj.hide_viewport = True
        if not obj.hide_render and render:
            obj.hide_render = True


def unhide(objs:list, viewport:bool=True, render:bool=True):
    # confirm objs is an iterable of objects
    objs = confirm_iter(objs)
    # unhide objects in list
    for obj in objs:
        if obj.hide_viewport and viewport:
            obj.hide_viewport = False
        if obj.hide_render and render:
            obj.hide_render = False


def set_active_obj(obj:Object, view_layer:ViewLayer=None):
    view_layer = view_layer or bpy.context.view_layer
    view_layer.objects.active = obj


def deselect_all():
    """ deselects all objs in scene """
    selected_objects = bpy.context.selected_objects if hasattr(bpy.context, "selected_objects") else [obj for obj in bpy.context.view_layer.objects if obj.select_get()]
    deselect(selected_objects)


def select(obj_list, active:bool=False, only:bool=False):
    """ selects objs in list (deselects the rest if 'only') """
    # confirm obj_list is a list of objects
    obj_list = confirm_iter(obj_list)
    # deselect all if selection is exclusive
    if only:
        deselect_all()
    # select objects in list
    for obj in obj_list:
        if obj is not None and not obj.select_get():
            obj.select_set(True)
    # set active object
    if active and len(obj_list) > 0:
        set_active_obj(obj_list[0])


def deselect(obj_list):
    """ deselects objs in list """
    # confirm obj_list is a list of objects
    obj_list = confirm_list(obj_list)
    # select/deselect objects in list
    for obj in obj_list:
        if obj is not None and obj.select_get():
            obj.select_set(False)


@persistent
def handle_animation(scn:Scene, junk=None):
    for coll in bpy.data.collections:
        if not (coll.name.startswith("Bricker_") and coll.name.endswith("_bricks")):
            continue
        for cur_bricks_coll in coll.children:
            try:
                cf = int(cur_bricks_coll.name[cur_bricks_coll.name.rfind("_") + 1:])
            except ValueError:
                continue
            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, coll)
            on_cur_f = adjusted_frame_current == cf
            # set active obj
            active_obj = bpy.context.active_object if hasattr(bpy.context, "active_object") else None
            # hide bricks from view and render unless on current frame
            if cur_bricks_coll.hide_render == on_cur_f:
                cur_bricks_coll.hide_render = not on_cur_f
            if cur_bricks_coll.hide_viewport == on_cur_f:
                cur_bricks_coll.hide_viewport = not on_cur_f


bpy.app.handlers.frame_change_post.append(handle_animation)
