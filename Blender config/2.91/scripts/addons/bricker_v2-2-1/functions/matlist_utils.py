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
from .common import *


def get_brick_mats(cm):
    brick_mats = []
    if cm.material_type == "RANDOM":
        mat_obj = get_mat_obj(cm, typ="RANDOM")
        brick_mats = list(mat_obj.data.materials.keys())
    return brick_mats


def create_mat_objs(cm):
    """ create new mat_objs for current cmlist id """
    mat_obj_names = ["Bricker_{}_RANDOM_mats".format(cm.id), "Bricker_{}_ABS_mats".format(cm.id)]
    junk_m = junk_mesh("Bricker_junk_mesh")
    for obj_n in mat_obj_names:
        mat_obj = bpy.data.objects.get(obj_n)
        if mat_obj is None:
            mat_m = bpy.data.meshes.new(obj_n)
            mat_obj = bpy.data.objects.new(obj_n, mat_m)
            mat_obj.use_fake_user = True
    cm.mat_obj_random = bpy.data.objects.get(mat_obj_names[0])
    cm.mat_obj_abs = bpy.data.objects.get(mat_obj_names[1])
    return cm.mat_obj_random, cm.mat_obj_abs


def get_mat_obj(cm, typ=None):
    typ = typ or ("RANDOM" if cm.material_type == "RANDOM" else "ABS")
    if typ == "RANDOM":
        mat_obj = cm.mat_obj_random
    else:
        mat_obj = cm.mat_obj_abs
    return mat_obj


def remove_mat_objs(idx):
    """ remove mat_objs for current cmlist id """
    mat_obj_names = ["Bricker_{}_RANDOM_mats".format(idx), "Bricker_{}_ABS_mats".format(idx)]
    for obj_n in mat_obj_names:
        mat_obj = bpy.data.objects.get(obj_n)
        if mat_obj is not None:
            bpy.data.objects.remove(mat_obj, do_unlink=True)
