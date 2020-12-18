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
# NONE!

# Blender imports
import bpy
from bpy.props import *
from bpy.types import Panel

# Module imports
from ..functions.common import *
from .. import addon_updater_ops

class PROPERTIES_PT_abs_plastic_materials(Panel):
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context     = "material"
    bl_label       = "ABS Plastic Materials"
    bl_idname      = "PROPERTIES_PT_abs_plastic_materials"
    # bl_category    = "ABS Plastic Materials"
    COMPAT_ENGINES = {"CYCLES", "BLENDER_EEVEE"}

    # @classmethod
    # def poll(cls, context):
    #     """ ensures operator can execute (if not, returns false) """
    #     return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Call to check for update in background
        # Internally also checks to see if auto-check enabled
        # and if the time interval has passed
        addon_updater_ops.check_for_update_background()
        # draw auto-updater update box
        addon_updater_ops.update_notice_box_ui(self, context)

        col = layout.column(align=True)
        col.operator("abs.append_materials", text="Import ABS Plastic Materials", icon="IMPORT")
        # col.operator("abs.mark_outdated", text="Mark Materials as Outdated", icon="LIBRARY_DATA_OVERRIDE" if b280() else "GO_LEFT")

        col = layout.column(align=True)
        right_align(col)
        col.prop(scn, "save_datablocks")
        if b280():
            col.prop(scn, "abs_viewport_transparency")


class PROPERTIES_PT_abs_plastic_materials_properties(Panel):
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context     = "material"
    bl_label       = "Properties" if b280() else "ABS Plastic Properties"
    bl_parent_id   = "PROPERTIES_PT_abs_plastic_materials"
    bl_idname      = "PROPERTIES_PT_abs_plastic_materials_properties"
    # bl_category    = "ABS Plastic Materials"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_EEVEE"}

    # @classmethod
    # def poll(cls, context):
    #     """ ensures operator can execute (if not, returns false) """
    #     return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # material settings
        col = layout.column(align=False)
        right_align(col)
        # col.label(text="Properties:")
        col.prop(scn, "abs_subsurf")
        col.prop(scn, "abs_roughness")
        col.prop(scn, "abs_fingerprints")
        col.prop(scn, "abs_randomize")


class PROPERTIES_PT_abs_plastic_materials_texture_mapping(Panel):
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context     = "material"
    bl_label       = "Texture Map" if b280() else "ABS Plastic Texture Mapping"
    bl_parent_id   = "PROPERTIES_PT_abs_plastic_materials"
    bl_idname      = "PROPERTIES_PT_abs_plastic_materials_texture_mapping"
    # bl_category    = "ABS Plastic Materials"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_EEVEE"}

    # @classmethod
    # def poll(cls, context):
    #     """ ensures operator can execute (if not, returns false) """
    #     return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=False)
        right_align(col)
        # col.label(text="Texture Mapping:")
        col.prop(scn, "abs_mapping", text="Mapping")
        col.prop(scn, "abs_displace")
        col.prop(scn, "abs_uv_scale", text="Scale")
        col.prop(scn, "abs_fpd_quality", text="FP/Dust Quality")
        if b280():
            col.prop(scn, "abs_s_quality", text="Scratch Quality")


class PROPERTIES_PT_abs_plastic_materials_dev_tools(Panel):
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context     = "material"
    bl_label       = "Dev Tools" if b280() else "ABS Plastic Dev Tools"
    bl_parent_id   = "PROPERTIES_PT_abs_plastic_materials"
    bl_idname      = "PROPERTIES_PT_abs_plastic_materials_dev_tools"
    # bl_category    = "ABS Plastic Materials"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_EEVEE"}

    @classmethod
    def poll(cls, context):
        """ ensures operator can execute (if not, returns false) """
        return bpy.props.abs_developer_mode != 0

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        layout.operator("abs.export_node_groups", icon="EXPORT")
