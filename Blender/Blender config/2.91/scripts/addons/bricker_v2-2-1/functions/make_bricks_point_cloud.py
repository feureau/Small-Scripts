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
import bmesh
import math
import time
import sys
import random
import json
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Module imports
from .make_bricks_utils import *
from .brick import *
from .common import *
from .general import *


def make_bricks_point_cloud(cm, bricksdict, keys_dict, parent, source_details, dimensions, bcoll, frame_num=None):
    # generate point cloud
    n = cm.source_obj.name
    instancer_name = "Bricker_%(n)s_instancer_f_%(frame_num)s" % locals() if frame_num is not None else "Bricker_%(n)s_instancer" % locals()
    bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent" % locals())
    point_cloud = bpy.data.meshes.new(instancer_name)
    point_cloud_obj = bpy.data.objects.new(instancer_name, point_cloud)
    # add point cloud to collection
    bcoll.objects.link(point_cloud_obj)
    # set point cloud location
    try:
        link_object(parent)
    except RuntimeError:
        pass
    depsgraph_update()
    point_cloud_obj.location = source_details.mid - parent.matrix_world.to_translation()
    # initialize vars
    rand_s2 = np.random.RandomState(cm.merge_seed + 1)
    random_rot = cm.random_rot
    random_loc = cm.random_loc
    use_local_orient = cm.use_local_orient
    source_obj = cm.source_obj
    zstep = cm.zstep
    i = 0
    # create points in cloud
    point_cloud.vertices.add(len(bricksdict))
    # set coordinates and normals for points in cloud
    for z in sorted(keys_dict.keys()):
        for key in keys_dict[z]:
            brick_d = bricksdict[key]
            brick_d["size"] = [1, 1, 1]
            # apply random rotation to edit mesh according to parameters
            random_rot_angle = get_random_rot_angle(random_rot * 2, rand_s2, brick_d["size"])
            # get brick location
            loc_offset = get_random_loc(random_loc, rand_s2, dimensions["half_width"], dimensions["half_height"])
            brick_loc = get_brick_center(bricksdict, key, zstep, str_to_list(key)) + loc_offset
            # set vert
            v = point_cloud.vertices[i]
            v.co = brick_loc
            if random_rot_angle:
                v.normal.x = 1
                v.normal.y = random_rot_angle[0]
                v.normal.z = random_rot_angle[1]
            i += 1
    bricks_created = point_cloud_obj
    # set up point cloud as instancer
    point_cloud_obj.instance_type = "VERTS"
    point_cloud_obj.show_instancer_for_viewport = True
    point_cloud_obj.show_instancer_for_render = False
    point_cloud_obj.use_instance_vertices_rotation = True
    # create instance obj
    brick = generate_brick_object(bcoll.name)
    if cm.material_type == "CUSTOM":
        set_material(brick, cm.custom_mat)
    bcoll.objects.link(brick)
    brick.parent = point_cloud_obj
    point_cloud_obj.parent = parent
    return [point_cloud_obj]
