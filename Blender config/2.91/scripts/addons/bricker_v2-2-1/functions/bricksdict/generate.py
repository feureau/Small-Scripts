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
import numpy as np

# Blender imports
import bpy
from bpy.types import Object, Scene, CollectionProperty
from mathutils import Matrix, Vector

# Module imports
from .make_lattice import generate_lattice
from .getters import *
from .modify import *
from ..common import *
from ..general import *
from ..colors import *
from ..mat_utils import *
from ..object_getters import *
from ..smoke_sim import *
from ..brick import *

accs = [0, 0, 0, 0, 0]


def cast_rays(obj_eval:Object, point:Vector, direction:Vector, mini_dist:float, round_type:str="CEILING", edge_len:int=0):
    """
    obj_eval   -- source object to test intersections for
    point      -- starting point for ray casting
    direction  -- cast ray in this direction
    mini_dist  -- Vector with miniscule amount to add after intersection
    round_type -- round final intersection location Vector with this type
    edge_len   -- distance to test for intersections
    """
    # initialize variables
    first_direction = False
    first_intersection = None
    next_intersection_loc = None
    last_intersection = None
    edge_intersects = False
    edge_len2 = round(edge_len + 0.000001, 6)
    starting_point = point
    intersections = 0
    # cast rays until no more rays to cast
    while True:
        _,location,normal,index = obj_eval.ray_cast(starting_point, direction)#distance=edge_len*1.00000000001)
        if index == -1: break
        if intersections == 0:
            first_direction = direction.dot(normal)
        if edge_len != 0:
            dist = (location - point).length
            # get first and last intersection (used when getting materials of nearest (first or last intersected) face)
            if dist <= edge_len2:
                if intersections == 0:
                    edge_intersects = True
                    first_intersection = {"idx":index, "dist":dist, "loc":location, "normal":normal}
                last_intersection = {"idx":index, "dist":edge_len - dist, "loc":location, "normal":normal}

            # set next_intersection_loc
            if next_intersection_loc is None:
                next_intersection_loc = location.copy()
        intersections += 1
        location = vec_round(location, precision=6, round_type=round_type)
        starting_point = location + mini_dist

    if edge_len != 0:
        return intersections, first_direction, first_intersection, next_intersection_loc, last_intersection, edge_intersects
    else:
        return intersections, first_direction


def ray_obj_intersections(scn:Scene, point:Vector, direction:Vector, mini_dist:Vector, edge_len:float, obj:Object, use_normals:bool, insideness_ray_cast_dir:str, brick_shell:str="INSIDE"):
    """
    cast ray(s) from point in direction to determine insideness and whether edge intersects obj within edge_len

    returned:
    - not outside        - 'point' is inside object 'obj'
    - edge_intersects    - ray from 'point' in 'direction' of length 'edge_len' intersects object 'obj'
    - intersections      - number of ray-obj intersections from 'point' in 'direction' to infinity
    - next_intersection_loc - second ray intersection from 'point' in 'direction'
    - first_intersection - dictionary containing 'idx':index of first intersection and 'distance:distance from point to first intersection within edge_len
    - last_intersection  - dictionary containing 'idx':index of last intersection and 'distance:distance from point to last intersection within edge_len

    """

    # initialize variables
    intersections = 0
    outside_L = []
    if b280():
        depsgraph = bpy.context.view_layer.depsgraph
        obj_eval = obj.evaluated_get(depsgraph)
    else:
        obj_eval = obj
    # set axis of direction
    axes = "XYZ" if direction[0] > 0 else ("YZX" if direction[1] > 0 else "ZXY")
    # run initial intersection check
    intersections, first_direction, first_intersection, next_intersection_loc, last_intersection, edge_intersects = cast_rays(obj_eval, point, direction, mini_dist, edge_len=edge_len)

    if brick_shell == "CONSISTENT" and edge_intersects:
        # skip insideness checks if brick shell doesn't take insideness into account
        outside = True
    else:
        # run initial insideness check(s)
        if insideness_ray_cast_dir == "HIGH_EFFICIENCY" or axes[0] in insideness_ray_cast_dir:
            outside_L.append(0)
            if intersections % 2 == 0 and not (use_normals and first_direction > 0):
                outside_L[0] = 1
            else:
                # double check vert is inside mesh
                # NOTE: no longer optional because this is almost always necessary
                count, first_direction = cast_rays(obj_eval, point, -direction, -mini_dist, round_type="FLOOR")
                if count % 2 == 0 and not (use_normals and first_direction > 0):
                    outside_L[0] = 1

        # run more insideness checks
        if insideness_ray_cast_dir != "HIGH_EFFICIENCY":
            dir0 = Vector((direction[2], direction[0], direction[1]))
            dir1 = Vector((direction[1], direction[2], direction[0]))
            mini_dist0 = Vector((mini_dist[2], mini_dist[0], mini_dist[1]))
            mini_dist1 = Vector((mini_dist[1], mini_dist[2], mini_dist[0]))
            dirs = ((dir0, mini_dist0), (dir1, mini_dist1))
            for i in range(2):
                if axes[i + 1] in insideness_ray_cast_dir:
                    outside_L.append(0)
                    direction = dirs[i][0]
                    mini_dist = dirs[i][1]
                    count, first_direction = cast_rays(obj_eval, point, direction, mini_dist)
                    if count % 2 == 0 and not (use_normals and first_direction > 0):
                        outside_L[len(outside_L) - 1] = 1
                    else:
                        # double check vert is inside mesh
                        # NOTE: no longer optional because this is almost always necessary
                        count, first_direction = cast_rays(obj_eval, point, -direction, -mini_dist, round_type="FLOOR")
                        if count % 2 == 0 and not (use_normals and first_direction > 0):
                            outside_L[len(outside_L) - 1] = 1

        # find average of outside_L and set outside accordingly (<0.5 is False, >=0.5 is True)
        outside = sum(outside_L) / len(outside_L) >= 0.5

    # return helpful information
    return not outside, edge_intersects, intersections, next_intersection_loc, first_intersection, last_intersection


