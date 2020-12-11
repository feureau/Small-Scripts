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
from ...common import *
from ...general import *
from ..types import *


def add_supports(dimensions, height, brick_size, brick_type, circle_verts, type, detail, d, scalar, thick, bme, hollow=None, add_beams=None):
    # initialize vars
    if hollow is None:
        add_beams = brick_size[2] == 3 and (sum(brick_size[:2]) > 4 or min(brick_size[:2]) == 1 and max(brick_size[:2]) == 3) and detail == "HIGH"
        hollow = brick_size[2] == 1 or min(brick_size[:2]) != 1
    b_and_p_brick = flat_brick_type(brick_type) and brick_size[2] == 3
    min_s = min(brick_size)
    sides = [0, 1] + ([0, 0, 1, 1] if brick_size[0] < brick_size[1] else [1, 1, 0, 0])
    sides2 = [0, 1] + ([1, 1, 0, 0] if brick_size[0] < brick_size[1] else [0, 0, 1, 1])
    z1 = d.z - height * 0.99975 if min_s > 2 else (d.z - thick.z - dimensions["support_height_triple" if b_and_p_brick else "support_height"])
    z2 = d.z - thick.z
    r = dimensions["stud_radius"] if min(brick_size[:2]) != 1 else dimensions["bar_radius"] - (dimensions["tube_thickness"] if hollow else 0)
    h = height - thick.z
    t = dimensions["tube_thickness"]
    tube_z = -(thick.z / 2)
    all_top_verts = []
    start_x = -1 if brick_size[0] == 1 else 0
    start_y = -1 if brick_size[1] == 1 else 0
    start_x = 1 if type == "SLOPE" and brick_size[:2] in ([3, 1], [4, 1]) else start_x
    start_y = 1 if type == "SLOPE" and brick_size[:2] in ([1, 3], [1, 4]) else start_y
    # add supports for each appropriate underside location
    for x_num in range(start_x, brick_size[0] - 1):
        for y_num in range(start_y, brick_size[1] - 1):
            # skip every other support cylinder location for bricks larger than 2 in all directions
            if min_s > 2 and (x_num + y_num) % 2 == 1:
                continue
            # add support tubes
            tube_x = (x_num * d.x * 2) + d.x * (2 if brick_size[0] == 1 else 1)
            tube_y = (y_num * d.y * 2) + d.y * (2 if brick_size[1] == 1 else 1)
            if hollow:
                bme, tube_verts = make_tube(r, h, t, circle_verts, co=Vector((tube_x, tube_y, tube_z)), bot_face=True, top_face=False, bme=bme)
                all_top_verts += tube_verts["outer"]["top"] + tube_verts["inner"]["top"]
            else:
                bme, tube_verts = make_cylinder(r, h, circle_verts, co=Vector((tube_x, tube_y, tube_z)), bot_face=True, top_face=False, bme=bme)
                all_top_verts += tube_verts["top"]
            # add support beams next to odd tubes
            if not add_beams or detail != "HIGH":
                continue
            if min_s % 2 == 0 and (brick_size[0] > brick_size[1] or min_s > 2):
                if brick_size[0] == 3 or x_num % 2 == 1 or (brick_size == [8, 1, 3] and x_num in (0, brick_size[0] - 2)):
                    # initialize x, y
                    x1 = tube_x - (dimensions["support_width"] / 2)
                    x2 = tube_x + (dimensions["support_width"] / 2)
                    y1 = tube_y + r
                    y2 = tube_y + d.y * min([min_s, 4]) - thick.y - (0 if y_num >= brick_size[1] - 3 else dimensions["tube_thickness"])
                    y3 = tube_y - d.y * min([min_s, 4]) + thick.y
                    y4 = tube_y - r
                    # create support beam
                    cur_sides = sides if brick_size[0] > brick_size[1] else sides2
                    if min_s == 1:
                        cube_verts = make_cube(Vector((x1, y3, z1)), Vector((x2, y2, z2)), sides=cur_sides, bme=bme)[1]
                        all_top_verts += cube_verts[4:]
                    else:
                        cube_verts1 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=cur_sides, bme=bme)[1]
                        all_top_verts += cube_verts1[4:]
                        if y_num <= 1:
                            cube_verts2 = make_cube(Vector((x1, y3, z1)), Vector((x2, y4, z2)), sides=cur_sides, bme=bme)[1]
                            all_top_verts += cube_verts2[4:]
            if min_s % 2 == 0 and (brick_size[1] > brick_size[0] or min_s > 2):
                if brick_size[1] == 3 or y_num % 2 == 1 or (brick_size == [1, 8, 3] and y_num in (0, brick_size[1] - 2)):
                    # initialize x, y
                    x1 = tube_x + r
                    x2 = tube_x + d.x * min([min_s, 4]) - thick.x - (0 if x_num >= brick_size[0] - 3 else dimensions["tube_thickness"])
                    x3 = tube_x - d.x * min([min_s, 4]) + thick.x
                    x4 = tube_x - r
                    y1 = tube_y - (dimensions["support_width"] / 2)
                    y2 = tube_y + (dimensions["support_width"] / 2)
                    cur_sides = sides if brick_size[1] > brick_size[0] else sides2
                    # create support beam
                    if min_s == 1:
                        cube_verts = make_cube(Vector((x3, y1, z1)), Vector((x2, y2, z2)), sides=cur_sides, bme=bme)[1]
                        all_top_verts += cube_verts[4:]
                    else:
                        cube_verts1 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=cur_sides, bme=bme)[1]
                        all_top_verts += cube_verts1[4:]
                        if x_num <= 1:
                            cube_verts2 = make_cube(Vector((x3, y1, z1)), Vector((x4, y2, z2)), sides=cur_sides, bme=bme)[1]
                            all_top_verts += cube_verts2[4:]
    if type == "SLOPE":
        cut_verts(dimensions, height, brick_size, all_top_verts, d, scalar, thick, bme)


