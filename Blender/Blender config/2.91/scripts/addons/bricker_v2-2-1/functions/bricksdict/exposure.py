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
import math
import colorsys

# Blender imports
import bpy

# Module imports
from ..common import *
from ..general import *
from ..brick import *


def verify_all_brick_exposures(scn, zstep, orig_loc, bricksdict, decriment=0, z_neg=False, z_pos=False):
    """ verify brick exposures for all bricks above/below added/removed brick """
    dlocs = []
    if not z_neg:
        dlocs.append((orig_loc[0], orig_loc[1], orig_loc[2] + decriment))
    if not z_pos:
        dlocs.append((orig_loc[0], orig_loc[1], orig_loc[2] - 1))
    # double check exposure of bricks above/below new adjacent brick
    for dloc in dlocs:
        k = list_to_str(dloc)
        try:
            brick_d = bricksdict[k]
        except KeyError:
            continue
        parent_key = k if brick_d["parent"] == "self" else brick_d["parent"]
        if parent_key is not None:
            set_brick_exposure(bricksdict, zstep, parent_key)
    return bricksdict


def is_brick_exposed(bricksdict, zstep, key=None, loc=None, internal_obscures=True):
    assert key is not None or loc is not None
    # initialize vars
    key = key or list_to_str(loc)
    loc = loc or get_dict_loc(bricksdict, key)
    keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[key]["size"], zstep, loc=loc)
    top_exposed, bot_exposed = False, False
    # set brick exposures
    # TODO: this currently checks all keys at z level of 2 for bricks of z size 3, which is unnecessary because the top and bottom is obscured by itself in that case
    for k in keys_in_brick:
        cur_top_exposed, cur_bot_exposed = check_brickd_exposure(bricksdict, k, internal_obscures=internal_obscures)
        if cur_top_exposed: top_exposed = True
        if cur_bot_exposed: bot_exposed = True
    return top_exposed, bot_exposed


def set_brick_exposure(bricksdict, zstep, key=None, loc=None):
    top_exposed, bot_exposed = is_brick_exposed(bricksdict, zstep, key, loc)
    bricksdict[key]["top_exposed"] = top_exposed
    bricksdict[key]["bot_exposed"] = bot_exposed
    return top_exposed, bot_exposed


def check_brickd_exposure(bricksdict, key=None, loc=None, internal_obscures=True, z_above_dist=1):
    """ check top and bottom exposure of single bricksdict loc/key """
    assert key is not None or loc is not None
    # initialize parameters unspecified
    loc = loc or get_dict_loc(bricksdict, key)
    key = key or list_to_str(loc)
    # initialize brick_d
    try:
        brick_d = bricksdict[key]
    except KeyError:
        return None, None
    # not exposed if brick is internal
    if brick_d["val"] < 1 and internal_obscures:
        return False, False
    # get keys above and below
    x, y, z = loc
    key_above = list_to_str((x, y, z + z_above_dist))
    key_below = list_to_str((x, y, z - 1))
    # check if brickd top or bottom is exposed
    top_exposed = not brick_obscures(bricksdict, key_above, direction="BELOW", internal_obscures=internal_obscures)
    bot_exposed = not brick_obscures(bricksdict, key_below, direction="ABOVE", internal_obscures=internal_obscures)
    return top_exposed, bot_exposed


def brick_obscures(bricksdict, key, direction="ABOVE", internal_obscures=True):
    """ checks if brick obscures the bricks either above or below it """
    try:
        val = bricksdict[key]["val"]
    except KeyError:
        return False
    parent_key = get_parent_key(bricksdict, key)
    typ = bricksdict[parent_key]["type"]
    brick_drawn = internal_obscures or bricksdict[parent_key]["draw"]
    return val != 0 and typ in get_obscuring_types(direction) and brick_drawn
