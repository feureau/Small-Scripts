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
from .general import *
from .brick.bricks import *
from .brick.legal_brick_sizes import *


def set_model_info(bricksdict, cm=None):
    if bricksdict is None:
        return
    scn, cm = get_active_context_info(cm=cm)[:2]
    internal_mat_name = cm.internal_mat.name if cm.internal_mat else ""
    legal_bricks = get_legal_bricks()
    num_bricks_in_model = 0
    model_weight = 0
    mats_in_model = list()
    max_vals = (0, 0, 0)
    bad_bricks = 0
    z_max = 0
    for k, brick_d in bricksdict.items():
        if not brick_d["draw"]:
            continue
        if brick_d["parent"] == "self":
            dict_loc = get_dict_loc(bricksdict, k)
            max_vals = (max(max_vals[0], dict_loc[0] + brick_d["size"][0] - 1), max(max_vals[1], dict_loc[1] + brick_d["size"][1] - 1), max(max_vals[2], dict_loc[2] + brick_d["size"][2] - 1))
            num_bricks_in_model += 1
            if brick_d["mat_name"] not in mats_in_model:
                mats_in_model.append(brick_d["mat_name"])
            part = get_part(legal_bricks, brick_d["size"], brick_d["type"])
            model_weight += part["wt"]
            cur_mat_name = brick_d["mat_name"] or internal_mat_name
    if "" in mats_in_model:
        mats_in_model.remove("")
    # print("Bad Bricks:", bad_bricks)

    dimensions = get_brick_dimensions(0.0096, cm.zstep, cm.gap)
    model_dims = (
        max_vals[0] * dimensions["width"],
        max_vals[1] * dimensions["width"],
        max_vals[2] * dimensions["height"],
    )

    cm.num_bricks_in_model = num_bricks_in_model
    cm.num_materials_in_model = len(mats_in_model)
    cm.real_world_dimensions = model_dims
    cm.model_weight = model_weight
