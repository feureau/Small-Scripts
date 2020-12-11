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
import copy

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_change_brick_type(Operator):
    """Change brick type of active brick"""
    bl_idname = "bricker.change_brick_type"
    bl_label = "Change Brick Type"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        scn = context.scene
        objs = context.selected_objects
        # check that at least 1 selected object is a brick
        for obj in objs:
            if not obj.is_brick:
                continue
            # get cmlist item referred to by object
            cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
            return True
        return False

    def execute(self, context):
        wm = context.window_manager
        wm.bricker_running_blocking_operation = True
        try:
            self.change_type(context)
        except:
            bricker_handle_exception()
        wm.bricker_running_blocking_operation = False
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        right_align(col)
        col.prop(self, "brick_type")
        if "SLOPE" in self.brick_type:
            col.prop(self, "flip_brick")
            col.prop(self, "rotate_brick")

    ################################################
    # initialization method

    def __init__(self):
        try:
            self.undo_stack = UndoStack.get_instance()
            self.orig_undo_stack_length = self.undo_stack.get_length()
            scn = bpy.context.scene
            selected_objects = bpy.context.selected_objects
            # initialize self.flip_brick, self.rotate_brick, and self.brick_type
            for obj in selected_objects:
                if not obj.is_brick:
                    continue
                # get cmlist item referred to by object
                cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
                # get bricksdict from cache
                bricksdict = get_bricksdict(cm)
                dkey = get_dict_key(obj.name)
                cur_brick_d = bricksdict[dkey]
                # initialize properties
                cur_brick_type = cur_brick_d["type"]
                cur_brick_size = cur_brick_d["size"]
                try:
                    self.flip_brick = cur_brick_d["flipped"]
                    self.rotate_brick = cur_brick_d["rotated"]
                    self.brick_type = cur_brick_type or "STANDARD"
                except TypeError:
                    pass
                break
            self.obj_names_dict = create_obj_names_dict(selected_objects)
            self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        except:
            bricker_handle_exception()

    ###################################################
    # class variables

    # vars
    bricksdicts = {}
    bricksdict = {}
    obj_names_dict = {}

    # get items for brick_type prop
    def get_items(self, context):
        items = get_available_types(by="SELECTION")
        return items


    # properties
    brick_type = bpy.props.EnumProperty(
        name="Brick Type",
        description="Choose what type of brick should be drawn at this location",
        items=get_items,
        default=None)
    flip_brick = bpy.props.BoolProperty(
        name="Flip Brick Orientation",
        description="Flip the brick about the non-mirrored axis",
        default=False)
    rotate_brick = bpy.props.BoolProperty(
        name="Rotate 90 Degrees",
        description="Rotate the brick about the Z axis (brick width & depth must be equivalent)",
        default=False)

    ###################################################
    # class methods

    def change_type(self, context):
        # revert to last bricksdict
        self.undo_stack.match_python_to_blender_state()
        # push to undo stack
        if self.orig_undo_stack_length == self.undo_stack.get_length():
            self.undo_stack.undo_push("change_type", affected_ids=list(self.obj_names_dict.keys()))
        scn = context.scene
        legal_brick_sizes = bpy.props.bricker_legal_brick_sizes
        # get original active and selected objects
        active_obj = context.active_object
        initial_active_obj_name = active_obj.name if active_obj else ""
        selected_objects = context.selected_objects
        obj_names_to_select = []
        bricks_were_generated = False
        # only reference self.brick_type once (runs get_items)
        target_brick_type = self.brick_type

        # iterate through cm_ids of selected objects
        for cm_id in self.obj_names_dict.keys():
            cm = get_item_by_id(scn.cmlist, cm_id)
            self.undo_stack.iterate_states(cm)
            # initialize vars
            bricksdict = deepcopy(self.bricksdicts[cm_id])
            keys_to_update = set()
            update_has_custom_objs(cm, target_brick_type)
            cm.customized = True
            brick_type = cm.brick_type
            brick_height = cm.brick_height
            gap = cm.gap
            draw_threshold = get_threshold(cm)

            # iterate through names of selected objects
            for obj_name in self.obj_names_dict[cm_id]:
                # initialize vars
                dkey = get_dict_key(obj_name)
                dloc = get_dict_loc(bricksdict, dkey)
                cur_brick_d = bricksdict[dkey]
                x0, y0, z0 = dloc
                # get size of current brick (e.g. [2, 4, 1])
                size = cur_brick_d["size"]
                typ = cur_brick_d["type"]

                # skip bricks that are already of type self.brick_type
                if (typ == target_brick_type
                    and (not typ.startswith("SLOPE")
                         or (cur_brick_d["flipped"] == self.flip_brick
                             and cur_brick_d["rotated"] == self.rotate_brick))):
                    continue
                # skip bricks that can't be turned into the chosen brick type
                if size[:2] not in legal_brick_sizes[3 if target_brick_type in get_brick_types(height=3) else 1][target_brick_type]:
                    continue

                # verify locations above are not obstructed
                if target_brick_type in get_brick_types(height=3) and size[2] == 1:
                    above_keys = [list_to_str((x0 + x, y0 + y, z0 + z)) for z in range(1, 3) for y in range(size[1]) for x in range(size[0])]
                    obstructed = False
                    for cur_key in above_keys:
                        if cur_key in bricksdict and bricksdict[cur_key]["draw"]:
                            self.report({"INFO"}, "Could not change to type {brick_type}; some locations are occupied".format(brick_type=target_brick_type))
                            obstructed = True
                            break
                    if obstructed: continue

                # set type of parent brick to target_brick_type
                last_type = cur_brick_d["type"]
                cur_brick_d["type"] = target_brick_type
                cur_brick_d["flipped"] = self.flip_brick
                cur_brick_d["rotated"] = False if min(size[:2]) == 1 and max(size[:2]) > 1 else self.rotate_brick

                # update height of brick if necessary, and update dictionary accordingly
                if flat_brick_type(brick_type):
                    dimensions = get_brick_dimensions(brick_height, cm.zstep, gap)
                    size = update_brick_size_and_dict(dimensions, get_source_name(cm), bricksdict, size, dkey, dloc, draw_threshold, cur_height=size[2], target_type=target_brick_type)

                # check if brick spans 3 matrix locations
                b_and_p_brick = flat_brick_type(brick_type) and size[2] == 3

                # verify exposure above and below
                brick_locs = get_locs_in_brick(size, cm.zstep, dloc)
                for cur_loc in brick_locs:
                    bricksdict = verify_all_brick_exposures(scn, cm.zstep, cur_loc, bricksdict, decriment=3 if b_and_p_brick else 1)
                    # add bricks to keys_to_update
                    keys_to_update |= set(get_parent_key(bricksdict, list_to_str((x0 + x, y0 + y, z0 + z))) for z in (-1, 0, 3 if b_and_p_brick else 1) for y in range(size[1]) for x in range(size[0]))
                obj_names_to_select += [bricksdict[list_to_str(loc)]["name"] for loc in brick_locs]

            # remove null key if present
            keys_to_update.discard(None)
            # if something was updated, set bricks_were_generated
            bricks_were_generated = bricks_were_generated or len(keys_to_update) > 0

            # draw updated brick
            draw_updated_bricks(cm, bricksdict, keys_to_update, run_pre_merge=False, select_created=False)
        # select original bricks
        orig_obj = bpy.data.objects.get(initial_active_obj_name)
        if orig_obj is not None: set_active_obj(orig_obj)
        objs_to_select = [bpy.data.objects.get(obj_n) for obj_n in obj_names_to_select if bpy.data.objects.get(obj_n) is not None]
        select(objs_to_select)
        # store current bricksdict to cache when re-run with original brick type so bricksdict is updated
        if not bricks_were_generated:
            cache_bricks_dict("CREATE", cm, bricksdict)
        # print helpful message to user in blender interface
        if bricks_were_generated:
            self.report({"INFO"}, "Changed bricks to type '{target_type}'".format(size=list_to_str(size).replace(",", "x"), target_type=target_brick_type))

    #############################################
