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
from ..brick import *


def brick_avail(bricksdict, target_key, brick_mat_name, merge_with_internals, material_type, merge_inconsistent_mats):
    """ check brick is available to merge """
    brick_d = bricksdict.get(target_key)
    # ensure brick exists and should be drawn
    if brick_d is None or not brick_d["draw"]:
        return False, brick_mat_name
    # ensure brick hasn't already been merged and is available for merging
    if brick_d["attempted_merge"] or not brick_d["available_for_merge"]:
        return False, brick_mat_name
    # ensure brick materials can be merged (same material or one of the mats is "" (internal)
    mats_mergable = mats_are_mergable(brick_d["mat_name"], brick_mat_name, merge_with_internals, merge_inconsistent_mats)
    if not mats_mergable:
        return False, brick_mat_name
    # set brick material name if it wasn't already set
    elif brick_mat_name == "":
        brick_mat_name = brick_d["mat_name"]
    # ensure brick type is mergable
    if not mergable_brick_type(brick_d["type"], up=False):
        return False, brick_mat_name
    # passed all the checks; brick is available!
    return True, brick_mat_name


def mats_are_mergable(mat_name1, mat_name2, merge_with_internals, merge_inconsistent_mats=False):
    return mat_name1 == mat_name2 or (merge_with_internals and "" in (mat_name1, mat_name2)) or merge_inconsistent_mats


# def get_num_aligned_edges(bricksdict, size, key, loc, bricks_and_plates=False):
#     num_aligned_edges = 0
#     locs = get_locs_in_brick(size, 1, loc)
#     got_one = False
#
#     for l in locs:
#         # # factor in height of brick (encourages)
#         # if bricks_and_plates:
#         #     k0 = list_to_str(l)
#         #     try:
#         #         p_brick0 = bricksdict[k0]["parent"]
#         #     except KeyError:
#         #         continue
#         #     if p_brick0 == "self":
#         #         p_brick0 = k
#         #     if p_brick0 is None:
#         #         continue
#         #     p_brick_sz0 = bricksdict[p_brick0]["size"]
#         #     num_aligned_edges -= p_brick_sz0[2] / 3
#         # check number of aligned edges
#         l[2] -= 1
#         k = list_to_str(l)
#         try:
#             p_brick_key = bricksdict[k]["parent"]
#         except KeyError:
#             continue
#         if p_brick_key == "self":
#             p_brick_key = k
#         if p_brick_key is None:
#             continue
#         got_one = True
#         p_brick_sz = bricksdict[p_brick_key]["size"]
#         p_brick_loc = get_dict_loc(bricksdict, p_brick_key)
#         # -X side
#         if l[0] == loc[0] and p_brick_loc[0] == l[0]:
#             num_aligned_edges += 1
#         # -Y side
#         if l[1] == loc[1] and p_brick_loc[1] == l[1]:
#             num_aligned_edges += 1
#         # +X side
#         if l[0] == loc[0] + size[0] - 1 and p_brick_loc[0] + p_brick_sz[0] - 1 == l[0]:
#             num_aligned_edges += 1
#         # +Y side
#         if l[1] == loc[1] + size[1] - 1 and p_brick_loc[1] + p_brick_sz[1] - 1 == l[1]:
#             num_aligned_edges += 1
#
#     if not got_one:
#         num_aligned_edges = size[0] * size[1] * 4
#
#     return num_aligned_edges
