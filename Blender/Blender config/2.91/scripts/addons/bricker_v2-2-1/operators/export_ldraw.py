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
import json
import math
import os
import time
import numpy as np

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import *

# Module imports
from ..functions import *


class BRICKER_OT_export_ldraw(Operator, ExportHelper):
    """Export active brick model to ldraw file"""
    bl_idname = "bricker.export_ldraw"
    bl_label = "Export LDR"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        try:
            self.write_ldraw_file(context)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        # get matrix for rotation of brick
        self.matrices = [
            " 0 0 -1 0 1 0  1 0  0",
            " 1 0  0 0 1 0  0 0  1",
            " 0 0  1 0 1 0 -1 0  0",
            "-1 0  0 0 1 0  0 0 -1"
        ]
        # get other vars
        self.legal_bricks = get_legal_bricks()
        self.abs_mat_properties = bpy.props.abs_mat_properties if hasattr(bpy.props, "abs_mat_properties") else None
        # initialize vars
        scn, cm, _ = get_active_context_info()
        self.trans_weight = cm.transparent_weight
        self.material_type = cm.material_type
        self.custom_mat = cm.custom_mat
        self.random_mat_seed = cm.random_mat_seed
        self.brick_height = cm.brick_height
        self.offset_brick_layers = cm.offset_brick_layers
        self.gap = cm.gap
        self.zstep = get_zstep(cm)
        self.brick_mats = get_brick_mats(cm)
        self.mat_shell_depth = cm.mat_shell_depth
        self.internal_mat = cm.internal_mat
        self.color_snap = cm.color_snap
        self.brick_materials_installed = brick_materials_installed()

    #############################################
    # ExportHelper properties

    filename_ext = ".ldr"
    filter_glob = StringProperty(
        default="*.ldr",
        options={"HIDDEN"},
    )
    # path_mode = path_reference_mode
    check_extension = True

    #############################################
    # class variables

    model_author = StringProperty(
        name="Author",
        description="Author name for the file's metadata",
        default="",
    )

    #############################################
    # class methods

    @timed_call()
    def write_ldraw_file(self, context):
        # open file for read and write
        self.filelines = list()
        # initialize vars
        scn, cm, n = get_active_context_info(context)
        blendfile_name = bpy.path.basename(context.blend_data.filepath)
        # iterate through models (if not animated, just executes once)
        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame) if cm.animated else [-1]:
            # write META commands
            self.filelines.append(f"0 FILE {blendfile_name}\n")
            self.filelines.append(f"0 {n}\n")
            self.filelines.append(f"0 Name: {n}\n")
            self.filelines.append("0 Unofficial model\n")
            self.filelines.append(f"0 Author: {self.model_author}\n")
            self.filelines.append("0 CustomBrick\n")
            bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=frame)
            if bricksdict is None:
                self.report({"ERROR"}, "The model's data is not cached – please update the model")
                return
            # get small offset for model to get close to Ldraw units
            offset = vec_conv(bricksdict[list(bricksdict.keys())[0]]["co"], int)
            offset.x = offset.x % 10
            offset.y = offset.z % 8
            offset.z = offset.y % 10
            # get dictionary of keys based on z value
            p_keys_dict = get_keys_dict(bricksdict, parents_only=True)
            sorted_z_vals = sorted(p_keys_dict.keys())

            # populate the filelines based on the build order method
            self.populate_filelines_basic(bricksdict, p_keys_dict, sorted_z_vals, offset)

            # add the ending line of the main file
            self.filelines.append("0 NOFILE\n")

            # close the file
            self.file = open(self.filepath, "w")
            self.file.writelines(self.filelines)
            self.file.close()
            self.report_export_status(cm, bricksdict)

    def populate_filelines_basic(self, bricksdict, p_keys_dict, sorted_z_vals, offset):
        """ populate filelines without step information """
        # remove 'NOFILE' line from the end of the intro lines
        self.filelines.pop()
        # grab all of the bricks and add them as a single step (remove step line at the end)
        flat_p_keys = set(item for z in p_keys_dict for item in p_keys_dict[z])
        self.add_build_step(bricksdict, p_keys_dict, flat_p_keys, offset, run_diff_update=False, max_step_size=inf)
        self.filelines.pop()

    def report_export_status(self, cm, bricksdict):
        # report the status of the export
        if not cm.last_legal_bricks_only:
            self.report({"WARNING"}, "Model may contain non-standard brick sizes. Enable 'Brick Types > Legal Bricks Only' to make bricks LDraw-compatible.")
        if self.abs_mat_properties is None and self.brick_materials_installed:
            self.report({"WARNING"}, "Materials may not have transferred successfully – please update to the latest version of 'ABS Plastic Materials'")
        else:
            self.report({"INFO"}, f"Ldraw file saved to '{self.filepath}'")
            # print num bricks exported
            num_bricks_exported = len(tuple(val for val in self.filelines if val.startswith("1")))
            total_bricks = len(get_parent_keys(bricksdict))
            print()
            print(f"{num_bricks_exported} / {total_bricks} bricks exported")
            # print num sub-steps exported
            num_steps_exported = len(tuple(val for val in self.filelines if val.startswith("0 ROTSTEP")))
            print(f"{num_steps_exported} steps exported")

    def add_build_step(self, bricksdict, p_keys_dict, keys, offset, run_diff_update=True, direction="UP", max_step_size=12):
        cur_model = self.filelines
        # remove keys in this step from p_keys_dict
        if run_diff_update:
            z_vals = [get_dict_loc(bricksdict, k1)[2] for k1 in keys]
            for z in z_vals:
                p_keys_dict[z].difference_update(keys)
        # iterate through keys
        sorted_keys = sorted(keys, key=lambda x: (get_dict_loc(bricksdict, x)[0], get_dict_loc(bricksdict, x)[1], get_dict_loc(bricksdict, x)[2]))
        step_starting_key = sorted_keys[0]
        for i, key in enumerate(sorted_keys):
            # break up this step up into roughly equivalent groups of up to 12 bricks (won't be split up into groups smaller than 7, which is max_step_size/2+1)
            if i > (max_step_size / 2) and i % math.ceil(len(sorted_keys) / round(len(sorted_keys) / max_step_size)) == 0:
                cur_model.append(self.get_step_line(direction))
            # write line to file for current brick
            brick_info_line = self.get_brick_info_line(bricksdict, key, offset)
            cur_model.append(brick_info_line)
        # add step info to end
        cur_model.append(self.get_step_line(direction))

    def get_brick_info_line(self, bricksdict, key, offset):
        # initialize brick info vars
        brick_d = bricksdict[key]
        size = brick_d["size"]
        typ = brick_d["type"]
        idx = self.get_brick_idx(brick_d, size, typ)
        matrix = self.matrices[idx]
        # get coordinate for brick in Ldraw units
        co = self.blend_to_ldraw_units(bricksdict, self.zstep, key, idx)
        # get color code of brick
        abs_mat_names = get_abs_mat_names()
        mat_name = get_material_name(bricksdict, key, size, self.zstep, self.material_type, self.mat_shell_depth, self.custom_mat, self.random_mat_seed, brick_mats=self.brick_mats)
        rgba = brick_d["rgba"]
        if mat_name in abs_mat_names and self.abs_mat_properties is not None:
            abs_mat_name = mat_name
        elif rgba not in (None, "") and self.material_type != "NONE" and self.color_snap != "ABS":
            abs_mat_name = find_nearest_color_name(rgba, trans_weight=self.trans_weight)
        elif bpy.data.materials.get(mat_name) is not None:
            rgba = get_material_color(mat_name)
            abs_mat_name = find_nearest_color_name(rgba, trans_weight=self.trans_weight)
        elif not mat_name and self.internal_mat and self.internal_mat.name in abs_mat_names:
            abs_mat_name = self.internal_mat.name
        else:
            abs_mat_name = ""
        color = self.abs_mat_properties[abs_mat_name]["LDR Code"] if abs_mat_name else 0
        # get part number and ldraw file name for brick
        part = get_part(self.legal_bricks, size, typ)["pt2" if typ == "SLOPE" and size[:2] in ([4, 2], [2, 4], [3, 2], [2, 3]) and brick_d["rotated"] else "pt"]
        brick_file = "%(part)s.dat" % locals()
        # offset the coordinate and round to ensure appropriate Ldraw location
        co += offset
        co = Vector((round_nearest(co.x, 5), round_nearest(co.y, 8), round_nearest(co.z, 5)))
        # get brick info line
        brick_info_line = "1 {color} {x} {y} {z} {matrix} {brick_file}\n".format(color=color, x=co.x, y=co.y, z=co.z, matrix=matrix, brick_file=brick_file)
        return brick_info_line

    def get_step_line(self, direction):
        if direction == "UP":
            return "0 ROTSTEP 40 45 0 ABS\n"
            # return "0 ROTSTEP 180 180 0 ABS\n"
        else:
            return "0 ROTSTEP -40 45 0 ABS\n"
            # return "0 ROTSTEP 180 180 0 ABS\n"

    def get_brick_idx(self, brick_d, size, typ):
        if typ == "SLOPE":
            idx = 0
            idx -= 2 if brick_d["flipped"] else 0
            idx -= 1 if brick_d["rotated"] else 0
            idx += 2 if (size[:2] in ([1, 2], [1, 3], [1, 4], [2, 3]) and not brick_d["rotated"]) or size[:2] == [2, 4] else 0
        else:
            idx = 1
        idx += 1 if size[1] > size[0] else 0
        return idx

    def blend_to_ldraw_units(self, bricksdict, zstep, key, idx):
        """ convert location of brick from blender units to ldraw units """
        brick_d = bricksdict[key]
        size = brick_d["size"]
        loc = get_brick_center(bricksdict, key, zstep)
        dimensions = get_brick_dimensions(self.brick_height, zstep, self.gap)
        h = 8 * zstep
        # initialize xy loc
        loc.x = loc.x * (20 / (dimensions["width"] + dimensions["gap"]))
        loc.y = loc.y * (20 / (dimensions["width"] + dimensions["gap"]))
        # handle special xy cases
        if brick_d["type"] == "SLOPE":
            if idx == 0:
                loc.x -= ((size[0] - 1) * 20) / 2
            elif idx in (1, -3):
                loc.y += ((size[1] - 1) * 20) / 2
            elif idx in (2, -2):
                loc.x += ((size[0] - 1) * 20) / 2
            elif idx in (3, -1):
                loc.y -= ((size[1] - 1) * 20) / 2
        # initialize z loc
        loc.z = loc.z * (h / (dimensions["height"] + dimensions["gap"]))
        # handle special z cases
        if brick_d["type"] == "SLOPE" and size == [1, 1, 3]:
            loc.z -= size[2] * 8
        if zstep == 1 and size[2] == 3:
            loc.z += 8
        # convert to right-handed co-ordinate system where -Y is "up"
        loc = Vector((loc.x, -loc.z, loc.y))
        return loc

    #############################################