def add_oblong_supports(dimensions, height, circle_verts, type, detail, d, scalar, thick, bme):
    # round circle_verts to multiple of 4
    circle_verts = round_up(circle_verts, 4)
    # initialize inner_verts
    inner_verts = {"top":{"-":[], "+":[]}, "mid":{"-":[], "+":[]}, "bottom":{"-":[], "+":[]}}
    # get support tube dimensions
    tube_x = 0
    tube_y1 = round(d.y - dimensions["oblong_support_dist"], 8)
    tube_y2 = round(d.y + dimensions["oblong_support_dist"], 8)
    tube_z = -(thick.z - dimensions["slit_depth"]) / 2
    r = dimensions["oblong_support_radius"]
    h = height - (thick.z + dimensions["slit_depth"])
    # generate parallel cylinders
    bme, tube_verts1 = make_cylinder(r, h, circle_verts, co=Vector((tube_x, tube_y1, tube_z)), bot_face=True, top_face=False, bme=bme)
    bme, tube_verts2 = make_cylinder(r, h, circle_verts, co=Vector((tube_x, tube_y2, tube_z)), bot_face=True, top_face=False, bme=bme)
    # remove half of cylinders and populate 'inner_verts'
    for side in ["top", "bottom"]:
        half_circs1 = []
        half_circs2 = []
        for v in tube_verts1[side]:
            co_y = round(v.co.y, 8)
            if co_y > tube_y1:
                bme.verts.remove(v)
            else:
                half_circs1.append(v)
            if co_y == tube_y1:
                inner_verts[side]["-"].append(v)
        for v in tube_verts2[side]:
            co_y = round(v.co.y, 8)
            if co_y < tube_y2:
                bme.verts.remove(v)
            else:
                half_circs2.append(v)
            if co_y == tube_y2:
                inner_verts[side]["+"].append(v)
        if side == "bottom":
            bme.faces.new(sorted(half_circs1, key=lambda x: -x.co.x) + sorted(half_circs2, key=lambda x: x.co.x))
    # connect half-cylinders
    bme.faces.new((inner_verts["top"]["+"][0], inner_verts["top"]["-"][0], inner_verts["bottom"]["-"][1], inner_verts["bottom"]["+"][1]))
    bme.faces.new((inner_verts["top"]["-"][1], inner_verts["top"]["+"][1], inner_verts["bottom"]["+"][0], inner_verts["bottom"]["-"][0]))
    # add low beam next to oblong support
    support_width = dimensions["slope_support_width"]
    support_height = dimensions["slope_support_height"]
    cube_y1 = round(d.y - support_width/2, 8)
    cube_y2 = round(d.y + support_width/2, 8)
    coord1 = Vector((r, cube_y1, d.z - thick.z - support_height))
    coord2 = Vector((d.x - thick.x + (dimensions["tick_depth"] if detail == "HIGH" else 0), cube_y2, d.z - thick.z))
    make_cube(coord1, coord2, sides=[0,1,0,0,1,1], bme=bme)
    coord1 = Vector((-d.x + thick.x, cube_y1, d.z - thick.z - support_height))
    coord2 = Vector((-r, cube_y2, d.z - thick.z))
    make_cube(coord1, coord2, sides=[0,1,0,0,1,1], bme=bme)



