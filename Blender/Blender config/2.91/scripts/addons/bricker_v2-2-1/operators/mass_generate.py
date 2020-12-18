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
import time
import os

# Blender imports
import bpy
from bpy.props import *

# Module imports
from ..lib.caches import *
from ..lib.undo_stack import *
from ..lib.mat_properties import *
from ..functions import *
from ..functions.property_callbacks import *


class BRICKER_OT_mass_generate(bpy.types.Operator):
    """Generate all sizes and colors for given brick type"""
    bl_idname = "bricker.mass_generate"
    bl_label = "Mass Generate"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    # @classmethod
    # def poll(self, context):
    #     return True

    def execute(self, context):
        try:
            # ensure abs mats installed
            if not brick_materials_imported():
                bpy.ops.abs.append_materials(include_undefined=True)

            # initialize new temp cmlist entry
            bpy.ops.bricker.cm_list_action(action="ADD")
            scn, cm, n = get_active_context_info()
            legal_bricks = get_legal_bricks()
            b_type, brick_size = get_brick_type_and_size_from_part_num(legal_bricks, self.pt_number)
            # cm.brick_type = "BRICKS" if flat_brick_type(b_type) else "PLATES"
            cm.material_type = "SOURCE"
            cm.color_snap = "ABS"
            cm.matrix_is_dirty = False
            cm.zstep = 1 if flat_brick_type(b_type) else 3#get_zstep(cm)
            cm.last_legal_bricks_only = True

            # intialize brick info
            brick_dims = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)

            # initialize everything else
            bricksdict = dict()
            z0 = 0

            # initialize brick for each material name available
            problem_mat_names = {
                # "ABS Plastic Bright Light Orange",
                # "ABS Plastic Bright Light Yellow",
                # "ABS Plastic Chrome Silver",
                # "ABS Plastic Coral",
                # "ABS Plastic Dark Orange",
                "ABS Plastic Medium Nougat",
                # "ABS Plastic Metallic Gold",
                # "ABS Plastic Metallic Silver",
                # "ABS Plastic Pearl Dark Gray",
            }
            for mat_name in mat_properties.keys():
                z0 += 1
                for x in range(brick_size[0]):
                    for y in range(brick_size[1]):
                        for z in range(brick_size[2]):
                            loc = [x, y, z + z0]
                            key = list_to_str(loc)
                            co = [0, 0, brick_dims["height"] * z0]
                            bricksdict[key] = create_bricksdict_entry(
                                name= f"Bricker_{b_type.lower()}",
                                loc= loc,
                                parent= "self" if not any((x, y, z)) else list_to_str([0, 0, z0]),
                                size= brick_size,
                                val= 1,
                                draw= True,
                                co= co,
                                mat_name= mat_name,
                                custom_mat_name= True,
                                b_type= b_type,
                            )
            cache_bricks_dict("CREATE", cm, bricksdict)
            bpy.ops.bricker.export_ldraw(build_order="LAYERS", filepath=self.filepath)
            bpy.ops.bricker.cm_list_action(action="REMOVE")
            return{"FINISHED"}
        except:
            bricker_handle_exception()
            return{"CANCELLED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class variables

    pt_number = StringProperty(
        name="Part Number",
    )
    filepath = StringProperty(
        name="Filepath",
        subtype="FILE_PATH",
        default="/Users/cgear13/Desktop/mass_generate.ldr",
    )

    ################################################
