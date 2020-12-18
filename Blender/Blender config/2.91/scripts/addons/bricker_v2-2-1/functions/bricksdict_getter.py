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
from mathutils import Vector, Matrix

# Module imports
# from .bevel_bricks import *
from .bricksdict import *
from .brick.bricks import get_brick_dimensions
from .common import *
from .general import *
# from .cmlist_utils import *
# from .logo_obj import *
# from .make_bricks_point_cloud import *
# from .make_bricks import *
# from .model_info import set_model_info
# from .smoke_cache import *
# from .transform_data import *


def get_bricksdict_for_model(cm, source, source_details, action, cur_frame, brick_scale, bricksdict, keys, redrawing, update_cursor):
    if bricksdict is None:
        # load bricksdict from cache
        bricksdict = get_bricksdict(cm, d_type=action, cur_frame=cur_frame)
        loaded_from_cache = bricksdict is not None
        # if not loaded, new bricksdict must be created
        if not loaded_from_cache:
            # multiply brick_scale by offset distance
            brick_scale2 = brick_scale if cm.brick_type != "CUSTOM" else vec_mult(brick_scale, Vector(cm.dist_offset))
            # create new bricksdict
            bricksdict = make_bricksdict(source, source_details, brick_scale2, cm.grid_offset, cm.use_absolute_grid_anim if cm.use_animation else cm.use_absolute_grid, cursor_status=update_cursor)
    else:
        loaded_from_cache = True
    if keys == "ALL": keys = set(bricksdict.keys())
    # reset all values for certain keys in bricksdict dictionaries
    if cm.build_is_dirty and loaded_from_cache and not redrawing:
        draw_threshold = get_threshold(cm)
        update_internal_drawing = cm.last_shell_thickness != cm.shell_thickness
        for kk, brick_d in bricksdict.items():
            kk0 = next(iter(keys))
            if kk in keys:
                brick_d["size"] = None
                brick_d["parent"] = None
                brick_d["top_exposed"] = None
                brick_d["bot_exposed"] = None
                if update_internal_drawing:
                    brick_d["draw"] = should_draw_brick(brick_d, draw_threshold)
            else:
                # don't merge bricks not in 'keys'
                brick_d["attempted_merge"] = True
    if (not loaded_from_cache or cm.internal_is_dirty) and check_if_internals_exist(cm):
        update_internal(bricksdict, cm, keys, clear_existing=loaded_from_cache)
        cm.build_is_dirty = True
    # update materials in bricksdict
    if cm.material_type != "NONE" and (cm.material_is_dirty or cm.matrix_is_dirty or cm.anim_is_dirty):
        bricksdict = update_materials(bricksdict, source, keys, cur_frame=cur_frame, action=action)
    return bricksdict, brick_scale


def get_arguments_for_bricksdict(cm, source=None, dimensions=None, brick_size=[1, 1, 3]):
    """ returns arguments for make_bricksdict function """
    source = source or cm.source_obj
    split_model = cm.split_model
    if dimensions is None:
        dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
    for has_custom_obj, custom_obj, data_attr in ((cm.has_custom_obj1, cm.custom_object1, "custom_mesh1"), (cm.has_custom_obj2, cm.custom_object2, "custom_mesh2"), (cm.has_custom_obj3, cm.custom_object3, "custom_mesh3")):
        if (data_attr == "custom_mesh1" and cm.brick_type == "CUSTOM") or has_custom_obj:
            scn = bpy.context.scene
            # duplicate custom object
            # TODO: remove this object on delete action
            custom_obj_name = custom_obj.name + "__dup__"
            m = new_mesh_from_object(custom_obj)
            custom_obj0 = bpy.data.objects.get(custom_obj_name)
            if custom_obj0 is not None:
                custom_obj0.data = m
            else:
                custom_obj0 = bpy.data.objects.new(custom_obj_name, m)
            # remove UV layers if not split (for massive performance improvement when combining meshes in `draw_brick` fn)
            if b280() and not split_model:
                for uv_layer in m.uv_layers:
                    m.uv_layers.remove(uv_layer)
            # apply transformation to custom object
            safe_link(custom_obj0)
            apply_transform(custom_obj0)
            depsgraph_update()
            safe_unlink(custom_obj0)
            # get custom object details
            cur_custom_obj_details = bounds(custom_obj0)
            # set brick scale
            scale = cm.brick_height / cur_custom_obj_details.dist.z
            brick_scale = cur_custom_obj_details.dist * scale + Vector([dimensions["gap"]] * 3)
            # get transformation matrices
            t_mat = Matrix.Translation(-cur_custom_obj_details.mid)
            max_dist = max(cur_custom_obj_details.dist)
            s_mat_x = Matrix.Scale((brick_scale.x - dimensions["gap"]) / cur_custom_obj_details.dist.x, 4, Vector((1, 0, 0)))
            s_mat_y = Matrix.Scale((brick_scale.y - dimensions["gap"]) / cur_custom_obj_details.dist.y, 4, Vector((0, 1, 0)))
            s_mat_z = Matrix.Scale((brick_scale.z - dimensions["gap"]) / cur_custom_obj_details.dist.z, 4, Vector((0, 0, 1)))
            # apply transformation to custom object dup mesh
            custom_obj0.data.transform(t_mat)
            custom_obj0.data.transform(mathutils_mult(s_mat_x, s_mat_y, s_mat_z))
            # center mesh origin
            center_mesh_origin(custom_obj0.data, dimensions, brick_size)
            # store fresh data to custom_mesh1/2/3 variable
            setattr(cm, data_attr, custom_obj0.data)
    if cm.brick_type != "CUSTOM":
        brick_scale = Vector((
            dimensions["width"] + dimensions["gap"],
            dimensions["width"] + dimensions["gap"],
            dimensions["height"]+ dimensions["gap"],
        ))
    return brick_scale
