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
import bpy

# Blender imports
# NONE!

# Module imports
from ..common import *


# NOTE: weights based on BrickLink entries: https://www.bricklink.com/v2/main.page

legal_bricks = {
    1: {
        "STANDARD": [  # Plates
            {"s":[1, 1], "pt":"3024", "wt":0.2},
            {"s":[1, 2], "pt":"3023", "wt":0.36},
            {"s":[1, 3], "pt":"3623", "wt":0.53},
            {"s":[1, 4], "pt":"3710", "wt":0.71},
            {"s":[1, 6], "pt":"3666", "wt":1.06},
            {"s":[1, 8], "pt":"3460", "wt":1.36},
            {"s":[1, 10], "pt":"4477", "wt":1.61},
            {"s":[1, 12], "pt":"60479", "wt":1.95},
            {"s":[2, 2], "pt":"3022", "wt":0.64},
            {"s":[2, 3], "pt":"3021", "wt":0.93},
            {"s":[2, 4], "pt":"3020", "wt":1.2},
            {"s":[2, 6], "pt":"3795", "wt":1.74},
            {"s":[2, 8], "pt":"3034", "wt":2.27},
            {"s":[2, 10], "pt":"3832", "wt":2.91},
            {"s":[2, 12], "pt":"2445", "wt":3.5},
            {"s":[2, 14], "pt":"91988", "wt":3.89},
            {"s":[2, 16], "pt":"4282", "wt":4.5},
            {"s":[3, 3], "pt":"11212", "wt":1.25},  # expensive ($0.10)
            {"s":[4, 4], "pt":"3031", "wt":2.22},
            {"s":[4, 6], "pt":"3032", "wt":3.3},
            {"s":[4, 8], "pt":"3035", "wt":4.7},
            {"s":[4, 10], "pt":"3030", "wt":5.55},
            {"s":[4, 12], "pt":"3029", "wt":6.76},  # too expensive ($0.09)
            {"s":[6, 6], "pt":"3958", "wt":4.71},
            {"s":[6, 8], "pt":"3036", "wt":6.4},
            {"s":[6, 10], "pt":"3033", "wt":7.95},
            {"s":[6, 12], "pt":"3028", "wt":9.47},
            {"s":[6, 14], "pt":"3456", "wt":11},
            {"s":[6, 16], "pt":"3027", "wt":13.27},  # too expensive ($0.32)
            {"s":[6, 24], "pt":"3026", "wt":19.43},  # too expensive ($2.28)
            {"s":[8, 8], "pt":"41539", "wt":9.4},
            {"s":[8, 11], "pt":"728", "wt":12.5},  # super rare
            {"s":[8, 16], "pt":"92438", "wt":17},  # too expensive ($0.30)
            {"s":[16, 16], "pt":"91405", "wt":35},  # too expensive ($0.95)
        ],
        "TILE": [
            {"s":[1, 1], "pt":"3070b", "wt":0.16},
            {"s":[1, 2], "pt":"3069b", "wt":0.26},
            {"s":[1, 3], "pt":"63864", "wt":0.39},
            {"s":[1, 4], "pt":"2431", "wt":0.54},
            {"s":[1, 6], "pt":"6636", "wt":0.83},
            {"s":[1, 8], "pt":"4162", "wt":1.06},
            {"s":[2, 2], "pt":"3068b", "wt":0.48},
            {"s":[2, 4], "pt":"87079", "wt":0.9},
            # {"s":[3, 6], "pt":"6934", "wt":1.73},  # too expensive ($11.24)
            # {"s":[6, 6], "pt":"10202", "wt":3.3},  # too expensive ($0.71)
            # {"s":[8, 16], "pt":"48288", "wt":14},  # too expensive ($0.66)
        ],
        "STUD": [
            {"s":[1, 1], "pt":"4073", "wt":0.12},
        ],
        "STUD_HOLLOW": [
            {"s":[1, 1], "pt":"85861", "wt":0.1},
        ],
        "STUD_TILE": [
            {"s":[1, 1], "pt":"98138", "wt":0.11},
        ],
        # "WING":[[2, 3],
        #         [2, 4],
        #         [3, 6],
        #         [3, 8],
        #         [3, 12],
        #         [4, 4],
        #         [6, 12],
        #         [7, 12]],
        # "ROUNDED_TILE":[[1, 1]],
        # "SHORT_SLOPE":[[1, 1],
        #             [1, 2]],
        "TILE_GRILL": [
            {"s":[1, 2], "pt":"2412b", "wt":0.24},
        ],
        # "TILE_ROUNDED":[[2, 2]],
        # "PLATE_ROUNDED":[[2, 2]],
    },
    3: {
        "STANDARD": [  # Bricks
            {"s":[1, 1], "pt":"3005", "wt":0.44},
            {"s":[1, 2], "pt":"3004", "wt":0.8},
            {"s":[1, 3], "pt":"3622", "wt":1.24},
            {"s":[1, 4], "pt":"3010", "wt":1.64},
            {"s":[1, 6], "pt":"3009", "wt":2.42},
            {"s":[1, 8], "pt":"3008", "wt":3.21},
            {"s":[1, 10], "pt":"6111", "wt":3.8},  # expensive ($0.10)
            {"s":[1, 12], "pt":"6112", "wt":4.8},
            {"s":[1, 16], "pt":"2465", "wt":6.2},  # too expensive ($0.19)
            {"s":[2, 2], "pt":"3003", "wt":1.35},
            {"s":[2, 3], "pt":"3002", "wt":1.92},
            {"s":[2, 4], "pt":"3001", "wt":2.32},
            {"s":[2, 6], "pt":"2456", "wt":3.74},
            {"s":[2, 8], "pt":"3007", "wt":4.75},
            {"s":[2, 10], "pt":"3006", "wt":5.75},
            {"s":[4, 6], "pt":"2356", "wt":6.3},  # too expensive ($0.38)
            {"s":[4, 10], "pt":"6212", "wt":9.5},  # too expensive ($0.20)
            {"s":[4, 12], "pt":"4202", "wt":11.5},
            {"s":[4, 18], "pt":"30400", "wt":17.7},  # too expensive ($6.95)
            {"s":[8, 8], "pt":"4201", "wt":16.3},  # too expensive ($0.39)
            {"s":[8, 16], "pt":"4204", "wt":30.66},  # expensive ($1.73)
            {"s":[12, 24], "pt":"30072", "wt":61},  # too expensive ($3.89)
        ],
        "SLOPE": [
            {"s":[1, 1], "pt":"54200", "wt":0.21},
            {"s":[1, 2], "pt":"3040b", "wt":0.69},
            {"s":[1, 3], "pt":"4286", "wt":0.98},
            {"s":[1, 4], "pt":"60477", "wt":1.1},
            {"s":[2, 2], "pt":"3039", "wt":1.15},
            {"s":[2, 3], "pt":"3298", "pt2":"3038", "wt":1.27},  # wt2: 1.72
            {"s":[2, 4], "pt":"30363", "pt2":"3037", "wt":1.71},  # wt2: 1.97
            {"s":[2, 6], "pt":"23949", "wt":2.9},
            {"s":[2, 8], "pt":"4445", "wt":4.04},
            {"s":[3, 3], "pt":"4161", "wt":1.94},
            {"s":[4, 3], "pt":"3297", "wt":2.57},
        ], # TODO: Add 6x3 option with studs missing between outer two (needs to be coded into slope.py generator)
        "SLOPE_INVERTED": [
            {"s":[1, 2], "pt":"3665", "wt":0.66},
            {"s":[1, 3], "pt":"4287", "wt":0.94},
            {"s":[2, 2], "pt":"3660p01", "wt":1.25},
            {"s":[2, 3], "pt":"3747a", "wt":1.65},
        ],
        "CYLINDER": [
            {"s":[1, 1], "pt":"3062b", "wt":0.28},
        ],
        "CONE": [
            {"s":[1, 1], "pt":"4589", "wt":0.25},
        ],
        "CUSTOM 1": [
            {"s":[1, 1], "pt":"3005", "wt":0.44},
        ],
        "CUSTOM 2": [
            {"s":[1, 1], "pt":"3005", "wt":0.44},
        ],
        "CUSTOM 3": [
            {"s":[1, 1], "pt":"3005", "wt":0.44},
        ],
        # "BRICK_STUD_ON_ONE_SIDE": [
        #     [1, 1],
        # ],
        # "BRICK_INSET_STUD_ON_ONE_SIDE": [
        #     [1, 1],
        # ],
        # "BRICK_STUD_ON_TWO_SIDES": [
        #     [1, 1],
        # ],
        # "BRICK_STUD_ON_ALL_SIDES": [
        #     [1, 1],
        # ],
        # "TILE_WITH_HANDLE": [
        #     [1, 2],
        # ],
        # "BRICK_PATTERN": [
        #     [1, 2],
        # ],
        # "DOME": [
        #     [2, 2],
        # ],
        # "DOME_INVERTED": [
        #     [2, 2],
        # ],
    },
    # 9: {
    #     "TALL_SLOPE": [
    #         [1, 2],
    #         [2, 2],
    #     ],
    #     "TALL_SLOPE_INVERTED": [
    #         [1, 2],
    #     ],
    #     "TALL_BRICK": [
    #         [2, 2],
    #     ],
    # },
    # 15: {
    #     "TALL_BRICK": [
    #         [1, 2],
    #     ],
    # },
}