def add_slope_studs(dimensions, height, brick_size, brick_type, circle_verts, bme, edge_xp=None, edge_xn=None, edge_yp=None, edge_yn=None, underside=False):
    r = dimensions["stud_radius"] if underside else dimensions["bar_radius"]
    h = dimensions["stud_height"]
    t = dimensions["stud_radius"] - dimensions["bar_radius"]
    z = (dimensions["stud_height"] + (-height if underside else height)) / 2
    s_min = edge_yp[0].co
    s_max = edge_yp[1].co
    s_dist_x = s_max.x - s_min.x
    s_dist_z = s_max.z - s_min.z
    end_verts = []
    all_semi_circle_verts = []
    # round circle_verts if underside
    if underside: circle_verts = round_up(circle_verts, 4)
    # make studs
    top_verts_d_of_ds = {}
    # for x_num in range(1, max(brick_size[:2])):
    #     for y_num in range(min(brick_size[:2])):
    for x_num in range(1, brick_size[0]):
        for y_num in range(brick_size[1]):
            x = dimensions["width"] * x_num
            y = dimensions["width"] * y_num
            if underside:
                _, stud_verts = make_cylinder(r, h, circle_verts, co=Vector((x, y, z)), bot_face=False, flip_normals=True, bme=bme)
                # move bottom verts of tubes to slope plane
                for v in stud_verts["bottom"]:
                    cur_ratio = (v.co.x - s_min.x) / s_dist_x
                    v.co.z = s_min.z + s_dist_z * cur_ratio
                # move top verts of tubes to middle of bottom verts
                z_ave = sum([v.co.z for v in stud_verts["bottom"]]) / len(stud_verts["bottom"])
                for v in stud_verts["top"]:
                    v.co.z = z_ave
                # remove half of cylinder
                for v in stud_verts["bottom"]:
                    if round(v.co.x, 8) > x:
                        bme.verts.remove(v)
                for v in stud_verts["top"]:
                    if round(v.co.x, 8) >= x:
                        bme.verts.remove(v)
                f0 = bme.faces.new((stud_verts["bottom"][circle_verts // 4 - 1], stud_verts["bottom"][circle_verts // 4], stud_verts["top"][(circle_verts // 4) * 3 - 1]))
                f1 = bme.faces.new((stud_verts["bottom"][(circle_verts // 4) * 3 - 2], stud_verts["bottom"][(circle_verts // 4) * 3 - 1], stud_verts["top"][circle_verts // 4 + 1]))
                f0.smooth = True
                f1.smooth = True
                bme.faces.new([v for v in stud_verts["top"][::-1] if v.is_valid] + [stud_verts["bottom"][(circle_verts // 4) * 3 - 1], stud_verts["bottom"][circle_verts // 4 - 1]])
                if y_num == 0:
                    bme.faces.new((edge_xn[0], edge_xp[1], stud_verts["bottom"][circle_verts // 4 - 1]))
                if y_num == min(brick_size[:2]) - 1:
                    bme.faces.new((edge_xp[0], edge_xn[1], stud_verts["bottom"][(circle_verts // 4) * 3 - 1]))
                end_verts += [stud_verts["bottom"][circle_verts // 4 - 1], stud_verts["bottom"][(circle_verts // 4) * 3 - 1]]
                all_semi_circle_verts += [v for v in stud_verts["bottom"] if v.is_valid]
            else:
                _, stud_verts = make_tube(r, h, t, circle_verts, co=Vector((x, y, z)), bot_face=False, bme=bme)
                # move bottom verts of tubes to slope plane
                for key in stud_verts:
                    for v in stud_verts[key]["bottom"]:
                        cur_ratio = (v.co.x - s_min.x) / s_dist_x
                        v.co.z = s_min.z + s_dist_z * cur_ratio
                if edge_xp is not None: bme.faces.new(stud_verts["inner"]["bottom"][::1 if underside else -1])
                select_geom(stud_verts["inner"]["bottom"] + stud_verts["outer"]["bottom"])
                if edge_xp is not None:
                    adj_x_num = x_num - 1
                    top_verts_d = create_vert_list_dict2(stud_verts["bottom"] if underside else stud_verts["outer"]["bottom"])
                    top_verts_d_of_ds["%(adj_x_num)s,%(y_num)s" % locals()] = top_verts_d
    if edge_xp is not None and not underside:
        connect_circles_to_square(dimensions, [brick_size[0] - 1, brick_size[1], brick_size[2]], circle_verts, edge_xn[::-1], edge_xp, edge_yn, edge_yp[::-1], top_verts_d_of_ds, x_num - 1, y_num, bme, flip_normals=not underside)
    if underside:
        bme.faces.new((edge_xp + all_semi_circle_verts)[::-1])
        bme.faces.new(edge_xn[::-1] + end_verts)
    return stud_verts


def cut_verts(dimensions, height, brick_size, verts, d, scalar, thick, bme):
    min_z = -(height / 2) + thick.z
    for v in verts:
        numer = v.co.x - d.x
        denom = d.x * (scalar.x - 1) - (dimensions["tube_thickness"] + dimensions["stud_radius"]) * (brick_size[0] - 2) + (thick.z * (brick_size[0] - 3))
        fac = numer / denom
        if fac < 0:
            continue
        v.co.z = fac * min_z + (1-fac) * v.co.z


def add_stud_cutouts(dimensions, brick_size, circle_verts, d, edge_xp, edge_xn, edge_yp, edge_yn, bme):
    thick_z = dimensions["thickness"]
    # make small cylinders
    bov_verts_d_of_ds = {}
    r = dimensions["stud_cutout_radius"]
    N = circle_verts
    h = dimensions["stud_cutout_height"]
    for x_num in range(brick_size[0]):
        for y_num in range(brick_size[1]):
            bme, inner_cylinder_verts = make_cylinder(-r, h, N, co=Vector((x_num * d.x * 2, y_num * d.y * 2, d.z - thick_z + h / 2)), bot_face=False, flip_normals=True, bme=bme)
            bov_verts_d = create_vert_list_dict(inner_cylinder_verts["bottom"])
            bov_verts_d_of_ds["%(x_num)s,%(y_num)s" % locals()] = bov_verts_d
    connect_circles_to_square(dimensions, brick_size, circle_verts, edge_xp, edge_xn, edge_yp, edge_yn, bov_verts_d_of_ds, x_num, y_num, bme)


def add_studs(dimensions, height, brick_size, brick_type, circle_verts, bme, edge_xp=None, edge_xn=None, edge_yp=None, edge_yn=None, hollow=False, bot_face=True):
    r = dimensions["bar_radius" if hollow else "stud_radius"]
    h = dimensions["stud_height"]
    t = dimensions["stud_radius"] - dimensions["bar_radius"]
    z = height / 2 + dimensions["stud_height"] / 2
    # make studs
    top_verts_d_of_ds = {}
    for x_num in range(brick_size[0]):
        for y_num in range(brick_size[1]):
            x = dimensions["width"] * x_num
            y = dimensions["width"] * y_num
            if hollow:
                _, stud_verts = make_tube(r, h, t, circle_verts, co=Vector((0, 0, z)), bot_face=bot_face, bme=bme)
                if edge_xp is not None: bme.faces.new(stud_verts["inner"]["bottom"])
            else:
                # split stud at center by creating cylinder and circle and joining them (allows Bevel to work correctly)
                _, stud_verts = make_cylinder(r, h, circle_verts, co=Vector((x, y, z)), bot_face=False, bme=bme)
            if edge_xp is not None:
                top_verts_d = create_vert_list_dict2(stud_verts["outer"]["bottom"] if hollow else stud_verts["bottom"])
                top_verts_d_of_ds["%(x_num)s,%(y_num)s" % locals()] = top_verts_d
    if edge_xp is not None:
        connect_circles_to_square(dimensions, brick_size, circle_verts, edge_xp, edge_xn, edge_yp, edge_yn, top_verts_d_of_ds, x_num, y_num, bme, flip_normals=True)
    return stud_verts


def connect_circles_to_square(dimensions, brick_size, circle_verts, edge_xp, edge_xn, edge_yp, edge_yn, verts_d_of_ds, x_num, y_num, bme, flip_normals=False):
    # join_verts = {"Y+":[v7, v8], "Y-":[v6, v5], "X+":[v7, v6], "X-":[v8, v5]}
    thick_z = dimensions["thickness"]
    sX = brick_size[0]
    sY = brick_size[1]
    step = -1 if flip_normals else 1
    edges_to_select = list()
    # Make corner faces if few cylinder verts
    v5 = edge_yn[-1]
    v6 = edge_yn[0]
    v7 = edge_yp[0]
    v8 = edge_yp[-1]
    l = "0,0"
    if len(verts_d_of_ds[l]["--"]) == 0:
        f = bme.faces.new((verts_d_of_ds[l]["y-"][0], verts_d_of_ds[l]["x-"][0], v5)[::-step])
        edges_to_select += f.edges[1:]
        f.smooth = True
    l = "%(x_num)s,0" % locals()
    if len(verts_d_of_ds[l]["+-"]) == 0:
        f = bme.faces.new((verts_d_of_ds[l]["x+"][0], verts_d_of_ds[l]["y-"][0], v6)[::-step])
        edges_to_select += f.edges[1:]
        f.smooth = True
    l = "%(x_num)s,%(y_num)s" % locals()
    if len(verts_d_of_ds[l]["++"]) == 0:
        f = bme.faces.new((verts_d_of_ds[l]["y+"][0], verts_d_of_ds[l]["x+"][0], v7)[::-step])
        edges_to_select += f.edges[1:]
        f.smooth = True
    l = "0,%(y_num)s" % locals()
    if len(verts_d_of_ds[l]["-+"]) == 0:
        f = bme.faces.new((verts_d_of_ds[l]["x-"][0], verts_d_of_ds[l]["y+"][0], v8)[::-step])
        edges_to_select += f.edges[1:]
        f.smooth = True

    # Make edge faces
    join_verts = {"Y+":edge_yp, "Y-":edge_yn, "X+":edge_xp, "X-":edge_xn}
    join_verts_orig_lengths = {"Y+":len(edge_yp), "Y-":len(edge_yn), "X+":len(edge_xp), "X-":len(edge_xn)}
    # Make edge faces on Y- and Y+ sides
    for x_num in range(sX):
        vert_d_pos = verts_d_of_ds[str(x_num) + "," + str(y_num)]
        vert_d_neg = verts_d_of_ds[str(x_num) + "," + str(0)]
        for sign, vert_d, dir, func in (["+", vert_d_pos, 1, math.ceil], ["-", vert_d_neg, -1, math.floor]):
            side = "Y%(sign)s" % locals()
            verts = vert_d["-%(sign)s" % locals()]
            if x_num > 0:
                join_verts[side].append(vert_d["x-"][0])
                for v in verts[::dir]:
                    join_verts[side].append(v)
            else:
                for v in verts[::dir][func(len(verts)/2) - (1 if dir == 1 else 0):]:
                    join_verts[side].append(v)
            join_verts[side].append(vert_d["y%(sign)s" % locals()][0])
            verts = vert_d["+%(sign)s" % locals()]
            if x_num < sX - 1:
                for v in verts[::dir]:
                    join_verts[side].append(v)
                join_verts[side].append(vert_d["x+"][0])
            else:
                for v in verts[::dir][:func(len(verts)/2) + (1 if dir == -1 else 0)]:
                    join_verts[side].append(v)
    # Make edge faces on X- and X+ sides
    for y_num in range(sY):
        vert_d_pos = verts_d_of_ds[str(x_num) + "," + str(y_num)]
        vert_d_neg = verts_d_of_ds[str(0) + "," + str(y_num)]
        for sign, vert_d, dir, func in (["+", vert_d_pos, -1, math.floor], ["-", vert_d_neg, 1, math.ceil]):
            side = "X%(sign)s" % locals()
            verts = vert_d["%(sign)s-" % locals()]
            if y_num > 0:
                join_verts[side].append(vert_d["y-"][0])
                for v in verts[::dir]:
                    join_verts[side].append(v)
            else:
                for v in verts[::dir][func(len(verts)/2) - (1 if dir == 1 else 0):]:
                    join_verts[side].append(v)
            join_verts[side].append(vert_d["x%(sign)s" % locals()][0])
            verts = vert_d["%(sign)s+" % locals()]
            if y_num < sY - 1:
                for v in verts[::dir]:
                    join_verts[side].append(v)
                join_verts[side].append(vert_d["y+"][0])
            else:
                for v in verts[::dir][:func(len(verts)/2) + (1 if dir == -1 else 0)]:
                    join_verts[side].append(v)
    for item in join_verts:
        step0 = -step if item in ("Y+", "X-") else step
        f = bme.faces.new(join_verts[item][::step0])
        edges_to_select.append(get_shared_edge(join_verts[item][join_verts_orig_lengths[item] - 1], join_verts[item][join_verts_orig_lengths[item]]))
        edges_to_select.append(get_shared_edge(join_verts[item][-1], join_verts[item][0]))
        f.smooth = True

    # select edges that should not be beveled
    for e in edges_to_select:
        e.select = True

    if 1 in brick_size[:2]:
        return

    # Make center faces
    for y_num in range(sY - 1):
        for x_num in range(sX - 1):
            verts = []
            l = str(x_num) + "," + str(y_num)
            verts += verts_d_of_ds[l]["y+"]
            v1 = verts[-1]
            verts += verts_d_of_ds[l]["++"]
            verts += verts_d_of_ds[l]["x+"]
            v2 = verts[-1]
            l = str(x_num + 1) + "," + str(y_num)
            verts += verts_d_of_ds[l]["x-"]
            v3 = verts[-1]
            verts += verts_d_of_ds[l]["-+"]
            verts += verts_d_of_ds[l]["y+"]
            v4 = verts[-1]
            l = str(x_num + 1) + "," + str(y_num + 1)
            verts += verts_d_of_ds[l]["y-"]
            v5 = verts[-1]
            verts += verts_d_of_ds[l]["--"]
            verts += verts_d_of_ds[l]["x-"]
            v6 = verts[-1]
            l = str(x_num) + "," + str(y_num + 1)
            verts += verts_d_of_ds[l]["x+"]
            v7 = verts[-1]
            verts += verts_d_of_ds[l]["+-"]
            verts += verts_d_of_ds[l]["y-"]
            v8 = verts[-1]
            f = bme.faces.new(verts[::-step])
            get_shared_edge(v2, v3).select = True
            get_shared_edge(v4, v5).select = True
            get_shared_edge(v6, v7).select = True
            get_shared_edge(v8, v1).select = True
            f.smooth = True


def add_tick_marks(dimensions, brick_size, circle_verts, detail, d, thick, bme, nno=None, npo=None, ppo=None, pno=None, nni=None, npi=None, ppi=None, pni=None, nnt=None, npt=None, ppt=None, pnt=None, inverted_slope=False, side_marks=True):
    # for edge vert refs, n=negative, p=positive, o=outer, i=inner, t=top
    join_verts = {"X-":[npi, npo, nno, nni], "X+":[ppi, ppo, pno, pni], "Y-":[pni, pno, nno, nni], "Y+":[ppi, ppo, npo, npi]}
    last_side_verts = {"X-":[nnt, nni], "X+":[pni, pnt], "Y-":[nni, nnt], "Y+":[npt, npi]}
    bottom_verts = {"X-":[], "X+":[], "Y-":[], "Y+":[]}
    tick_depth = dimensions["slope_tick_depth"] if inverted_slope else dimensions["tick_depth"]
    tick_width = dimensions["support_width"] if inverted_slope else dimensions["tick_width"]
    # make tick marks
    for x_num in range(brick_size[0]):
        for y_num in range(brick_size[1]):
            # initialize z
            z1 = -d.z
            z2 = d.z - thick.z
            if x_num == 0 and side_marks:
                # initialize x, y
                x1 = -d.x + thick.x
                x2 = -d.x + thick.x + tick_depth
                y1 = y_num * d.y * 2 - tick_width / 2
                y2 = y_num * d.y * 2 + tick_width / 2
                # CREATING SUPPORT BEAM
                v1, v2, _, _, v5, v6, v7, v8 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=[0, 1, 1, 0, 1, 1], bme=bme)[1]
                join_verts["X-"] += [v1, v2]
                # get_shared_edge(v1, v2).select = True
                bme.faces.new([v1, v5] + last_side_verts["X-"])
                last_side_verts["X-"] = [v8, v2]
                bottom_verts["X-"] += [v5, v6, v7, v8]
            elif x_num == brick_size[0]-1:
                # initialize x, y
                x1 = x_num * d.x * 2 + d.x - thick.x - tick_depth
                x2 = x_num * d.x * 2 + d.x - thick.x
                y1 = y_num * d.y * 2 - tick_width / 2
                y2 = y_num * d.y * 2 + tick_width / 2
                # CREATING SUPPORT BEAM
                _, _, v3, v4, v5, v6, v7, v8 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=[0, 1, 0, 1, 1, 1], bme=bme)[1]
                join_verts["X+"] += [v4, v3]
                # get_shared_edge(v4, v3).select = True
                bme.faces.new([v6, v4] + last_side_verts["X+"])
                last_side_verts["X+"] = [v3, v7]
                bottom_verts["X+"] += [v6, v5, v8, v7]
            if y_num == 0 and side_marks:
                # initialize x, y
                y1 = -d.y + thick.y
                y2 = -d.y + thick.y + tick_depth
                x1 = x_num * d.x * 2 - tick_width / 2
                x2 = x_num * d.x * 2 + tick_width / 2
                # CREATING SUPPORT BEAM
                v1, _, _, v4, v5, v6, v7, v8 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=[0, 1, 1, 1, 1, 0], bme=bme)[1]
                join_verts["Y-"] += [v1, v4]
                # get_shared_edge(v1, v4).select = True
                bme.faces.new([v5, v1] + last_side_verts["Y-"])
                last_side_verts["Y-"] = [v4, v6]
                bottom_verts["Y-"] += [v5, v8, v7, v6]
            elif y_num == brick_size[1]-1 and side_marks:
                # initialize x, y
                x1 = x_num * d.x * 2 - tick_width / 2
                x2 = x_num * d.x * 2 + tick_width / 2
                y1 = y_num * d.y * 2 + d.y - thick.y - tick_depth
                y2 = y_num * d.y * 2 + d.y - thick.y
                # CREATING SUPPORT BEAM
                _, v2, v3, _, v5, v6, v7, v8 = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), sides=[0, 1, 1, 1, 0, 1], bme=bme)[1]
                # select bottom connecting verts for exclusion from vertex group
                join_verts["Y+"] += [v2, v3]
                # get_shared_edge(v2, v3).select = True
                bme.faces.new([v2, v8] + last_side_verts["Y+"])
                last_side_verts["Y+"] = [v7, v3]
                bottom_verts["Y+"] += [v8, v5, v6, v7]

    # draw faces between ticks and base
    bme.faces.new(join_verts["X+"])
    bme.faces.new([ppt, ppi] + last_side_verts["X+"])
    if side_marks:
        bme.faces.new(join_verts["X-"][::-1])
        bme.faces.new([npi, npt] + last_side_verts["X-"])
        bme.faces.new(join_verts["Y-"])
        bme.faces.new(join_verts["Y+"][::-1])
        bme.faces.new([pnt, pni] + last_side_verts["Y-"])
        bme.faces.new([ppi, ppt] + last_side_verts["Y+"])

    return bottom_verts


def create_vert_list_dict(verts):
    idx1 = int(round(len(verts) * 1 / 4)) - 1
    idx2 = int(round(len(verts) * 2 / 4)) - 1
    idx3 = int(round(len(verts) * 3 / 4)) - 1
    idx4 = int(round(len(verts) * 4 / 4)) - 1

    vert_list_dict = {"++":[verts[idx] for idx in range(idx1 + 1, idx2)],
                     "+-":[verts[idx] for idx in range(idx2 + 1, idx3)],
                     "--":[verts[idx] for idx in range(idx3 + 1, idx4)],
                     "-+":[verts[idx] for idx in range(0,        idx1)],
                     "y+":[verts[idx1]],
                     "x+":[verts[idx2]],
                     "y-":[verts[idx3]],
                     "x-":[verts[idx4]]}

    return vert_list_dict


def create_vert_list_dict2(verts):
    idx1 = int(round(len(verts) * 1 / 4)) - 1
    idx2 = int(round(len(verts) * 2 / 4)) - 1
    idx3 = int(round(len(verts) * 3 / 4)) - 1
    idx4 = int(round(len(verts) * 4 / 4)) - 1

    vert_list_dict = {"--":[verts[idx] for idx in range(idx1 + 1, idx2)],
                     "-+":[verts[idx] for idx in range(idx2 + 1, idx3)],
                     "++":[verts[idx] for idx in range(idx3 + 1, idx4)],
                     "+-":[verts[idx] for idx in range(0,        idx1)],
                     "y-":[verts[idx1]],
                     "x-":[verts[idx2]],
                     "y+":[verts[idx3]],
                     "x+":[verts[idx4]]}

    return vert_list_dict


def add_grill_details(dimensions, brick_size, thick, scalar, d, v1, v2, v3, v4, v9, v10, v11, v12, bme):
    # NOTE: n=negative, p=positive, m=middle
    # inner support in middle
    x1 = dimensions["stud_radius"]
    x2 = dimensions["stud_radius"] + (d.x - dimensions["stud_radius"]) * 2
    y1 = -dimensions["thickness"] / 2
    y2 =  dimensions["thickness"] / 2
    z1 = -d.z
    z2 = d.z - dimensions["thickness"]
    mms = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), [0, 1, 1, 1, 1, 1], bme=bme)[1]

    z1 = d.z - dimensions["thickness"]
    z2 = d.z
    # upper middle x- grill
    x1 = -d.x
    x2 = -d.x + dimensions["thickness"]
    nmg = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), [1, 0, 0, 1, 1, 1], bme=bme)[1]
    # upper y- x- grill
    y3 = y1 - dimensions["thickness"] * 2
    y4 = y2 - dimensions["thickness"] * 2
    nng = make_cube(Vector((x1, y3, z1)), Vector((x2, y4, z2)), [1, 0, 0, 1, 1, 1], bme=bme)[1]
    bme.verts.remove(nng[3])
    nng[3] = None
    # upper y+ x- grill
    y3 = y1 + dimensions["thickness"] * 2
    y4 = y2 + dimensions["thickness"] * 2
    npg = make_cube(Vector((x1, y3, z1)), Vector((x2, y4, z2)), [1, 0, 0, 1, 1, 1], bme=bme)[1]
    bme.verts.remove(npg[2])
    npg[2] = None

    # upper middle x+ grill
    x1 = d.x * 3 - dimensions["thickness"]
    x2 = d.x * 3
    pmg = make_cube(Vector((x1, y1, z1)), Vector((x2, y2, z2)), [1, 0, 1, 0, 1, 1], bme=bme)[1]
    # upper y- x+ grill
    y3 = y1 - dimensions["thickness"] * 2
    y4 = y2 - dimensions["thickness"] * 2
    png = make_cube(Vector((x1, y3, z1)), Vector((x2, y4, z2)), [1, 0, 1, 0, 1, 1], bme=bme)[1]
    bme.verts.remove(png[0])
    png[0] = None
    # upper y+ x+ grill
    y3 = y1 + dimensions["thickness"] * 2
    y4 = y2 + dimensions["thickness"] * 2
    ppg = make_cube(Vector((x1, y3, z1)), Vector((x2, y4, z2)), [1, 0, 1, 0, 1, 1], bme=bme)[1]
    bme.verts.remove(ppg[1])
    ppg[1] = None

    # connect grill tops
    bme.faces.new((pmg[4], pmg[7], nmg[6], nmg[5]))
    bme.faces.new((png[4], png[7], nng[6], nng[5]))
    bme.faces.new((ppg[4], ppg[7], npg[6], npg[5]))
    # connect outer sides
    bme.faces.new((v4, png[3], png[5], nng[4], nng[0], v1))
    bme.faces.new((v2, npg[1], npg[7], ppg[6], ppg[2], v3))
    bme.faces.new((v3, ppg[2], ppg[3], pmg[2], pmg[3], png[2], png[3], v4))
    bme.faces.new((v1, nng[0], nng[1], nmg[0], nmg[1], npg[0], npg[1], v2))
    # connect grills together
    bme.faces.new((nng[1], nng[2], nmg[3], nmg[0]))
    bme.faces.new((nmg[1], nmg[2], npg[3], npg[0]))
    bme.faces.new((png[1], png[2], pmg[3], pmg[0]))
    bme.faces.new((pmg[1], pmg[2], ppg[3], ppg[0]))
    bme.faces.new((nmg[5], nmg[3], mms[4], mms[5], pmg[0], pmg[4]))
    bme.faces.new((pmg[7], pmg[1], mms[6], mms[7], nmg[2], nmg[6]))
    # connect grill to base
    bme.faces.new((nmg[2], mms[7], mms[4], nmg[3]))
    bme.faces.new((pmg[0], mms[5], mms[6], pmg[1]))
    # create square at inner base
    coord1 = -d + Vector((thick.x, thick.y, 0))
    coord2 = vec_mult(d, scalar) - thick
    coord2.z = -d.z
    v17, v18, v19, v20 = make_rectangle(coord1, coord2, face=False, bme=bme)[1]
    # connect inner base to outer base
    bme.faces.new((v17, v9, v10, v20))
    bme.faces.new((v20, v10, v11, v19))
    bme.faces.new((v19, v11, v12, v18))
    bme.faces.new((v18, v12, v9, v17))
    # create inner faces
    if brick_size[0] < brick_size[1]:
        bme.faces.new((v17, v20, ppg[0], ppg[4], npg[5], npg[4]))
        bme.faces.new((v19, v18, nng[2], nng[6], png[7], png[1]))
        bme.faces.new((v20, v19, png[1], pmg[0], pmg[1], ppg[0]))
        bme.faces.new((v18, v17, npg[3], nmg[2], nmg[3], nng[2]))
    else:
        bme.faces.new((v20, v19, ppg[0], ppg[4], npg[5], npg[4]))
        bme.faces.new((v18, v17, nng[2], nng[6], png[7], png[1]))
        bme.faces.new((v19, v18, png[1], pmg[0], pmg[1], ppg[0]))
        bme.faces.new((v17, v20, npg[3], nmg[2], nmg[3], nng[2]))

    # rotate created vertices in to place if necessary
    if brick_size[0] < brick_size[1]:
        vertsCreated = nng + nmg + npg + png + pmg + ppg + mms
        vertsCreated = [v for v in vertsCreated if v is not None]
        bmesh.ops.rotate(bme, verts=vertsCreated, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'Z'))
