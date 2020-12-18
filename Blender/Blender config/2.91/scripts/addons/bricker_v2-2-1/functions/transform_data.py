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
from mathutils import Vector, Euler

# Module imports
from .common import confirm_iter
from .general import *


def store_transform_data(cm, obj, offset_by=None):
    """ store transform data from obj into cm.model_loc/rot/scale """
    if obj:
        loc = obj.location
        if offset_by is not None:
            loc += Vector(offset_by)
        cm.model_loc = list_to_str(loc.to_tuple())
        # cm.model_loc = list_to_str(obj.matrix_world.to_translation().to_tuple())
        last_mode = obj.rotation_mode
        obj.rotation_mode = "XYZ"
        cm.model_rot = list_to_str(tuple(obj.rotation_euler))
        cm.model_scale = list_to_str(obj.scale.to_tuple())
        obj.rotation_mode = last_mode
    elif obj is None:
        cm.model_loc = "0,0,0"
        cm.model_rot = "0,0,0"
        cm.model_scale = "1,1,1"


def get_transform_data(cm):
    """ return transform data from cm.model_loc/rot/scale """
    l = str_to_tuple(cm.model_loc, float)
    r = str_to_tuple(cm.model_rot, float)
    s = str_to_tuple(cm.model_scale, float)
    return l, r, s


def clear_transform_data(cm):
    cm.model_loc = "0,0,0"
    cm.model_rot = "0,0,0"
    cm.model_scale = "1,1,1"


def apply_transform_data(cm, objs):
    """ apply transform data from cm.model_loc/rot/scale to objects in passed iterable """
    objs = confirm_iter(objs)
    # apply matrix to objs
    for obj in objs:
        # LOCATION
        l, r, s = get_transform_data(cm)
        obj.location = obj.location + Vector(l)
        # ROTATION
        last_mode = obj.rotation_mode
        obj.rotation_mode = "XYZ"
        obj.rotation_euler.rotate(Euler(r))
        obj.rotation_mode = last_mode
        # SCALE
        osx, osy, osz = obj.scale
        obj.scale = vec_mult(obj.scale, s)