def update_bf_matrix(scn, x0, y0, z0, coord_matrix, ray, edge_len, face_idx_matrix, brick_freq_matrix, brick_shell, source, x1, y1, z1, mini_dist, use_normals, insideness_ray_cast_dir):
    """ update brick_freq_matrix[x0][y0][z0] based on results from ray_obj_intersections

    Returns:
        intersections         - Number of intersections found in whichever direction is currently 'forward'
        next_intersection_loc - Location of next intersection found, in whichever direction is currently 'forward'
        edge_intersects       - Whether or not the ray cast from the current loc to the next loc intersected the source mesh
        target_val            - The value this iteration of update_bf_matrix would set `brick_freq_matrix[x0][y0][z0]` to (ignoring whatever the value started at based on previous iterations)
    """
    point = coord_matrix[x0][y0][z0]
    point_inside, edge_intersects, intersections, next_intersection_loc, first_intersection, last_intersection = ray_obj_intersections(scn, point, ray, mini_dist, edge_len, source, use_normals, insideness_ray_cast_dir, brick_shell)

    target_val = 0
    if point_inside and brick_freq_matrix[x0][y0][z0] == 0:
        # define brick as inside shell
        brick_freq_matrix[x0][y0][z0] = -1
        target_val = -1
    if edge_intersects:
        if (brick_shell in ("INSIDE", "CONSISTENT") and point_inside) or (brick_shell == "OUTSIDE" and not point_inside):
            target_val = 1
            # define brick as part of shell
            brick_freq_matrix[x0][y0][z0] = 1
            # set or update nearest face to brick
            if type(face_idx_matrix[x0][y0][z0]) != dict or face_idx_matrix[x0][y0][z0]["dist"] > first_intersection["dist"]:
                face_idx_matrix[x0][y0][z0] = first_intersection
        else:  # EQUIVALENT TO: if (brick_shell in ("INSIDE", "CONSISTENT") and not point_inside) or (brick_shell == "OUTSIDE" and point_inside):
            target_val = 0
            try:
                # define brick as part of shell
                brick_freq_matrix[x1][y1][z1] = 1
            except IndexError:
                return -1, None, True, target_val
            # set or update nearest face to brick
            if type(face_idx_matrix[x1][y1][z1]) != dict or face_idx_matrix[x1][y1][z1]["dist"] > last_intersection["dist"]:
                face_idx_matrix[x1][y1][z1] = last_intersection

    return intersections, next_intersection_loc, edge_intersects, target_val


def is_internal(brick_d, shell_depth=1):
    """ check if brick entry in bricksdict is internal """
    val = brick_d["val"]
    return (0 < val < 1 - (shell_depth - 1) / 100) or val == -1


def add_column_supports(bricksdict, keys, thickness, step):
    """ update bricksdict internal entries to draw columns
    bricksdict -- dictionary with brick information at each lattice coordinate
    keys       -- keys to test in bricksdict
    thickness  -- thickness of the columns
    step       -- distance between columns
    """
    step = step + thickness
    for key in keys:
        brick_d = bricksdict[key]
        if not is_internal(brick_d):
            continue
        x,y,z = get_dict_loc(bricksdict, key)
        if (x % step < thickness and
            y % step < thickness):
            brick_d["draw"] = True


