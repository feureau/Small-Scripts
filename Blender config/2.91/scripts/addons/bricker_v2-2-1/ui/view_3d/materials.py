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
# NONE!

# Blender imports
import bpy
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..matslot_uilist import *
from ..panel_info import *
from ...functions import *


class VIEW3D_PT_bricker_materials(BrickerPanel, Panel):
    bl_label       = "Materials"
    bl_idname      = "VIEW3D_PT_bricker_materials"
    bl_parent_id   = "VIEW3D_PT_bricker_model_settings"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj

        col = layout.column(align=True)
        col.prop(cm, "material_type", text="")

        if cm.material_type == "CUSTOM":
            col = layout.column(align=True)
            col.prop(cm, "custom_mat", text="")
            if brick_materials_installed() and not brick_materials_imported():
                col.operator("abs.append_materials", text="Import Brick Materials", icon="IMPORT")
            if cm.model_created or cm.animated:
                col = layout.column(align=True)
                col.operator("bricker.apply_material", icon="FILE_TICK")
        elif cm.material_type == "RANDOM":
            col = layout.column(align=True)
            col.active = cm.instance_method != "POINT_CLOUD"
            col.prop(cm, "random_mat_seed")
            if cm.model_created or cm.animated:
                if cm.material_is_dirty and not cm.last_split_model:
                    col = layout.column(align=True)
                    col.label(text="Run 'Update Model' to apply changes")
                elif cm.last_material_type == cm.material_type or (not cm.use_animation and cm.last_split_model):
                    col = layout.column(align=True)
                    col.operator("bricker.apply_material", icon="FILE_TICK")
        elif cm.material_type in "SOURCE" and obj:
            # internal material info
            if cm.shell_thickness > 1 or cm.internal_supports != "NONE":
                # if len(obj.data.uv_layers) <= 0 or len(obj.data.vertex_colors) > 0:
                col = layout.column(align=True)
                col.active = cm.instance_method != "POINT_CLOUD"
                col.label(text="Internal Material:")
                col.prop(cm, "internal_mat", text="")
                col.prop(cm, "mat_shell_depth")
                if cm.model_created:
                    if cm.mat_shell_depth <= cm.last_mat_shell_depth and cm.last_split_model:
                        col.operator("bricker.apply_material", icon="FILE_TICK")
                    else:
                        col.label(text="Run 'Update Model' to apply changes")

            # color snapping info
            col = layout.column(align=True)
            col.active = cm.instance_method != "POINT_CLOUD"
            col.label(text="Color Mapping:")
            row = col.row(align=True)
            row.prop(cm, "color_snap", expand=True)
            if cm.color_snap == "RGB":
                col.prop(cm, "color_depth")
            if cm.color_snap == "ABS":
                # col.prop(cm, "blur_radius")
                # col.prop(cm, "color_depth")
                col.prop(cm, "transparent_weight", text="Transparent Weight")

            if not b280() and cm.color_snap != "NONE":
                col = layout.column(align=True)
                col.active = len(obj.data.uv_layers) > 0 and cm.instance_method != "POINT_CLOUD"
                row.prop(cm, "use_uv_map", text="Use UV Map")
                if cm.use_uv_map:
                    split = layout_split(row, factor=0.75)
                    # split.active = cm.use_uv_map
                    split.prop(cm, "uv_image", text="")
                    split.operator("image.open", icon="FILEBROWSER" if b280() else "FILESEL", text="")
                if len(obj.data.vertex_colors) > 0:
                    col = layout.column(align=True)
                    col.scale_y = 0.7
                    col.label(text="(Vertex colors not supported)")


class VIEW3D_PT_bricker_use_uv_map(BrickerPanel, Panel):
    bl_label       = "Use UV Map"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_idname      = "VIEW3D_PT_bricker_use_uv_map"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn() or not b280():
            return False
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj
        if cm.instance_method == "POINT_CLOUD":
            return False
        if obj and len(obj.data.uv_layers) > 0 and cm.material_type == "SOURCE" and cm.color_snap != "NONE":
            return True
        return False

    def draw_header(self, context):
        scn, cm, _ = get_active_context_info()
        self.layout.prop(cm, "use_uv_map", text="")

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "uv_image", text="Tex")
        row.operator("image.open", icon="FILEBROWSER" if b280() else "FILESEL", text="")


