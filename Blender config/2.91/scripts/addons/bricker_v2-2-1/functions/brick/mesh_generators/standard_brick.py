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

# Blender imports
from mathutils import Vector, Matrix
from bpy.types import Object

# Module imports
from .generator_utils import *


def make_standard_brick(dimensions:dict, brick_size:list, type:str, brick_type:str, circle_verts:int=16, detail:str="LOW", logo:Object=None, stud:bool=True, bme:bmesh=None):
    """
    create brick with bmesh

    Keyword Arguments:
        dimensions  -- dictionary containing brick dimensions
        brick_size   -- size of brick (e.g. standard 2x4 -> [2, 4, 3])
        type        -- type of brick (e.g. BRICK, PLATE, CUSTOM)
        brick_type   -- cm.brick_type
        circle_verts -- number of vertices per circle of cylinders
        detail      -- level of brick detail (options: ["FLAT", "LOW", "HIGH"])
        logo        -- logo object to create on top of studs
        stud        -- create stud on top of brick
        bme         -- bmesh object in which to create verts

    """
    assert detail in ("FLAT", "LOW", "HIGH")
    # create new bmesh object
    bme = bmesh.new() if not bme else bme
    b_and_p_brick = flat_brick_type(brick_type) and brick_size[2] == 3
    height = dimensions["height"] * (3 if b_and_p_brick else 1)

    # get half scale
    d = Vector((dimensions["half_width"], dimensions["half_width"], dimensions["half_height"]))
    d.z = d.z * (brick_size[2] if flat_brick_type(brick_type) else 1)
    # get scalar for d in positive xyz directions
    scalar = Vector((
        brick_size[0] * 2 - 1,
        brick_size[1] * 2 - 1,
        1,
    ))
    # get thickness of brick from inside to outside
    thick_xy = dimensions["thickness"] - (dimensions["tick_depth"] if "High" in detail and min(brick_size) != 1 else 0)
    thick = Vector((thick_xy, thick_xy, dimensions["thickness"]))

    # create cube
    coord1 = -d
    coord2 = vec_mult(d, scalar)
    v1, v2, v3, v4, v5, v6, v7, v8 = make_cube(coord1, coord2, [0 if stud else 1, 1 if detail == "FLAT" else 0, 1, 1, 1, 1], seams=True, bme=bme)[1]

    # add studs
    if stud: add_studs(dimensions, height, brick_size, brick_type, circle_verts, bme, edge_xp=[v7, v6], edge_xn=[v8, v5], edge_yp=[v7, v8], edge_yn=[v6, v5], hollow=brick_size[2] > 3 or "HOLES" in type)

    # add details
    if detail != "FLAT":
        draw_tick_marks = detail == "HIGH" and ((brick_size[0] == 2 and brick_size[1] > 1) or (brick_size[1] == 2 and brick_size[0] > 1)) and brick_size[2] != 1
        # making verts for hollow portion
        coord1 = -d + Vector((thick.x, thick.y, 0))
        coord2 = vec_mult(d, scalar) - thick
        sides = [1 if detail == "LOW" else 0, 0] + ([0 if draw_tick_marks else 1] * 4)
        v9, v10, v11, v12, v13, v14, v15, v16 = make_cube(coord1, coord2, sides, flip_normals=True, seams=True, bme=bme)[1]
        # make tick marks inside 2 by x bricks
        if draw_tick_marks:
            bottom_verts = add_tick_marks(dimensions, brick_size, circle_verts, detail, d, thick, bme, nno=v1, npo=v2, ppo=v3, pno=v4, nni=v9, npi=v10, ppi=v11, pni=v12, nnt=v13, npt=v16, ppt=v15, pnt=v14)
        else:
            # make faces on bottom edges of brick
            bme.faces.new((v1,  v9,  v12, v4))
            bme.faces.new((v1,  v2,  v10, v9))
            bme.faces.new((v11, v3,  v4,  v12))
            bme.faces.new((v11, v10, v2,  v3))
        # get upper edge verts for connecting to supports/cylinders
        edge_xp = [v15] + (bottom_verts["X+"][::-1] if draw_tick_marks else []) + [v14]
        edge_xn = [v16] + (bottom_verts["X-"][::-1] if draw_tick_marks else []) + [v13]
        edge_yp = [v15] + (bottom_verts["Y+"][::-1] if draw_tick_marks else []) + [v16]
        edge_yn = [v14] + (bottom_verts["Y-"][::-1] if draw_tick_marks else []) + [v13]
        # add supports
        if max(brick_size[:2]) > 1:
            add_supports(dimensions, height, brick_size, brick_type, circle_verts, type, detail, d, scalar, thick, bme, add_beams=detail == "HIGH")
        # add stud cutouts
        if detail == "HIGH":
            add_stud_cutouts(dimensions, brick_size, circle_verts, d, edge_xp, edge_xn, edge_yp, edge_yn, bme)

    # transform final mesh
    gap = Vector([dimensions["gap"]] * 2)
    numer = vec_mult(d.xy * 2 + gap, brick_size[:2]) - gap
    denom = vec_mult(d.xy * 2,       brick_size[:2])
    if brick_size[0] != 1 or brick_size[1] != 1:
        bmesh.ops.scale(bme, verts=bme.verts, vec=(numer.x / denom.x, numer.y / denom.y, 1.0))
        if brick_size[0] > 1:
            for v in bme.verts:
                v.co.x -= (gap.x * brick_size[0] - gap.x) / 2
        if brick_size[1] > 1:
            for v in bme.verts:
                v.co.y -= (gap.y * brick_size[1] - gap.y) / 2

    # return bmesh
    return bme