def add_lattice_supports(bricksdict, keys, step, height, alternate_xy):
    """ update bricksdict internal entries to draw lattice supports
    bricksdict  -- dictionary with brick information at each lattice coordinate
    keys        -- keys to test in bricksdict
    step        -- distance between lattice supports
    alternate_xy -- alternate x-beams and y-beams for each Z-axis level
    """
    for key in keys:
        brick_d = bricksdict[key]
        if not is_internal(brick_d):
            continue
        x,y,z = get_dict_loc(bricksdict, key)
        z0 = (floor(z / height) if alternate_xy else z) % 2
        if x % step == 0 and (not alternate_xy or z0 == 0):
            brick_d["draw"] = True
        elif y % step == 0 and (not alternate_xy or z0 == 1):
            brick_d["draw"] = True


def update_internal(bricksdict, cm, keys, clear_existing=False):
    """ update bricksdict internal entries
    cm            -- active cmlist object
    bricksdict    -- dictionary with brick information at each lattice coordinate
    keys          -- keys to test in bricksdict
    clear_existing -- set draw for all internal bricks to False before adding supports
    """
    # clear extisting internal structure
    if clear_existing:
        # set all bricks as unmerged
        split_bricks(bricksdict, cm.zstep, keys)
        # clear internal
        for k in keys:
            if is_internal(bricksdict[k], shell_depth=cm.last_shell_thickness):
                bricksdict[k]["draw"] = False
    # Draw column supports
    if cm.internal_supports == "COLUMNS":
        add_column_supports(bricksdict, keys, cm.col_thickness, cm.col_step)
    # draw lattice supports
    elif cm.internal_supports == "LATTICE":
        add_lattice_supports(bricksdict, keys, cm.lattice_step, cm.lattice_height, cm.alternate_xy)


def get_brick_matrix(source, face_idx_matrix, coord_matrix, brick_shell, axes="xyz", print_status=True, cursor_status=False):
    """ returns new brick_freq_matrix """
    scn, cm, _ = get_active_context_info()
    brick_freq_matrix = deepcopy(face_idx_matrix)
    axes = axes.lower()
    dist = coord_matrix[1][1][1] - coord_matrix[0][0][0]
    casts_in_multiple_dirs = cm.insideness_ray_cast_dir in ("HIGH_EFFICIENCY", "XYZ")
    negative_inf = Vector((-inf, -inf, -inf))
    # runs update functions only once
    use_normals = cm.use_normals
    insideness_ray_cast_dir = cm.insideness_ray_cast_dir
    # initialize Matrix sizes
    bfm_dim = [
        len(brick_freq_matrix),
        len(brick_freq_matrix[0]),
        len(brick_freq_matrix[0][0]),
    ]

    # initialize values used for printing status
    denom = (len(brick_freq_matrix[0][0]) + len(brick_freq_matrix[0]) + len(brick_freq_matrix))/100
    if cursor_status:
        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)

    def print_cur_status(percentStart, num0, denom0, lastPercent):
        # print status to terminal
        percent = percentStart + (len(brick_freq_matrix) / denom * (num0 / (denom0 - 1))) / 100
        update_progress_bars(percent, 0, "Shell", print_status, cursor_status)
        return percent

    percent0 = 0
    if "x" in axes:
        x_ray = coord_matrix[1][0][0] - coord_matrix[0][0][0]
        x_edge_len = x_ray.length
        x_mini_dist = Vector((0.00015, 0.0, 0.0))
        for z in range(bfm_dim[2]):
            # print status to terminal
            percent0 = print_cur_status(0, z, bfm_dim[2], percent0)
            for y in range(bfm_dim[1]):
                next_intersection_loc = negative_inf
                i = 1
                for x in range(bfm_dim[0]):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i >= 2 and casts_in_multiple_dirs and coord_matrix[x][y][z].x + dist.x + x_mini_dist.x < next_intersection_loc.x:
                        brick_freq_matrix[x][y][z] = val
                        continue
                    # cast rays and update brick_freq_matrix
                    intersections, next_intersection_loc, edge_intersects, target_val = update_bf_matrix(scn, x, y, z, coord_matrix, x_ray, x_edge_len, face_idx_matrix, brick_freq_matrix, brick_shell, source, x+1, y, z, x_mini_dist, use_normals, insideness_ray_cast_dir)
                    i = 0 if edge_intersects else (i + 1)
                    val = target_val
                    if intersections == 0:
                        break

    percent1 = percent0
    if "y" in axes:
        y_ray = coord_matrix[0][1][0] - coord_matrix[0][0][0]
        y_edge_len = y_ray.length
        y_mini_dist = Vector((0.0, 0.00015, 0.0))
        for z in range(bfm_dim[2]):
            # print status to terminal
            percent1 = print_cur_status(percent0, z, bfm_dim[2], percent1)
            for x in range(bfm_dim[0]):
                next_intersection_loc = negative_inf
                i = 1
                for y in range(bfm_dim[1]):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i >= 2 and casts_in_multiple_dirs and coord_matrix[x][y][z].y + dist.y + y_mini_dist.y < next_intersection_loc.y:
                        if brick_freq_matrix[x][y][z] == 0:
                            brick_freq_matrix[x][y][z] = val
                        if brick_freq_matrix[x][y][z] == val:
                            continue
                    # cast rays and update brick_freq_matrix
                    intersections, next_intersection_loc, edge_intersects, target_val = update_bf_matrix(scn, x, y, z, coord_matrix, y_ray, y_edge_len, face_idx_matrix, brick_freq_matrix, brick_shell, source, x, y+1, z, y_mini_dist, use_normals, insideness_ray_cast_dir)
                    i = 0 if edge_intersects else (i + 1)
                    val = target_val
                    if intersections == 0:
                        break

    percent2 = percent1
    if "z" in axes:
        z_ray = coord_matrix[0][0][1] - coord_matrix[0][0][0]
        z_edge_len = z_ray.length
        z_mini_dist = Vector((0.0, 0.0, 0.00015))
        for x in range(bfm_dim[0]):
            # print status to terminal
            percent2 = print_cur_status(percent1, x, bfm_dim[0], percent2)
            for y in range(bfm_dim[1]):
                next_intersection_loc = negative_inf
                i = 1
                for z in range(bfm_dim[2]):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i >= 2 and casts_in_multiple_dirs and coord_matrix[x][y][z].z + dist.z + z_mini_dist.z < next_intersection_loc.z:
                        if brick_freq_matrix[x][y][z] == 0:
                            brick_freq_matrix[x][y][z] = val
                        if brick_freq_matrix[x][y][z] == val:
                            continue
                    # cast rays and update brick_freq_matrix
                    intersections, next_intersection_loc, edge_intersects, target_val = update_bf_matrix(scn, x, y, z, coord_matrix, z_ray, z_edge_len, face_idx_matrix, brick_freq_matrix, brick_shell, source, x, y, z+1, z_mini_dist, use_normals, insideness_ray_cast_dir)
                    i = 0 if edge_intersects else (i + 1)
                    val = target_val
                    if intersections == 0:
                        break

    # mark inside freqs as internal (-1) and outside next to outsides for removal
    adjust_bfm(brick_freq_matrix, cm.mat_shell_depth, calc_internals=cm.calc_internals, remove_bad_internals=use_normals, face_idx_matrix=face_idx_matrix, axes=axes)

    # print status to terminal
    update_progress_bars(1, 0, "Shell", print_status, cursor_status, end=True)

    return brick_freq_matrix