class VIEW3D_PT_bricker_included_materials(BrickerPanel, Panel):
    bl_label       = "Included Materials"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_idname      = "VIEW3D_PT_bricker_included_materials"

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        # order here is important
        if cm.material_type == "RANDOM":
            return True
        elif cm.instance_method == "POINT_CLOUD":
            return False
        elif cm.material_type == "SOURCE" and cm.color_snap == "ABS":
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        mat_obj = get_mat_obj(cm)
        if mat_obj is None:
            return
        col = layout.column(align=True)
        if not brick_materials_installed():
            col.label(text="'ABS Plastic Materials' not installed")
            col.scale_y = 0.75
            col = layout.column(align=True)
            col.operator("wm.url_open", text="View Website", icon="WORLD").url = "http://www.blendermarket.com/products/abs-plastic-materials"
            col.separator()
        elif scn.render.engine not in ("CYCLES", "BLENDER_EEVEE"):
            col.label(text="Switch to 'Cycles' or 'Eevee' for Brick Materials")
        else:
            # draw materials UI list and list actions
            num_mats = len(mat_obj.data.materials)
            rows = 5 if num_mats > 5 else (num_mats if num_mats > 2 else 2)
            split = layout_split(col, factor=0.85)
            col1 = split.column(align=True)
            col1.template_list("MATERIAL_UL_matslots", "", mat_obj, "material_slots", mat_obj, "active_material_index", rows=rows)
            col1 = split.column(align=True)
            col1.operator("bricker.mat_list_action", icon="REMOVE" if b280() else "ZOOMOUT", text="").action = "REMOVE"
            col1.scale_y = 1 + rows
            if not brick_materials_imported():
                col.operator("abs.append_materials", text="Import Brick Materials", icon="IMPORT")
            else:
                col.operator("bricker.add_abs_plastic_materials", text="Add ABS Plastic Materials", icon="ADD" if b280() else "ZOOMIN")
            # settings for adding materials
            if hasattr(bpy.props, "abs_mats_common"):  # checks that ABS plastic mats are at least v2.1
                col = layout.column(align=True)
                right_align(col)
                col.prop(scn, "include_transparent")
                col.prop(scn, "include_uncommon")

            col = layout.column(align=True)
            split = layout_split(col, factor=0.25)
            col = split.column(align=True)
            col.label(text="Add:")
            col = split.column(align=True)
            col.prop(cm, "target_material", text="")
            if cm.target_material_message != "" and time.time() - float(cm.target_material_time) < 4:
                col = layout.column(align=True)
                col.label(text=cm.target_material_message, icon="INFO" if cm.target_material_message.startswith("Added") else "ERROR")


class VIEW3D_PT_bricker_material_properties(BrickerPanel, Panel):
    bl_label       = "Material Properties"
    bl_idname      = "VIEW3D_PT_bricker_material_properties"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj
        if cm.instance_method == "POINT_CLOUD":
            return False
        if cm.material_type == "SOURCE" and obj:
            if cm.color_snap == "RGB" or (cm.use_uv_map and len(obj.data.uv_layers) > 0 and cm.color_snap == "NONE"):
                return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=True)
        right_align(col)
        col.prop(cm, "use_abs_template")
        col.enabled = brick_materials_installed()

        if not (cm.use_abs_template and brick_materials_installed()):
            obj = cm.source_obj
            if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
                col = layout.column(align=True)
                col.prop(cm, "color_snap_specular")
                col.prop(cm, "color_snap_roughness")
                col.prop(cm, "color_snap_ior")
            if scn.render.engine in ("CYCLES", "BLENDER_EEVEE"):
                col.prop(cm, "color_snap_sss")
                col.prop(cm, "color_snap_sss_saturation")
                col.prop(cm, "color_snap_transmission")
            if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
                col = layout.column(align=True)
                right_align(col)
                col.prop(cm, "include_transparency")
        elif brick_materials_installed():
            col = layout.column(align=True)
            col.prop(cm, "color_snap_sss")
            col.prop(cm, "color_snap_displacement")
            col = layout.column(align=True)
            right_align(col)
            col.prop(cm, "include_transparency")
