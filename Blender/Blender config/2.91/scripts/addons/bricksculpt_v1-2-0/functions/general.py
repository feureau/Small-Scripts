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

# Module imports
from .common import *


def is_bricker_installed():
    return hasattr(bpy.props, "bricker_module_name")


def bricksculpt_handle_exception():
    handle_exception(log_name="BrickSculpt (Bricker Addon) log", report_button_loc="Bricker > Customize Model > Report Error")


def get_nearby_loc_from_vector(loc_diff, cur_loc, dimensions, zstep, brick_size, width_divisor=2.05, height_divisor=2.05):
    d = Vector((dimensions["width"] / width_divisor, dimensions["width"] / width_divisor, dimensions["height"] / height_divisor))
    next_loc = Vector(cur_loc)
    if loc_diff.z > d.z - dimensions["stud_height"]:
        next_loc.z += math.ceil((loc_diff.z - d.z) / (d.z * 2))
    elif loc_diff.z < -d.z:
        next_loc.z -= 1
    if loc_diff.x > d.x:
        next_loc.x += math.ceil((loc_diff.x - d.x) / (d.x * 2))
    elif loc_diff.x < -d.x:
        next_loc.x += math.floor((loc_diff.x + d.x) / (d.x * 2))
    if loc_diff.y > d.y:
        next_loc.y += math.ceil((loc_diff.y - d.y) / (d.y * 2))
    elif loc_diff.y < -d.y:
        next_loc.y += math.floor((loc_diff.y + d.y) / (d.y * 2))
    # if the next_loc is inside the original brick, assume we're trying to target the underside (because bricks may be hollow)
    if loc_is_in_brick(next_loc, cur_loc, brick_size):
        next_loc.z = cur_loc[2] - 1
    return [int(next_loc.x), int(next_loc.y), int(next_loc.z)]


def loc_is_in_brick(loc, brick_loc, brick_size):
    x0, y0, z0 = loc
    return all((
        brick_loc[0] <= loc[0] <= brick_loc[0] + brick_size[0] - 1,
        brick_loc[1] <= loc[1] <= brick_loc[1] + brick_size[1] - 1,
        brick_loc[2] <= loc[2] <= brick_loc[2] + brick_size[2] - 1,
    ))