def get_brick_matrix_smoke(cm, source, face_idx_matrix, brick_shell, source_details, print_status=True, cursor_status=False):
    # source = cm.source_obj
    density_grid, flame_grid, color_grid, domain_res, max_res, adapt, adapt_min, adapt_max = get_smoke_info(source)
    brick_freq_matrix = deepcopy(face_idx_matrix)
    color_matrix = deepcopy(face_idx_matrix)
    old_percent = 0
    brightness = Vector([(cm.smoke_brightness - 1) / 5]*3)
    sat_mat = get_saturation_matrix(cm.smoke_saturation)
    quality = cm.smoke_quality
    flame_intensity = cm.flame_intensity
    flame_color = cm.flame_color
    smoke_density = cm.smoke_density

    # get starting and ending idx
    if adapt:
        full_min = source_details.min
        full_max = source_details.max
        full_dist = full_max - full_min
        if 0 in full_dist:
            return brick_freq_matrix, color_matrix
        start_percent = vec_div(adapt_min - full_min, full_dist)
        end_percent   = vec_div(adapt_max - full_min, full_dist)
        s_idx = (len(face_idx_matrix) * start_percent.x, len(face_idx_matrix[0]) * start_percent.y, len(face_idx_matrix[0][0]) * start_percent.z)
        e_idx = (len(face_idx_matrix) * end_percent.x,   len(face_idx_matrix[0]) * end_percent.y,   len(face_idx_matrix[0][0]) * end_percent.z)
    else:
        s_idx = (0, 0, 0)
        e_idx = (len(face_idx_matrix), len(face_idx_matrix[0]), len(face_idx_matrix[0][0]))

    # get number of iterations from s_idx to e_idx for x, y, z
    d = Vector((e_idx[0] - s_idx[0], e_idx[1] - s_idx[1], e_idx[2] - s_idx[2]))
    # verify bounding box is larger than 0 in all directions
    if 0 in d:
        return brick_freq_matrix, color_matrix

    # get x/y/z distances
    xn0 = domain_res[0] / d.x
    yn0 = domain_res[1] / d.y
    zn0 = domain_res[2] / d.z
    denom = d.x

    # set up brick_freq_matrix values

    # iterate over x
    for x in range(int(s_idx[0]), int(e_idx[0])):
        # get x range
        x0 = x - s_idx[0]
        xn = [int(xn0 * x0), int(xn0 * (x0 + 1))]
        xn[1] += 1 if xn[1] == xn[0] else 0
        step_x = math.ceil((xn[1] - xn[0]) / quality)
        # print status to terminal
        old_percent = update_progress_bars(x / denom, old_percent, "Shell", print_status, cursor_status)

        # iterate over y
        for y in range(int(s_idx[1]), int(e_idx[1])):
            # get y range
            y0 = y - s_idx[1]
            yn = [int(yn0 * y0), int(yn0 * (y0 + 1))]
            yn[1] += 1 if yn[1] == yn[0] else 0
            step_y = math.ceil((yn[1] - yn[0]) / quality)

            # iterate over z
            for z in range(int(s_idx[2]), int(e_idx[2])):
                # get z range
                z0 = z - s_idx[2]
                zn = [int(zn0 * z0), int(zn0 * (z0 + 1))]
                zn[1] += 1 if zn[1] == zn[0] else 0
                step_z = math.ceil((zn[1] - zn[0]) / quality)

                # initialize accumulators
                d_acc = 0
                f_acc = 0
                cs_acc = Vector((0, 0, 0))
                cf_acc = 0
                ave_denom = 0

                # iterate through chunk of density grid near current brick locations
                for x1 in range(xn[0], xn[1], step_x):
                    for y1 in range(yn[0], yn[1], step_y):
                        for z1 in range(zn[0], zn[1], step_z):
                            cur_idx = (z1 * domain_res[1] + y1) * domain_res[0] + x1
                            _d = density_grid[cur_idx]
                            f = flame_grid[cur_idx]
                            d_acc += _d
                            f_acc += f
                            cur_idx_ext = cur_idx * 4
                            cs_acc += _d * Vector((color_grid[cur_idx_ext], color_grid[cur_idx_ext + 1], color_grid[cur_idx_ext + 2]))
                            cf_acc += f ** 2
                            ave_denom += 1

                # multiply by flame properties
                cf_acc *= flame_intensity * Vector(flame_color)

                # get acc averages
                d_ave = d_acc / ave_denom
                f_ave = f_acc / ave_denom
                cs_ave = cs_acc / (ave_denom * (d_ave if d_ave != 0 else 1))
                cf_ave = cf_acc / (ave_denom * (f_ave if f_ave != 0 else 1))

                # get final color values
                c_ave = (cs_ave + cf_ave)
                alpha = d_ave + f_ave

                # add brightness
                c_ave += brightness

                # add saturation
                c_ave = mathutils_mult(c_ave, sat_mat)

                # store to matrices
                brick_freq_matrix[x][y][z] = 0 if alpha < (1 - smoke_density) else 1
                color_matrix[x][y][z] = list(c_ave) + [alpha]


    # mark inside freqs as internal (-1) and outside next to outsides for removal
    adjust_bfm(brick_freq_matrix, cm.mat_shell_depth, calc_internals=cm.calc_internals)  # REMOVED: , axes="")

    # end progress bar
    update_progress_bars(1, 0, "Shell", print_status, cursor_status, end=True)

    return brick_freq_matrix, color_matrix


