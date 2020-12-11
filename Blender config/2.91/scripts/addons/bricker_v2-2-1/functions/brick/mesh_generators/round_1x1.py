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
from mathutils import Vector

# Module imports
from .generator_utils import *


def make_round_1x1(dimensions:dict, brick_type:str, circle_verts:int=None, type:str="CYLINDER", detail:str="LOW", bme:bmesh=None):
    """
    create round 1x1 brick with bmesh

    Keyword Arguments:
        dimensions   -- dictionary containing brick dimensions
        brick_type   -- cm.brick_type
        circle_verts -- number of vertices per circle of cylinders
        type         -- type of round 1x1 brick in ('CONE', 'CYLINDER', 'STUD', 'STUD_HOLLOW', 'STUD_TILE')
        detail       -- level of brick detail (options: ('FLAT', 'LOW', 'HIGH'))
        bme          -- bmesh object in which to create verts

    """
    # ensure type argument passed is valid
    assert type in ("CONE", "CYLINDER", "STUD", "STUD_HOLLOW", "STUD_TILE")
    # create new bmesh object
    bme = bmesh.new() if not bme else bme
    # set whether the stud on top of the brick is hollow
    hollow_stud = type in ("CONE", "CYLINDER", "STUD_HOLLOW")
    tall_type = type in ("CONE", "CYLINDER")

    # set brick height and thickness
    height = dimensions["height"] if not flat_brick_type(brick_type) or "STUD" in type else dimensions["height"] * 3
    short_brick_height = height / (3 if tall_type else 1)
    thick_xy = dimensions["thickness"]

    # initialize varying dimensions
    lower_cylinder_height = dimensions["slit_height" if "TILE" in type else "stud_height"]
    if "TILE" in type:
        lower_cylinder_height = dimensions["slit_height"]
        lower_cylinder_radius = dimensions["half_width"] - dimensions["slit_depth"]
    else:
        lower_cylinder_height = dimensions["stud_height"]
        lower_cylinder_radius = dimensions["stud_radius"] + dimensions["thickness"] / 2

    # create outer cylinder
    r = dimensions["width"] / 2
    h = height - lower_cylinder_height
    z = lower_cylinder_height / 2
    bme, verts_outer_cylinder = make_cylinder(r, h, circle_verts, co=Vector((0, 0, z)), bot_face=False, top_face="TILE" in type, bme=bme)
    # update upper cylinder verts for cone shape
    if type == "CONE":
        new_radius = dimensions["stud_radius"] * 1.075
        factor = new_radius / (dimensions["width"] / 2)
        for vert in verts_outer_cylinder["top"]:
            vert.co.xy = vec_mult(vert.co.xy, [factor]*2)

    # create lower cylinder
    r = lower_cylinder_radius
    t = r - dimensions["stud_radius"]
    h = lower_cylinder_height
    z = - (height / 2) + (lower_cylinder_height / 2)
    if not hollow_stud and detail == "FLAT":
        bme, lower_cylinder_verts = make_cylinder(r, h, circle_verts, co=Vector((0, 0, z)), top_face=False, bme=bme)
        # get pointer to outer lower tube verts
        lower_tube_verts_outer = lower_cylinder_verts
    else:
        bme, lower_tube_verts = make_tube(r - t, h, t, circle_verts, co=Vector((0, 0, z)), top_face=False, bme=bme)
        # get pointer to outer lower tube verts
        lower_tube_verts_outer = lower_tube_verts["outer"]

    # add stud
    if "TILE" not in type:
        stud_verts = add_studs(dimensions, height, [1, 1, 1], type, circle_verts, bme, hollow=hollow_stud, bot_face=False)

        # create faces connecting bottom of stud to top of outer cylinder
        stud_verts_outer = stud_verts["outer"] if hollow_stud else stud_verts
        connect_circles(verts_outer_cylinder["top"], stud_verts_outer["bottom"][::-1], bme, select=False)

    # create faces connecting bottom of outer cylinder with top of lower tube
    connect_circles(lower_tube_verts_outer["top"], verts_outer_cylinder["bottom"][::-1], bme, select=False)

    # create small inner cylinder inside stud for high detail
    if type == "STUD" and detail == "HIGH":
        # make stud cutout
        r = dimensions["stud_cutout_radius"]
        h = height - dimensions["stud_height"] + dimensions["stud_cutout_height"]
        z = (dimensions["half_height"] + dimensions["stud_cutout_height"]) / 2
        bme, stud_cutout_verts = make_cylinder(r, h, circle_verts, co=Vector((0, 0, z)), bot_face=False, flip_normals=True, bme=bme)
        # create faces connecting bottom of stud cutout with top of lower tube
        bot_verts_from_stud_cutout = stud_cutout_verts["bottom"][::-1]
        connect_circles(lower_tube_verts["inner"]["top"], bot_verts_from_stud_cutout, bme)
    # create face at top of cylinder inside brick
    elif type == "STUD" and detail == "LOW":
        bme.faces.new(lower_tube_verts["inner"]["top"])
    # join the hollow stud to the underside detail
    elif hollow_stud:
        # TODO: improve the topology of the cones here... as this isn't accurate to their mold
        # move the inner-bottom hollow stud verts down
        z_loc = height / 2 - (short_brick_height - dimensions["stud_height"])
        for v in stud_verts["inner"]["bottom"] + lower_tube_verts["inner"]["top"]:
            v.co.z = z_loc
        # connect them to the inner-top lower tube verts
        connect_circles(lower_tube_verts["inner"]["top"], stud_verts["inner"]["bottom"][::-1], bme)
    elif "TILE" in type and detail != "FLAT":
        z_loc = dimensions["stud_z_thickness"]
        for v in lower_tube_verts["inner"]["top"]:
            v.co.z = z_loc
        bme.faces.new(lower_tube_verts["inner"]["top"])

    return bme
