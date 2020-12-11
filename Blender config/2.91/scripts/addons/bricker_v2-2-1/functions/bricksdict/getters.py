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

# Module imports
from ..common import *
from ..general import *


def get_material_name(bricksdict, key, size, zstep, material_type, mat_shell_depth=1, custom_mat=None, random_mat_seed=1000, brick_mats=None):
    mat = None
    if bricksdict[key]["custom_mat_name"] and is_mat_shell_val(bricksdict[key]["val"], mat_shell_depth):
        mat = bpy.data.materials.get(bricksdict[key]["mat_name"])
    elif material_type == "CUSTOM":
        mat = custom_mat
    elif material_type == "SOURCE":
        mat_name = get_most_frequent_mat_name(bricksdict, key, size, zstep, mat_shell_depth)
        # get the material for that mat_name
        mat = bpy.data.materials.get(mat_name)
    elif material_type == "RANDOM" and brick_mats is not None and len(brick_mats) > 0:
        if len(brick_mats) > 1:
            rand_state = np.random.RandomState(0)
            rand_state.seed(random_mat_seed + int(str(hash(key))[-9:]))
            rand_idx = rand_state.randint(0, len(brick_mats))
        else:
            rand_idx = 0
        mat_name = brick_mats[rand_idx]
        mat = bpy.data.materials.get(mat_name)
    mat_name = "" if mat is None else mat.name
    return mat_name


def get_most_frequent_mat_name(bricksdict, key, size, zstep, mat_shell_depth):
    # initialize vars
    highest_val = 0
    mats_L = []
    mat_name = ""
    # get most frequent material in brick size
    keys_in_brick = get_keys_in_brick(bricksdict, size, zstep, key=key)
    for key0 in keys_in_brick:
        cur_brick_d = bricksdict[key0]
        if cur_brick_d["val"] >= highest_val:
            highest_val = cur_brick_d["val"]
            mat_name = cur_brick_d["mat_name"]
            if is_mat_shell_val(cur_brick_d["val"], mat_shell_depth) and mat_name:
                mats_L.append(mat_name)
    # if multiple shell materials, use the most frequent one
    if len(mats_L) > 1:
        mat_name = most_common(mats_L)
    return mat_name


def is_mat_shell_val(val, mat_shell_depth=1):
    return (1 - val) * 100 < mat_shell_depth