def adjust_bfm(brick_freq_matrix, mat_shell_depth, calc_internals=True, remove_bad_internals=False, face_idx_matrix=None, axes="xyz"):
    """ adjust brick_freq_matrix values """
    shell_vals = []
    bfm_dim = [
        len(brick_freq_matrix),
        len(brick_freq_matrix[0]),
        len(brick_freq_matrix[0][0]),
    ]

    # if generating shell outside mesh with less than three axes
    if axes != "xyz":
        for x in range(bfm_dim[0]):
            for y in range(bfm_dim[1]):
                for z in range(bfm_dim[2]):
                    # if current location is inside (-1) and adjacent location is out of bounds, current location is shell (1)
                    if (brick_freq_matrix[x][y][z] == -1 and
                        (("z" not in axes and
                          (z in (0, bfm_dim[2]-1) or
                           brick_freq_matrix[x][y][z+1] == 0 or
                           brick_freq_matrix[x][y][z-1] == 0)) or
                         ("y" not in axes and
                          (y in (0, bfm_dim[1]-1) or
                           brick_freq_matrix[x][y+1][z] == 0 or
                           brick_freq_matrix[x][y-1][z] == 0)) or
                         ("x" not in axes and
                          (x in (0, bfm_dim[0]-1) or
                           brick_freq_matrix[x+1][y][z] == 0 or
                           brick_freq_matrix[x-1][y][z] == 0))
                      )):
                        brick_freq_matrix[x][y][z] = 1
                        # TODO: set face_idx_matrix value to nearest shell value using some sort of built in nearest poly to point function

    # iterate through all values except boundaries in case internals intersect outside
    if remove_bad_internals:
        for x in range(1, bfm_dim[0] - 1):
            for y in range(1, bfm_dim[1] - 1):
                for z in range(1, bfm_dim[2] - 1):
                    # If inside location (-1) intersects outside location (0), make it ouside (0)
                    if (brick_freq_matrix[x][y][z] == -1 and
                        (brick_freq_matrix[x+1][y][z] == 0 or
                         brick_freq_matrix[x-1][y][z] == 0 or
                         brick_freq_matrix[x][y+1][z] == 0 or
                         brick_freq_matrix[x][y-1][z] == 0 or
                         brick_freq_matrix[x][y][z+1] == 0 or
                         brick_freq_matrix[x][y][z-1] == 0)):
                        brick_freq_matrix[x][y][z] = 0

    trash_vals = [0] if calc_internals else [0, -1]
    all_shell_vals = []
    # iterate through all values
    for x in range(bfm_dim[0]):
        for y in range(bfm_dim[1]):
            for z in range(bfm_dim[2]):
                # mark outside and unused inside brick_freq_matrix values for removal
                if brick_freq_matrix[x][y][z] in trash_vals:
                    brick_freq_matrix[x][y][z] = None
                # get shell values for next calc
                elif calc_internals and brick_freq_matrix[x][y][z] == 1:
                    all_shell_vals.append((x, y, z))

    if not calc_internals:
        return

    # iterate through all shell values
    for x, y, z in all_shell_vals:
        # If shell location (1) does not intersect outside/trashed/nonexistent location (0, None), make it inside (-1)
        if brick_freq_matrix[x][y][z] == 1:
            try:
                surrounded = all((
                    brick_freq_matrix[x+1][y][z],
                    brick_freq_matrix[x-1][y][z],
                    brick_freq_matrix[x][y+1][z],
                    brick_freq_matrix[x][y-1][z],
                    brick_freq_matrix[x][y][z+1],
                    brick_freq_matrix[x][y][z-1],
                ))
            except IndexError:
                # in this case, an adjacent loc is nonexistent, therefore the current loc cannot be surrounded
                surrounded = False
            if surrounded:
                brick_freq_matrix[x][y][z] = -1
                if face_idx_matrix:
                    face_idx_matrix[x][y][z] = 0
            else:
                shell_vals.append((x, y, z))


    # Update internals
    j = 1
    set_nf = True
    for i in range(50):
        j = j - 0.01
        got_one = False
        new_shell_vals = []
        if set_nf:
            set_nf = is_mat_shell_val(j, mat_shell_depth)
        for x, y, z in shell_vals:
            idxs_to_check = get_neighbor_idxs(x, y, z)
            for idx in idxs_to_check:
                try:
                    cur_val = brick_freq_matrix[idx[0]][idx[1]][idx[2]]
                except IndexError:
                    continue
                if cur_val == -1:
                    new_shell_vals.append(idx)
                    brick_freq_matrix[idx[0]][idx[1]][idx[2]] = j
                    if face_idx_matrix and set_nf: face_idx_matrix[idx[0]][idx[1]][idx[2]] = face_idx_matrix[x][y][z]
                    got_one = True
        if not got_one:
            break
        shell_vals = new_shell_vals


