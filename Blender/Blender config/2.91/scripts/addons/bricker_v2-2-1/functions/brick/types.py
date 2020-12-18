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
import collections
import json
import math
import numpy as np
import bmesh

# Blender imports
import bpy
import addon_utils
from mathutils import Vector, Euler, Matrix
from bpy.types import Object

# Module imports
from ..common import *


def get_brick_types(height):
    return bpy.props.bricker_legal_brick_sizes[height].keys()


def get_zstep(cm):
    return 1 if flat_brick_type(cm.brick_type) else 3


def flat_brick_type(typ:str):
    if typ is None:
        return False
    return "PLATE" in typ or "STUD" in typ or "TILE" in typ


def mergable_brick_type(typ:str, up:bool=False):
    if typ is None:
        return False
    return "STANDARD" in typ or "PLATE" in typ or "BRICK" in typ or "SLOPE" in typ or (up and typ == "CYLINDER")


def get_tall_type(brick_d, target_type=None):
    tall_types = get_brick_types(height=3)
    return target_type if target_type in tall_types else (brick_d["type"] if brick_d["type"] in tall_types else "STANDARD")


def get_short_type(brick_d, target_type=None):
    short_types = get_brick_types(height=1)
    return target_type if target_type in short_types else (brick_d["type"] if brick_d["type"] in short_types else "STANDARD")


def get_brick_type(model_brick_type):
    return "STANDARD" if model_brick_type in ("BRICKS", "PLATES", "BRICKS_AND_PLATES") else (model_brick_type[:-1] if model_brick_type.endswith("S") else ("CUSTOM 1" if model_brick_type == "CUSTOM" else model_brick_type))


def get_round_brick_types():
    return ("CYLINDER", "CONE", "STUD", "STUD_HOLLOW", "STUD_TILE")