def get_legal_brick_sizes():
    """ returns a list of legal brick sizes """
    legal_brick_sizes = {}
    # add reverses of brick sizes
    for height_key, types in legal_bricks.items():
        legal_brick_sizes[height_key] = {}
        for typ, parts in types.items():
            reverse_sizes = [part["s"][::-1] for part in parts]
            legal_brick_sizes[height_key][typ] = uniquify2(reverse_sizes + [part["s"] for part in parts])
    return legal_brick_sizes


def get_legal_bricks():
    """ returns a list of legal brick sizes and part numbers """
    return legal_bricks


def get_obscuring_types(direction="BELOW"):
    if direction == "BELOW":
        return ["STANDARD", "TILE", "STUD", "SLOPE"]
    elif direction == "ABOVE":
        return ["STANDARD", "TILE", "STUD", "SLOPE_INVERTED"]


def is_legal_brick_size(size, type, mat_name="", internal_mat_name=""):
    assert isinstance(size, list)
    # access blender property for performance improvement over running 'get_legal_brick_sizes' every time
    if size[:2] not in bpy.props.bricker_legal_brick_sizes[size[2]][type]:
        return False
    return True


def get_part(legal_bricks, size, typ):
    parts = legal_bricks[size[2]][typ]
    for j,part in enumerate(parts):
        if parts[j]["s"] in (size[:2], size[1::-1]):
            part = parts[j]
            break
    return part


def get_brick_type_and_size_from_part_num(legal_bricks, pt_num):
    for ht in legal_bricks.keys():
        for typ in legal_bricks[ht].keys():
            for part_info in legal_bricks[ht][typ]:
                if part_info["pt"] == pt_num:
                    return typ, part_info["s"] + [ht]
    return None, None