def linear_is_hole(brick_freq_matrix, visited, starting_loc):
    is_hole = True
    next_locs = {starting_loc}
    while len(next_locs) > 0:
        x, y, z = next_locs.pop()
        # base case (no longer inside brick_freq_matrix)
        if not (0 <= x < len(brick_freq_matrix) and 0 <= y < len(brick_freq_matrix[0]) and 0 <= z < len(brick_freq_matrix[0][0])):
            is_hole = False
            continue
        # continue if visited
        if visited[x][y][z]:
            continue
        else:
            visited[x][y][z] = 1
        # continue if no longer on outside loc
        if brick_freq_matrix[x][y][z]!= 0:
            continue
        # add new neighbor locs to next_locs
        next_locs |= get_neighbor_idxs(x, y, z)
    return is_hole


def linear_fill_hole(brick_freq_matrix, starting_loc):
    next_locs = {starting_loc}
    while len(next_locs) > 0:
        x, y, z = next_locs.pop()
        # base case
        if brick_freq_matrix[x][y][z] != 0:
            continue
        # set as internal
        brick_freq_matrix[x][y][z] = -1
        # add new neighbor locs to next_locs
        next_locs |= get_neighbor_idxs(x, y, z)


def get_neighbor_idxs(x, y, z):
    return {
        (x+1, y, z),
        (x-1, y, z),
        (x, y+1, z),
        (x, y-1, z),
        (x, y, z+1),
        (x, y, z-1)
    }


