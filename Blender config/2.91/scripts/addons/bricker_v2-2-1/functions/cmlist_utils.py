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
from operator import itemgetter
import json

# Blender imports
import bpy
from bpy.props import *
from mathutils import Vector, Color

# Module imports
from .common import *

# Conditional imports
if b280():
    from bpy.types import Material, Image, Object, Mesh, Collection
    # NOTE: 'Meshe' used because the plural of Mesh is 'Meshes'
    types = {Material:"Material", Image:"Image", Object:"Object", Mesh:"Meshe", Collection:"Collection"}
else:
    from bpy.types import Material, Image, Object, Mesh, Group
    types = {Material:"Material", Image:"Image", Object:"Object", Mesh:"Meshe", Group:"Group"}


def get_data_blocks_from_props(cm, skip_keys=None):
    if skip_keys is None:
        skip_keys = []
    data_blocks = set()

    for item in get_annotations(cm):
        if not item.islower() or item in skip_keys:
            continue
        try:
            item_prop = getattr(cm, item)
        except:
            continue
        item_type = type(item_prop)
        if item_type in types.keys():
            data_blocks.add(item_prop)
    return data_blocks


# def dump_cm_props(cm, skip_keys=None):
#     if skip_keys is None:
#         skip_keys = []
#     prop_dict = {}
#     pointer_dict = {}
#
#     for item in get_annotations(cm):
#         if not item.islower() or item in skip_keys:
#             continue
#         try:
#             item_prop = getattr(cm, item)
#         except:
#             continue
#         item_type = type(item_prop)
#         if item_type in types.keys():
#             pointer_dict[item] = {"name":item_prop.name, "type":types[item_type]}
#             continue
#         if item_type in (Vector, Color):
#             item_prop = tuple(item_prop)
#         prop_dict[item] = item_prop
#     return prop_dict, pointer_dict


# def load_cm_props(cm, prop_dict, pointer_dict):
#     for item in prop_dict:
#         setattr(cm, item, prop_dict[item])
#     for item in pointer_dict:
#         name = pointer_dict[item]["name"]
#         typ = pointer_dict[item]["type"]
#         data = getattr(bpy.data, typ.lower() + "s")[name]
#         setattr(cm, item, data)

def match_properties(cm_to, cm_from, full_match=False):
    scn = bpy.context.scene
    # get list of properties that should not be matched
    if not full_match:
        props_to_match = [
            # ANIMATION SETTINGS
            "use_animation",
            "start_frame",
            "stop_frame",
            "step_frame",
            # BASIC MODEL SETTINGS
            "brick_height",
            "gap",
            "split_model",
            "random_loc",
            "random_rot",
            "shell_thickness",
            # MERGE SETTINGS
            "merge_type",
            "merge_seed",
            "align_bricks",
            "offset_brick_layers",
            # SMOKE SETTINGS
            "smoke_density",
            "smoke_quality",
            "smoke_brightness",
            "smoke_saturation",
            "flame_color",
            "flame_intensity",
            # BRICK TYPE SETTINGS
            "brick_type",
            "max_width",
            "max_depth",
            "custom_object1",
            "custom_object2",
            "custom_object3",
            "dist_offset",
            # MATERIAL & COLOR SETTINGS
            "material_type",
            "custom_mat",
            "internal_mat",
            "mat_shell_depth",
            "merge_internals",
            "random_mat_seed",
            "use_uv_map",
            "uv_image",
            "color_snap",
            "color_depth",
            "blur_radius",
            "color_snap_specular",
            "color_snap_roughness",
            "color_snap_sss",
            "color_snap_sss_saturation",
            "color_snap_ior",
            "color_snap_transmission",
            "color_snap_displacement",
            "use_abs_template",
            "include_transparency",
            "transparent_weight",
            # BRICK DETAIL SETTINGS
            "stud_detail",
            "logo_type",
            "logo_resolution",
            "logo_decimate",
            "logo_object",
            "logo_scale",
            "logo_inset",
            "hidden_underside_detail",
            "exposed_underside_detail",
            "circle_verts",
            # BOOLEAN SETTINGS
            "booleans",
            # INTERNAL SUPPORTS SETTINGS
            "internal_supports",
            "lattice_step",
            "lattice_height",
            "alternate_xy",
            "col_thickness",
            "col_step",
            # ADVANCED SETTINGS
            "insideness_ray_cast_dir",
            "brick_shell",
            "calculation_axes",
            "use_normals",
            "grid_offset",
            "calc_internals",
            "use_local_orient",
            "instance_method",
        ]
        if not cm_from.bevel_added or not cm_to.bevel_added:
            props_to_match.append("bevel_width")
            props_to_match.append("bevel_segments")
            props_to_match.append("bevel_profile")
    # get all properties from cm_from
    cm_from_props = get_collection_props(cm_from)
    # remove properties that shouldn't be matched
    if not full_match:
        for k in list(cm_from_props.keys()):
            if k not in props_to_match:
                cm_from_props.pop(k)
    # match material properties for Random/ABS Plastic Snapping
    mat_obj_names_from = ["Bricker_{}_RANDOM_mats".format(cm_from.id), "Bricker_{}_ABS_mats".format(cm_from.id)]
    mat_obj_names_to   = ["Bricker_{}_RANDOM_mats".format(cm_to.id), "Bricker_{}_ABS_mats".format(cm_to.id)]
    for i in range(2):
        mat_obj_from = bpy.data.objects.get(mat_obj_names_from[i])
        mat_obj_to = bpy.data.objects.get(mat_obj_names_to[i])
        if mat_obj_from is None or mat_obj_to is None:
            continue
        mat_obj_to.data.materials.clear()
        for mat in mat_obj_from.data.materials:
            mat_obj_to.data.materials.append(mat)
    # match properties from 'cm_from' to 'cm_to'
    set_collection_props(cm_to, cm_from_props)
