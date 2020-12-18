# Copyright (C) 2018 Christopher Gearhart
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
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

# Addon imports
from ..functions import *


def get_quadview_index(context, x, y):
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        is_quadview = len(area.spaces.active.region_quadviews) == 0
        i = -1
        for region in area.regions:
            if region.type == 'WINDOW':
                i += 1
                if (x >= region.x and
                    y >= region.y and
                    x < region.width + region.x and
                    y < region.height + region.y):

                    return (area.spaces.active, None if is_quadview else i)
    return (None, None)


class BricksculptFramework:
    """ modal framework for the paintbrush tool """

    ################################################
    # Blender Operator methods

    def modal(self, context, event):
        try:
            ct = time.time()
            scn = bpy.context.scene

            # commit changes on 'ret' key press
            if event.type == "RET" and event.value == "PRESS":
                self.commit_changes(context)
                return{"FINISHED"}
            # cancel changes on 'esc' key press
            if event.type == "ESC" and self.layer_solod is None and event.value == "PRESS":
                bpy.ops.bricksculpt.confirm_cancel("INVOKE_DEFAULT")
            if context.scene.bricksculpt.cancel_session_changes:
                self.cancel_changes(context)
                return{"CANCELLED"}

            # block undo action
            if event.type == "Z" and (event.ctrl or event.oskey):
                self.report({"WARNING"}, "Undo not allowed during BrickSculpt session")
                return {"RUNNING_MODAL"}

            # switch mode
            if not self.left_click and event.value == "PRESS":
                if event.type in "DC" and self.mode != "DRAW":
                    if self.mode == "PAINT":
                        self.last_paintbrush_mat = None  # runs merge on release code
                    self.mode = "DRAW"
                    self.set_cursor_type(event)
                elif event.type in "MS" and self.mode != "MERGE_SPLIT":
                    if self.mode == "PAINT":
                        self.last_paintbrush_mat = None  # runs merge on release code
                    self.mode = "MERGE_SPLIT"
                    self.set_cursor_type(event)
                elif event.type == "P" and self.mode != "PAINT":
                    self.mode = "PAINT"
                    self.set_cursor_type(event)

            if self.mode == "PAINT":
                # choose new material
                if (event.type == "SPACE" and event.value == "PRESS"):
                    scn.bricksculpt.choosing_material = True
                    bpy.ops.bricksculpt.choose_paintbrush_material("INVOKE_DEFAULT")

            # store current mouse information
            self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            self.mouse_travel = abs(self.mouse.x - self.last_mouse.x) + abs(self.mouse.y - self.last_mouse.y)

            # unhide all bricks before view rays casted for hide action
            prefs = get_addon_preferences()
            if event.value == "PRESS" and prefs.enable_layer_soloing and (
                (event.ctrl and self.mouse_travel >= 2) or
                (self.layer_solod is not None and event.type == "ESC")
            ):
                self.unhide_all()
                if event.type == "ESC":
                    self.layer_solod = None

            # check if left_click is pressed
            if event.type == "LEFTMOUSE":
                if event.value == "PRESS":
                    # block left_click if not in 3D viewport
                    if not mouse_in_view3d_window(event, context.area, include_tools_panel=True):
                        return {"RUNNING_MODAL"}
                    # enable click
                    self.left_click = True
                elif event.value == "RELEASE":
                    self.last_mouse = Vector((-10, -10))  # reset the last_mouse position so mouse_travel is reset
                    if not self.left_click:
                        return {"RUNNING_MODAL"}
                    self.left_click = False
                    self.release_time = time.time()
                    # clear bricks protected from deletion
                    self.protected_until_release = set()

            # cast ray to calculate mouse position and travel
            if event.type in ('MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_ALT', 'RIGHT_ALT', 'UP_ARROW', 'DOWN_ARROW') or self.left_click or self.initialize_cursor:
                self.initialize_cursor = False
                scn, cm, n = self.get_active_context_info(context)
                tag_redraw_areas("VIEW_3D")
                # set mouse information
                if event.type.endswith("MOUSEMOVE") and self.mouse_travel < 2:
                    return {"RUNNING_MODAL"}
                # hover the scene to get targetted obj, near_key, loc, normal
                self.obj, self.near_key, self.loc, self.normal = self.hover_scene(context, self.mouse.x, self.mouse.y, n, update_header=self.left_click)
                # self.update_ui_mouse_pos()
                # run solo layer functionality
                if (event.type.endswith("ARROW") or event.ctrl) and not event.alt and event.value == "PRESS" and prefs.enable_layer_soloing:
                    if self.obj is None and event.ctrl:
                        self.layer_solod = None
                    elif event.ctrl or (self.obj and self.layer_solod is None):
                        if self.mode == "PAINT":
                            self.run_post_action_cleanup(context)
                        self.last_mouse = self.mouse
                        cur_key, cur_loc = self.get_cur_loc_and_key()
                        near_loc = self.get_nearest_loc(cur_key, cur_loc, cm)
                        self.solo_layer(near_loc[2], cm.zstep)
                    elif event.type.endswith("ARROW"):
                        self.move_solod_layer(event, cm.zstep)
                # if not object found return running_modal
                if self.obj is None:
                    bpy.context.window.cursor_set("DEFAULT")
                    return {"RUNNING_MODAL"}
                elif not scn.bricksculpt.choosing_material:
                    self.set_cursor_type(event)
                    # if self.obj.name == "BrickSculpt_temp_bricks":
                    #     return {"RUNNING_MODAL"}

            # run BrickSculpt action(s) on left_click & drag
            if self.left_click and (event.type == 'LEFTMOUSE' or (event.type.endswith("MOUSEMOVE") and (not event.alt or self.mouse_travel > 5))):
                # determine which action (if any) to run at current mouse position
                add_brick = self.mode == "DRAW" and not event.alt
                remove_brick = self.mode == "DRAW" and event.alt and self.mouse_travel > 10
                change_material = self.mode == "PAINT" and not (event.alt or scn.bricksculpt.paintbrush_mat is None)
                get_material = self.mode == "PAINT" and (event.alt or scn.bricksculpt.paintbrush_mat is None)
                split_brick = self.mode == "MERGE_SPLIT" and (event.alt or event.shift)
                merge_bricks = self.mode == "MERGE_SPLIT" and self.obj.name not in self.keys_to_update_on_release and not event.alt
                # get key/loc/size of brick at mouse position
                action_taken = add_brick or remove_brick or change_material or get_material or split_brick or merge_bricks
                if action_taken:
                    self.last_mouse = self.mouse
                    cur_key, cur_loc = self.get_cur_loc_and_key()
                # add brick next to existing brick
                if add_brick:
                    cur_key, cur_loc = self.add_brick(cm, n, cur_key, cur_loc)
                # remove existing brick
                elif remove_brick:
                    cur_key, cur_loc = self.remove_brick(context, cm, n, event, cur_key, cur_loc)
                # change material
                elif change_material:
                    cur_key, cur_loc = self.change_material(cm, n, cur_key, cur_loc, scn.bricksculpt.paintbrush_mat.name)
                # get material
                elif get_material:
                    self.get_material(scn, cm, n, cur_key, event)
                # split current brick
                elif split_brick:
                    self.split_brick(cm, event, cur_key, cur_loc)
                # add current brick to 'self.keys_to_merge'
                elif merge_bricks:
                    self.merge_bricks(cm, n, cur_key, cur_loc, mode=self.mode, state="DRAG")
                # stopwatch("Modal Iteration (action)", ct)
                return {"RUNNING_MODAL"}

            # clean up after splitting bricks
            if event.type in ("LEFT_ALT", "RIGHT_ALT", "LEFT_SHIFT", "RIGHT_SHIFT") and event.value == "RELEASE" and self.mode == "MERGE_SPLIT":
                deselect_all()

            # merge bricks in 'self.keys_to_merge'
            if (event.type == "LEFTMOUSE" and event.value == "RELEASE" and self.mode in ("DRAW", "MERGE_SPLIT")) or self.last_paintbrush_mat != scn.bricksculpt.paintbrush_mat:
                self.run_post_action_cleanup(context, attempt_merge=not (self.mode == "DRAW" and event.alt))

            # stopwatch("Modal Iteration", ct)
            return {"PASS_THROUGH" if is_navigation_event(event) or event.type in "N" else "RUNNING_MODAL"}
        except:
            self.cancel(context)
            bricksculpt_handle_exception()
            return {"CANCELLED"}

    ###################################################
    # class variables

    # NONE!

    #############################################
    # class methods

    def draw(self, context):
        row = self.layout
        row.prop(context.scene.bricksculpt, "cancel_session_changes", text="Cancel BrickSculpt Session (changes will be permanently lost)")

    # from CG Cookie's retopoflow plugin
    def hover_scene(self, context, x, y, source_name, update_header=True):
        """ casts ray through point x,y and sets self.obj if obj intersected """
        scn = context.scene
        self.region = context.region
        self.r3d = context.space_data.region_3d
        # TODO: Use custom view layer with only current model instead?
        if b280(): view_layer = self.ray_cast_view_layer
        rv3d = context.region_data
        if rv3d is None:
            return None
        coord = x, y
        ray_max = 1000000  # changed from 10000 to 1000000 to increase accuracy
        view_vector = region_2d_to_vector_3d(self.region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(self.region, rv3d, coord)
        ray_target = ray_origin + (view_vector * ray_max)

        if b280():
            result, loc, normal, idx, obj, mx = scn.ray_cast(view_layer, ray_origin, ray_target)
        else:
            result, loc, normal, idx, obj, mx = scn.ray_cast(ray_origin, ray_target)

        if result and obj.name == "BrickSculpt_temp_bricks":
            loc, near_key = nearest_neighbor(self.keys_to_update_on_release, point=loc, max_dist=self.brick_height)
        elif result and (obj.name.startswith('Bricker_' + source_name) or obj.name == "BrickSculpt_temp_bricks"):
            near_key = None
        else:
            obj = None
            near_key = None
            loc = None
            normal = None
            if b280():
                context.area.header_text_set(text=None)
            else:
                context.area.header_text_set()

        return obj, near_key, loc, normal

    def cancel(self, context):
        self.done(context)

    ##########################