def get_threshold(cm):
    """ returns threshold (draw bricks if returned val >= threshold) """
    return 1.01 - (cm.shell_thickness / 100)


global_x_dir = Vector((1, 0, 0))
global_x_mini_dist = Vector((0.001, 0, 0))
def should_omit_brick(co:Vector, bool_list:CollectionProperty, use_normals:bool=False, insideness_ray_cast_dir:str="XYZ"):
    scn = bpy.context.scene
    omit_brick = False
    for bool in bool_list:
        if bool.type == "OBJECT":
            if bool.object_dup is None:
                continue
            (1, 0, 0)
            # check if brick inside bool object
            is_inside = ray_obj_intersections(scn, co, global_x_dir, global_x_mini_dist, 1, bool.object_dup.evaluated_get(bpy.context.view_layer.depsgraph), use_normals, insideness_ray_cast_dir)[0]
            # omit brick if inside bool object
            if is_inside:
                omit_brick = True
                break
        elif bool.type == "MODEL":
            cm = scn.cmlist.get(bool.model_name)
    return omit_brick


def create_bricksdict_entry(name:str, loc:list, val:float=0, draw:bool=False, co:tuple=(0, 0, 0), omitted:bool=False, near_face:int=None, near_intersection:str=None, near_normal:tuple=None, rgba:tuple=None, mat_name:str="", custom_mat_name:bool=False, parent:str=None, size:list=None, attempted_merge:bool=False, available_for_merge:bool=False, top_exposed:bool=None, bot_exposed:bool=None, obscures:list=[False]*6, b_type:str=None, flipped:bool=False, rotated:bool=False, created_from:str=None):
    """
    create an entry in the dictionary of brick locations

    Keyword Arguments:
    name                -- name of the brick object
    loc                 -- str_to_list(key)
    val                 -- location of brick in model (0: outside of model, 0.00-1.00: number of bricks away from shell / 100, 1: on shell)
    draw                -- draw the brick in 3D space
    co                  -- 1x1 brick centered at this location
    omitted             -- brick should be omitted due to a bool
    near_face           -- index of nearest face intersection with source mesh
    near_intersection   -- coordinate location of nearest intersection with source mesh
    near_normal         -- normal of the nearest face intersection
    rgba                -- [red, green, blue, alpha] values of brick color
    mat_name            -- name of material attributed to bricks at this location
    custom_mat_name     -- mat_name was set with 'Change Material' customization tool
    parent              -- key into brick dictionary with information about the parent brick merged with this one
    size                -- 3D size of FULL brick (e.g. standard 2x4 brick -> [2, 4, 3])
    attempted_merge     -- successful attempt has been made in make_bricks function to merge this brick with nearby bricks
    available_for_merge -- brick needs to be merged
    top_exposed         -- top of FULL brick is visible to camera
    bot_exposed         -- bottom of FULL brick is visible to camera
    obscures            -- obscures neighboring locations [+z, -z, +x, -x, +y, -y]
    type                -- type of brick
    flipped             -- brick is flipped over non-mirrored axis
    rotated             -- brick is rotated 90 degrees about the Z axis
    created_from        -- key of brick this brick was created from in draw_adjacent

    """
    return {
        "name": name,
        "loc": loc,
        "val": val,
        "draw": draw,
        "co": co,
        "omitted": omitted,
        "near_face": near_face,
        "near_intersection": near_intersection,
        "near_normal": near_normal,
        "rgba": rgba,
        "mat_name": mat_name,
        "custom_mat_name": custom_mat_name,
        "parent": parent,
        "size": size,
        "attempted_merge": attempted_merge,
        "available_for_merge": available_for_merge,
        "top_exposed": top_exposed,
        "bot_exposed": bot_exposed,
        "obscures": obscures,
        "type": b_type,
        "flipped": flipped,
        "rotated": rotated,
        "created_from": created_from,
    }

