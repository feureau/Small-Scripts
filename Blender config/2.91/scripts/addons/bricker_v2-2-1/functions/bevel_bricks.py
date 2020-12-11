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
from bpy.types import Object
props = bpy.props

# Module imports
from .common import *
from .general import *


def remove_bevel_mods(objs):
    """ removes bevel modifier 'obj.name + "_bvl"' for objects in 'objs' """
    objs = confirm_iter(objs)
    for obj in objs:
        bvlMod = obj.modifiers.get(obj.name + "_bvl")
        if bvlMod is None:
            continue
        obj.modifiers.remove(bvlMod)


def create_bevel_mods(cm, objs):
    """ runs 'create_bevel_mod' on objects in 'objs' """
    # get objs to bevel
    objs = confirm_iter(objs)
    # initialize vars
    segments = cm.bevel_segments
    profile = cm.bevel_profile
    show_render = cm.bevel_show_render
    show_viewport = cm.bevel_show_viewport
    show_in_editmode = cm.bevel_show_edit_mode
    # create bevel modifiers for each object
    brick_objs = [obj for obj in objs if obj.type == "MESH"]
    for obj in brick_objs:
        create_bevel_mod(obj=obj, width=cm.bevel_width * cm.brick_height, segments=segments, profile=profile, limit_method="WEIGHT", offset_type="OFFSET", angle_limit=1.55334, show_render=show_render, show_viewport=show_viewport, show_in_editmode=show_in_editmode)


def create_bevel_mod(obj:Object, width:float=1, segments:int=1, profile:float=0.5, affect:str="EDGES", limit_method:str="NONE", angle_limit:float=0.523599, vertex_group:str=None, offset_type:str="OFFSET", show_render:bool=True, show_viewport:bool=True, show_in_editmode:bool=True):
    """ create bevel modifier for 'obj' with given parameters """
    b_mod = obj.modifiers.get(obj.name + "_bvl")
    if not b_mod:
        b_mod = obj.modifiers.new(obj.name + "_bvl", "BEVEL")
    # only update values if necessary (prevents multiple updates to mesh)
    if bpy.app.version[:2] < (2, 90):
        use_only_vertices = affect == "VERTICES"
        if b_mod.use_only_vertices != use_only_vertices:
            b_mod.use_only_vertices = use_only_vertices
    elif b_mod.affect != affect:
        b_mod.affect = affect
    if b_mod.width != width:
        b_mod.width = width
    if b_mod.segments != segments:
        b_mod.segments = segments
    if b_mod.profile != profile:
        b_mod.profile = profile
    if b_mod.limit_method != limit_method:
        b_mod.limit_method = limit_method
    if vertex_group and b_mod.vertex_group != vertex_group:
        try:
            b_mod.vertex_group = vertex_group
        except Exception as e:
            print("[Bricker]", e)
            b_mod.limit_method = "ANGLE"
    if b_mod.angle_limit != angle_limit:
        b_mod.angle_limit = angle_limit
    if b_mod.offset_type != offset_type:
        b_mod.offset_type = offset_type
    # update visibility of bevel modifier
    if b_mod.show_render != show_render:
        b_mod.show_render = show_render
    if b_mod.show_viewport != show_viewport:
        b_mod.show_viewport = show_viewport
    if b_mod.show_in_editmode != show_in_editmode:
        b_mod.show_in_editmode = show_in_editmode
