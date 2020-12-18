# Copyright (C) 2019 Christopher Gearhart
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
import os
import time

# Blender imports
import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector

# Module imports
from ..functions import *


class ABS_OT_export_node_groups(Operator):
    """Export ABS Plastic Materials node groups to 'node_groups_2-7/8.blend' library file"""
    bl_idname = "abs.export_node_groups"
    bl_label = "Export ABS Node Groups"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return bpy.props.abs_developer_mode != 0

    def execute(self, context):
        data_blocks = []

        # un-map image nodes from image data blocks
        backup_ims = {}
        for gn in ("ABS_Fingerprint", "ABS_Specular Map", "ABS_Scratches"):
            ng = bpy.data.node_groups.get(gn)
            for node in ng.nodes:
                if node.type == "TEX_IMAGE":
                    backup_ims[node.name] = node.image
                    node.image = None

        # append node groups from nodeDirectory
        group_names = ("ABS_Bump", "ABS_Dialectric", "ABS_Transparent", "ABS_Uniform Scale", "ABS_Translate")
        for group_name in group_names:
            data_blocks.append(bpy.data.node_groups.get(group_name))

        blendlib_name = "node_groups_2-8.blend" if b280() else "node_groups_2-7.blend"
        storage_path = os.path.join(get_addon_directory(), "lib", blendlib_name)

        assert None not in data_blocks

        bpy.data.libraries.write(storage_path, set(data_blocks), fake_user=True)

        self.report({"INFO"}, "Exported successfully!")

        # re-map image nodes back to correct image data block
        for gn in ("ABS_Fingerprint", "ABS_Specular Map", "ABS_Scratches"):
            ng = bpy.data.node_groups.get(gn)
            for node in ng.nodes:
                if node.type == "TEX_IMAGE":
                    node.image = backup_ims[node.name]

        return {"FINISHED"}

    #############################################