@timed_call()
def make_bricksdict(source, source_details, brick_scale, grid_offset, use_absolute_grid=False, cursor_status=False):
    """ make dictionary with brick information at each coordinate of lattice surrounding source
    source            -- source object to construct lattice around
    source_details    -- object details with subattributes for distance and midpoint of x, y, z axes
    brick_scale       -- scale of bricks
    grid_offset       -- offset of lattice grid for brick generation (0.5 = half the brick scale)
    use_absolute_grid -- use a fixed lattice grid for brick generation based on global coordinates
    cursor_status     -- update mouse cursor with status of matrix creation
    """
    scn, cm, n = get_active_context_info()
    # get lattice bmesh
    print("\ngenerating blueprint...")
    l_scale = source_details.dist
    vec_half = Vector((0.5, 0.5, 0.5))
    vec_ones = Vector((1, 1, 1))
    # get offset for lattice
    offset = Vector(source_details.mid)
    if source.parent:
        offset -= source.parent.location
    # shift offset to absolute grid location (also ensures lattice surrounds object
    if use_absolute_grid:
        offset -= vec_remainder(offset, brick_scale)
    # else:
    #     offset -= brick_scale
    # shift offset by grid_offset parameter
    if any(grid_offset):
        grid_offset = vec_remainder(grid_offset + vec_half, vec_ones) - vec_half  # modulo -1 to 1 range to -0.5 to 0.5
        offset += vec_mult(brick_scale, grid_offset)
    # get coordinate list from intersections of edges with faces
    coord_matrix = generate_lattice(brick_scale, l_scale, offset, extra_res=1)
    if len(coord_matrix) == 0:
        coord_matrix.append(source_details.mid)
    # set calculation_axes
    calculation_axes = cm.calculation_axes if cm.brick_shell == "OUTSIDE" else "XYZ"
    # set up face_idx_matrix and brick_freq_matrix
    face_idx_matrix = np.zeros((len(coord_matrix), len(coord_matrix[0]), len(coord_matrix[0][0])), dtype=int).tolist()
    if cm.is_smoke:
        brick_freq_matrix, smoke_colors = get_brick_matrix_smoke(cm, source, face_idx_matrix, cm.brick_shell, source_details, cursor_status=cursor_status)
    else:
        brick_freq_matrix = get_brick_matrix(source, face_idx_matrix, coord_matrix, cm.brick_shell, axes=calculation_axes, cursor_status=cursor_status)
        smoke_colors = None
    # initialize active keys
    cm.active_key = (-1, -1, -1)

    # create bricks dictionary with brick_freq_matrix values
    bricksdict = {}
    draw_threshold = get_threshold(cm)
    brick_type = cm.brick_type  # prevents cm.brick_type update function from running over and over in for loop
    bool_list = cm.booleans
    bool_dupes = update_bool_dupes(cm)
    uv_image = cm.uv_image
    build_is_dirty = cm.build_is_dirty
    drawn_keys = []
    source_mats = cm.material_type == "SOURCE"
    noOffset = vec_round(offset, precision=5) == Vector((0, 0, 0))
    for x in range(len(coord_matrix)):
        for y in range(len(coord_matrix[0])):
            for z in range(len(coord_matrix[0][0])):
                # skip brick_freq_matrix values set to None
                if brick_freq_matrix[x][y][z] is None:
                    continue

                # initialize variables
                b_loc = [x, y, z]
                b_key = list_to_str(b_loc)

                co = coord_matrix[x][y][z].to_tuple() if noOffset else (coord_matrix[x][y][z] - source_details.mid).to_tuple()

                # get material from nearest face intersection point
                nf = face_idx_matrix[x][y][z]["idx"] if type(face_idx_matrix[x][y][z]) == dict else None
                ni = face_idx_matrix[x][y][z]["loc"].to_tuple() if type(face_idx_matrix[x][y][z]) == dict else None
                nn = face_idx_matrix[x][y][z]["normal"] if type(face_idx_matrix[x][y][z]) == dict else None
                val = round(brick_freq_matrix[x][y][z], 2)
                omitted = should_omit_brick(Vector(co), bool_list)
                norm_dir = get_normal_direction(nn, slopes=True)
                b_type = get_brick_type(brick_type)
                flipped, rotated = get_flip_rot("" if norm_dir is None else norm_dir[1:])
                if smoke_colors:
                    rgba = smoke_colors[x][y][z]
                elif source_mats:
                    rgba = get_uv_pixel_color(source, nf, ni if ni is None else Vector(ni), uv_image)
                else:
                    rgba = (0, 0, 0, 1)
                # create bricksdict entry for current brick
                bricksdict[b_key] = create_bricksdict_entry(
                    name= "Bricker_%(n)s__%(b_key)s" % locals(),
                    loc= b_loc,
                    val= val,
                    co= co,
                    near_face= nf,
                    near_intersection= ni,
                    near_normal= norm_dir,
                    omitted= omitted,
                    rgba= rgba,
                    # mat_name= "",  # defined in 'update_materials' function
                    # obscures= [brick_freq_matrix[x][y][z] != 0]*6,
                    b_type= b_type,
                    flipped= flipped,
                    rotated= rotated,
                )
                bricksdict[b_key]["draw"] = should_draw_brick(bricksdict[b_key], draw_threshold)
                if build_is_dirty and bricksdict[b_key]["draw"]:
                    drawn_keys.append(b_key)
    # delete all of the bool dupes
    delete(bool_dupes)
    # return list of created Brick objects
    return bricksdict
