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
import bmesh
import math
import numpy as np

# Blender imports
from mathutils import Vector, Matrix

# Module imports
from .generator_utils import *


def make_inverted_slope(dimensions:dict, brick_size:list, brick_type:str, direction:str=None, circle_verts:int=None, detail:str="LOW", stud:bool=True, bme:bmesh=None):
    """
    create slope brick with bmesh

    NOTE: brick created with slope facing +X direction, then translated/rotated as necessary

    Keyword Arguments:
        dimensions  -- dictionary containing brick dimensions
        brick_size   -- size of brick (e.g. 2x3 slope -> [2, 3, 3])
        brick_type   -- cm.brick_type
        direction   -- direction slant faces in ("X+", "X-", "Y+", "Y-")
        circle_verts -- number of vertices per circle of cylinders
        detail      -- level of brick detail (options: ("FLAT", "LOW", "HIGH"))
        stud        -- create stud on top of brick
        bme         -- bmesh object in which to create verts

    """
    # create new bmesh object
    bme = bmesh.new() if not bme else bme

    # set direction to longest side if None (defaults to X if sides are the same)
    max_idx = brick_size.index(max(brick_size[:2]))
    directions = ["X+", "Y+", "X-", "Y-"]
    # default to "X+" if X is larger, "Y+" if Y is larger
    direction = direction or directions[max_idx]
    # verify direction is valid
    assert direction in directions

    # get halfScale
    b_and_p_brick = flat_brick_type(brick_type) and brick_size[2] == 3
    height = dimensions["height"] * (3 if b_and_p_brick else 1)
    d = Vector((dimensions["width"] / 2, dimensions["width"] / 2, height / 2))
    # get scalar for d in positive xyz directions
    adjusted_brick_size = (brick_size[:2] if "X" in direction else brick_size[1::-1]) + brick_size[2:]
    scalar = Vector((
        adjusted_brick_size[0] * 2 - 1,
        adjusted_brick_size[1] * 2 - 1,
        1,
    ))
    # get thickness of brick from inside to outside
    thick = Vector([dimensions["thickness"]] * 3)

    # make brick body cube
    coord1 = -d
    coord2 = vec_mult(d, [1, scalar.y, 1])
    v1, v2, v3, v4, v5, v6, v7, v8 = make_cube(coord1, coord2, [0 if stud else 1, 1 if detail == "FLAT" else 0, 0, 0, 1, 1], bme=bme)[1]
    if adjusted_brick_size[0] > 1:
        # remove bottom verts on slope side
        bme.verts.remove(v6)
        bme.verts.remove(v7)
    # add face to opposite side from slope
    bme.faces.new((v1, v5, v8, v2))

    # make square at end of slope
    coord1 = vec_mult(d, [scalar.x, -1, 1])
    coord2 = vec_mult(d, [scalar.x, scalar.y, 1])
    coord1.z -= thick.z
    v9, v10, v11, v12 = make_rectangle(coord1, coord2, bme=bme)[1]

    # connect square to body cube
    bme.faces.new([v8, v11, v10, v3, v2])
    bme.faces.new([v9, v12, v5, v1, v4])
    if max(brick_size[:2]) == 2 or detail in ["FLAT", "LOW"]:
        bme.faces.new((v4, v3, v10, v9))
    else:
        pass
        # TODO: Draw inset half-cylinder

    # add details on top
    if not stud:
        bme.faces.new((v12, v11, v8, v5))
    else:
        if adjusted_brick_size[0] > 1:
            # make upper square over slope
            coord1 = Vector((d.x, -d.y + thick.y / 2, -d.z * (0.5 if max(adjusted_brick_size[:2]) == 2 else 0.625)))
            coord2 = Vector((d.x * scalar.x - thick.x, d.y * scalar.y - thick.y / 2, d.z))
            # v13, v14, v15, v16, v17, v18, v19, v20 = make_cube(coord1, coord2, [0, 0, 1, 0 if sum(adjusted_brick_size[:2]) == 5 else 1, 1, 1], flip_normals=True, bme=bme)[1]
            # TODO: replace the following line with line above to add support details later
            v13, v14, v15, v16, v17, v18, v19, v20 = make_cube(coord1, coord2, [0, 0, 1, 1, 1, 1], flip_normals=True, bme=bme)[1]
            v15.co.z += (d.z * 2 - thick.z) * (0.9 if max(adjusted_brick_size[:2]) == 3 else 0.8)
            v16.co.z = v15.co.z
            # make faces on edges of new square
            bme.faces.new((v18, v17, v5, v12))
            bme.faces.new((v19, v18, v12, v11))
            bme.faces.new((v20, v19, v11, v8))
            add_slope_studs(dimensions, height, adjusted_brick_size, brick_type, circle_verts, bme, edge_xp=[v14, v13], edge_xn=[v16, v15], edge_yp=[v13, v16], edge_yn=[v15, v14])
        else:
            v17, v20 = v6, v7

        add_studs(dimensions, height, [1, adjusted_brick_size[1], adjusted_brick_size[2]], brick_type, circle_verts, bme, edge_xp=[v20, v17], edge_xn=[v8, v5], edge_yp=[v20, v8], edge_yn=[v17, v5])
        pass

    # add details underneath
    if detail != "FLAT":
        # making verts for hollow portion
        coord1 = -d + Vector((thick.x, thick.y, 0))
        coord2 = Vector((d.x + (dimensions["tick_depth"] if detail == "HIGH" else 0), d.y * scalar.y, d.z * scalar.z)) - thick
        sides = [1 if detail == "LOW" else 0, 0, 0 if detail == "HIGH" else 1, 1, 1, 1]
        v21, v22, v23, v24, v25, v26, v27, v28 = make_cube(coord1, coord2, sides, flip_normals=True, bme=bme)[1]
        # make faces on bottom edges of brick
        bme.faces.new((v1,  v21,  v24, v4))
        bme.faces.new((v1,  v2,  v22, v21))
        bme.faces.new((v23, v22, v2,  v3))

        # make tick marks inside
        if detail == "HIGH":
            bottom_verts_d = add_tick_marks(dimensions, [1, min(adjusted_brick_size[:2]), adjusted_brick_size[2]], circle_verts, detail, d, thick, bme, nno=v1, npo=v2, ppo=v3, pno=v4, nni=v21, npi=v22, ppi=v23, pni=v24, nnt=v25, npt=v28, ppt=v27, pnt=v26, inverted_slope=True, side_marks=False)
            bottom_verts = bottom_verts_d["X+"][::-1]
        else:
            bme.faces.new((v23, v3, v4, v24))
            bottom_verts = []

        # add supports
        if detail == "HIGH" and min(adjusted_brick_size[:2]) == 2:
            add_oblong_supports(dimensions, height, circle_verts, "SLOPE_INVERTED", detail, d, scalar, thick, bme) # [v27] + bottom_verts + [v26], [v28, v25], [v27, v28], [v26, v25], bme)

        # add stud cutouts
        if detail == "HIGH":
            add_stud_cutouts(dimensions, [1, min(adjusted_brick_size[:2]), adjusted_brick_size[2]], circle_verts, d, [v27] + bottom_verts + [v26], [v28, v25], [v27, v28], [v26, v25], bme)

        # add half-cylinder insets on slope underside
        if detail == "HIGH" and max(adjusted_brick_size[:2]) == 3:
            # TODO: Rewrite this as dedicated function
            add_slope_studs(dimensions, height, [2, min(adjusted_brick_size[:2]), adjusted_brick_size[2]], brick_type, circle_verts, bme, edge_xp=[v3, v4], edge_xn=[v9, v10], edge_yp=[v4, v9], edge_yn=[v10, v3], underside=True)

    # translate slope to adjust for flipped brick
    for v in bme.verts:
        v.co.y -= d.y * (scalar.y - 1) if direction in ("X-", "Y+") else 0
        v.co.x -= d.x * (scalar.x - 1) if direction in ("X-", "Y-") else 0
    # rotate slope to the appropriate orientation
    mult = directions.index(direction)
    bmesh.ops.rotate(bme, verts=bme.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90) * mult, 3, 'Z'))

    return bme
