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
from ..created_model_uilist import *
from ..panel_info import *
from ...operators.test_brick_generators import *
from ...functions import *
from ... import addon_updater_ops


class BRICKER_MT_specials(bpy.types.Menu):
    bl_idname      = "BRICKER_MT_specials"
    bl_label       = "Select"

    def draw(self, context):
        layout = self.layout

        layout.operator("cmlist.copy_settings_to_others", icon="COPY_ID", text="Copy Settings to Others")
        layout.operator("cmlist.copy_settings", icon="COPYDOWN", text="Copy Settings")
        layout.operator("cmlist.paste_settings", icon="PASTEDOWN", text="Paste Settings")
        layout.separator()
        layout.label(text="Brick Selection:")
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_OFF", text="Select All").deselect = False
        layout.operator("bricker.select_bricks_by_type", icon="RESTRICT_SELECT_OFF", text="Select By Type")
        layout.operator("bricker.select_bricks_by_size", icon="RESTRICT_SELECT_OFF", text="Select By Size")
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_ON", text="Deselect All").deselect = True
        if b280():
            layout.separator()
            layout.operator("cmlist.link_animated_model", icon="LINK_BLEND")
            # layout.operator("cmlist.link_frames", icon="LINK_BLEND")


class VIEW3D_PT_bricker_brick_models(BrickerPanel, Panel):
    bl_label       = "Brick Models"
    bl_idname      = "VIEW3D_PT_bricker_brick_models"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Call to check for update in background
        # Internally also checks to see if auto-check enabled
        # and if the time interval has passed
        addon_updater_ops.check_for_update_background()
        # draw auto-updater update box
        addon_updater_ops.update_notice_box_ui(self, context)

        # if blender version is before 2.79, ask user to upgrade Blender
        if bversion() < "002.079":
            col = layout.column(align=True)
            col.label(text="ERROR: upgrade needed", icon="ERROR")
            col.label(text="Bricker requires Blender 2.79+")
            return

        # draw UI list and list actions
        rows = 2 if len(scn.cmlist) < 2 else 4
        row = layout.row()
        row.template_list("BRICKER_UL_created_models", "", scn, "cmlist", scn, "cmlist_index", rows=rows)

        col = row.column(align=True)
        col.operator("bricker.cm_list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="", icon="ADD" if b280() else "ZOOMIN").action = "ADD"
        col.operator("bricker.cm_list_action", icon="REMOVE" if b280() else "ZOOMOUT", text="").action = "REMOVE"
        col.menu("BRICKER_MT_specials", icon="DOWNARROW_HLT", text="")
        if len(scn.cmlist) > 1:
            col.separator()
            col.operator("bricker.cm_list_action", icon="TRIA_UP", text="").action = "UP"
            col.operator("bricker.cm_list_action", icon="TRIA_DOWN", text="").action = "DOWN"

        # draw menu options below UI list
        if scn.cmlist_index == -1:
            layout.operator("bricker.cm_list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="New Brick Model", icon="ADD" if b280() else "ZOOMIN").action = "ADD"
        else:
            cm, n = get_active_context_info()[1:]

            if not created_with_newer_version(cm):
                # first, draw source object text
                source_name = " %(n)s" % locals() if cm.animated or cm.model_created else ""
                col1 = layout.column(align=True)
                col1.label(text="Source Object:%(source_name)s" % locals())
                if not (cm.animated or cm.model_created):
                    col2 = layout.column(align=True)
                    col2.prop_search(cm, "source_obj", scn, "objects", text="")

            # draw anim only ui
            if cm.linked_from_external:
                if cm.animated:
                    col = layout.column(align=True)
                    right_align(col)
                    col.prop(cm, "last_start_frame", text="Frame Start")
                    col.prop(cm, "last_stop_frame", text="End")
                    col.prop(cm, "last_step_frame", text="Step")
                return

            # initialize variables
            obj = cm.source_obj
            v_str = cm.version[:3]

            # if model created with newer version, disable
            if created_with_newer_version(cm):
                col = layout.column(align=True)
                col.scale_y = 0.7
                col.label(text="Model was created with")
                col.label(text="Bricker v%(v_str)s. Please" % locals())
                col.label(text="update Bricker in your")
                col.label(text="addon preferences to edit")
                col.label(text="this model.")
            # if undo stack not initialized, draw initialize button
            elif not bpy.props.bricker_initialized:
                row = col1.row(align=True)
                row.operator("bricker.initialize", text="Initialize Bricker", icon="MODIFIER")
                # draw test brick generator button (for testing purposes only)
                if BRICKER_OT_test_brick_generators.draw_ui_button():
                    col = layout.column(align=True)
                    col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")
            # if use animation is selected, draw animation options
            elif cm.use_animation:
                if cm.animated:
                    row1 = col1.row(align=True)
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    if cm.brickifying_in_background and cm.frames_to_animate > 0:
                        row1.operator("bricker.stop_brickifying_in_background", text="Stop Brickifying", icon="PAUSE")
                        row = col.row(align=True)
                        row.prop(cm, "job_progress")
                    else:
                        row1.operator("bricker.delete_model", text="Delete Brick Animation", icon="CANCEL")
                        row.active = brickify_should_run(cm)
                        if (cm.start_frame < cm.last_start_frame or cm.stop_frame > cm.last_stop_frame) and not update_can_run("ANIMATION"):
                            row.operator("bricker.brickify", text="Complete Animation", icon="FORWARD").split_before_update = False
                        else:
                            row.operator("bricker.brickify", text="Update Animation", icon="FILE_REFRESH").split_before_update = False
                    if created_with_unsupported_version(cm):
                        v_str = cm.version[:3]
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                else:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == "MESH" and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Animation", icon="MOD_REMESH").split_before_update = False
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
            # if use animation is not selected, draw modeling options
            else:
                if not cm.animated and not cm.model_created:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == "MESH" and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Object", icon="MOD_REMESH").split_before_update = False
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
                else:
                    row = col1.row(align=True)
                    row.operator("bricker.delete_model", text="Stop Brickifying" if cm.brickifying_in_background and cm.frames_to_animate > 0 else "Delete Brick Model", icon="CANCEL")
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    if cm.brickifying_in_background:
                        row.label(text="Brickifying...")
                    else:
                        row.active = brickify_should_run(cm)
                        row.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH").split_before_update = False
                    if created_with_unsupported_version(cm):
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                    elif matrix_really_is_dirty(cm, include_lost_matrix=False) and cm.customized:
                        row = col.row(align=True)
                        row.label(text="Customizations will be lost")
                        row = col.row(align=True)
                        row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")

            col = layout.column(align=True)
            row = col.row(align=True)

        if bpy.data.texts.find("Bricker log") >= 0:
            split = layout_split(layout, factor=0.9)
            split.operator("bricker.report_error", text="Report Error", icon="URL")
            split.operator("bricker.close_report_error", text="", icon="PANEL_CLOSE")
