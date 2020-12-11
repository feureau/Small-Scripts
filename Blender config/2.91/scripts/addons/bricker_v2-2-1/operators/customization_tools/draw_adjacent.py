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
from bpy.props import *

# Module imports
# from .merge_bricks import *
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *


class BRICKER_OT_draw_adjacent(Operator):
    """Draw new brick(s) adjacent to active brick"""
    bl_idname = "bricker.draw_adjacent"
    bl_label = "Draw Adjacent Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        active_obj = context.active_object
        # check active object is not None
        if active_obj is None:
            return False
        # check that active_object is brick
        if not active_obj.is_brick:
            return False
        return True

    def execute(self, context):
        try:
            # only reference self.brick_type once (runs get_items)
            target_type = self.brick_type
            # store enabled/disabled values
            create_adj_bricks = [self.x_pos, self.x_neg, self.y_pos, self.y_neg, self.z_pos, self.z_neg]
            # if no sides were and are selected, don't execute (i.e. if only brick type changed)
            if [False]*6 == [create_adj_bricks[i] or self.adj_bricks_created[i][0] for i in range(6)]:
                return {"CANCELLED"}
            scn, cm, n = get_active_context_info()
            # revert to last bricksdict
            self.undo_stack.match_python_to_blender_state()
            # push to undo stack
            if self.orig_undo_stack_length == self.undo_stack.get_length():
                self.undo_stack.undo_push("draw_adjacent", affected_ids=[cm.id])
            if not b280(): scn.update()
            self.undo_stack.iterate_states(cm)
            # get fresh copy of self.bricksdict
            self.bricksdict = get_bricksdict(cm)
            # initialize vars
            obj = context.active_object
            initial_active_obj_name = obj.name
            cm.customized = True
            keys_to_merge = set()
            update_has_custom_objs(cm, target_type)

            # get dict key details of current obj
            cur_key = get_dict_key(obj.name)
            cur_loc = get_dict_loc(self.bricksdict, cur_key)
            x0,y0,z0 = cur_loc
            # get size of current brick (e.g. [2, 4, 1])
            obj_size = self.bricksdict[cur_key]["size"]

            decriment = 0
            # check all 6 directions for action to be executed
            for i in range(6):
                # if checking beneath obj, check 3 keys below instead of 1 key below
                if i == 5 and flat_brick_type(cm.brick_type):
                    new_brick_height = self.get_new_brick_height(target_type)
                    decriment = new_brick_height - 1
                # if action should be executed (value changed in direction prop)
                if (create_adj_bricks[i] or (not create_adj_bricks[i] and self.adj_bricks_created[i][0])):
                    # add or remove bricks in all adjacent locations in current direction
                    for j,adj_dict_loc in enumerate(self.adj_locs[i]):
                        if decriment != 0:
                            adj_dict_loc = adj_dict_loc.copy()
                            adj_dict_loc[2] -= decriment
                        status = self.toggle_brick(cm, n, self.bricksdict, self.adj_locs, self.adj_bricks_created, self.dimensions, adj_dict_loc, cur_key, cur_loc, obj_size, target_type, i, j, keys_to_merge, add_brick=create_adj_bricks[i])
                        if not status["val"]:
                            self.report({status["report_type"]}, status["msg"])
                        if status["dir_bool"] is not None:
                            self.set_dir_bool(status["dir_bool"][0], status["dir_bool"][1])
                    # after ALL bricks toggled, check exposure of bricks above and below new ones
                    for j,adj_dict_loc in enumerate(self.adj_locs[i]):
                        self.bricksdict = verify_all_brick_exposures(scn, cm.zstep, adj_dict_loc.copy(), self.bricksdict, decriment=decriment + 1, z_neg=self.z_neg, z_pos=self.z_pos)

            # recalculate val for each bricksdict key in original brick
            brick_locs = [[x, y, z] for z in range(z0, z0 + obj_size[2], cm.zstep) for y in range(y0, y0 + obj_size[1]) for x in range(x0, x0 + obj_size[0])]
            for loc0 in brick_locs:
                set_brick_val(self.bricksdict, loc=loc0)

            # attempt to merge created bricks
            keys_to_update = merge_bricks(self.bricksdict, keys_to_merge, cm, target_type=target_type)

            # if bricks created on top or bottom, set exposure of original brick
            if self.z_pos or self.z_neg:
                set_brick_exposure(self.bricksdict, cm.zstep, cur_key)
                keys_to_update.add(cur_key)

            # draw created bricks
            draw_updated_bricks(cm, self.bricksdict, keys_to_update, select_created=False)

            # select original brick
            orig_obj = bpy.data.objects.get(initial_active_obj_name)
            if orig_obj: select(orig_obj, active=True)
        except:
            bricker_handle_exception()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    ################################################
    # initialization method

    def __init__(self):
        try:
            self.undo_stack = UndoStack.get_instance()
            self.orig_undo_stack_length = self.undo_stack.get_length()
            scn, cm, _ = get_active_context_info()
            obj = bpy.context.active_object
            cur_key = get_dict_key(obj.name)

            # initialize self.bricksdict
            self.bricksdict = get_bricksdict(cm)
            # initialize direction bools
            self.z_pos, self.z_neg, self.y_pos, self.y_neg, self.x_pos, self.x_neg = [False] * 6
            # initialize self.dimensions
            self.dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
            # initialize self.adj_locs
            self.adj_locs = get_adj_locs(cm, self.bricksdict, cur_key)
            # initialize self.adj_bricks_created
            self.adj_bricks_created = [[False] * len(self.adj_locs[i]) for i in range(6)]
            # initialize self.brick_type
            obj_type = self.bricksdict[cur_key]["type"]
            try:
                self.brick_type = obj_type or "STANDARD"
            except TypeError:
                pass
        except:
            bricker_handle_exception()

    ###################################################
    # class variables

    # vars
    bricksdict = {}
    adj_locs = []

    # get items for brick_type prop
    def get_items(self, context):
        items = get_available_types(by="ACTIVE", include_sizes="ALL")
        return items

    # define props for popup
    brick_type = EnumProperty(
        name="Brick Type",
        description="Type of brick to draw adjacent to current brick",
        items=get_items,
        default=None)
    z_pos = BoolProperty(name="+Z (Top)", default=False)
    z_neg = BoolProperty(name="-Z (Bottom)", default=False)
    x_pos = BoolProperty(name="+X (Front)", default=False)
    x_neg = BoolProperty(name="-X (Back)", default=False)
    y_pos = BoolProperty(name="+Y (Right)", default=False)
    y_neg = BoolProperty(name="-Y (Left)", default=False)

    #############################################
    # class methods

    def set_dir_bool(self, idx, val):
        if idx == 0: self.x_pos = val
        elif idx == 1: self.x_neg = val
        elif idx == 2: self.y_pos = val
        elif idx == 3: self.y_neg = val
        elif idx == 4: self.z_pos = val
        elif idx == 5: self.z_neg = val

    @staticmethod
    def get_brickd(bricksdict, dkl):
        """ set up adj_brick_d """
        adjacent_key = list_to_str(dkl)
        try:
            brick_d = bricksdict[adjacent_key]
            return adjacent_key, brick_d
        except:
            return adjacent_key, False

    @staticmethod
    def get_new_brick_height(target_type):
        new_brick_height = 1 if target_type in get_brick_types(height=1) else 3
        return new_brick_height

    @staticmethod
    def get_new_coord(cm, bricksdict, origKey, orig_loc, new_key, new_loc, dimensions):
        full_d = Vector((dimensions["width"], dimensions["width"], dimensions["height"]))
        if cm.brick_type == "CUSTOM": full_d = vec_mult(full_d, cm.dist_offset)
        cur_co = bricksdict[origKey]["co"]
        new_co = Vector(cur_co)
        loc_diff = Vector((new_loc[0] - orig_loc[0], new_loc[1] - orig_loc[1], new_loc[2] - orig_loc[2]))
        new_co += vec_mult(full_d, loc_diff)
        new_co.x += dimensions["gap"] * (loc_diff.x - (0 if loc_diff.x == 0 else 1)) + (0 if loc_diff.x == 0 else dimensions["gap"])
        new_co.y += dimensions["gap"] * (loc_diff.y - (0 if loc_diff.y == 0 else 1)) + (0 if loc_diff.y == 0 else dimensions["gap"])
        new_co.z += dimensions["gap"] * (loc_diff.z - (0 if loc_diff.z == 0 else 1)) + (0 if loc_diff.z == 0 else dimensions["gap"])
        return tuple(new_co)

    @staticmethod
    def is_brick_already_created(adj_locs, adj_bricks_created, brick_num, side):
        return not (brick_num == len(adj_locs[side]) - 1 and
                    not any(adj_bricks_created[side])) # evaluates True if all values in this list are False

    @staticmethod
    def toggle_brick(cm, n, bricksdict, adj_locs, adj_bricks_created, dimensions, adjacent_loc, cur_key, cur_loc, obj_size, target_type, side, brick_num, keys_to_merge, is_placeholder_brick=False, add_brick=True):
        # if brick height is 3 and 'Plates' in cm.brick_type
        new_brick_height = BRICKER_OT_draw_adjacent.get_new_brick_height(target_type)
        check_two_more_above = "PLATES" in cm.brick_type and new_brick_height == 3
        dir_bool = None
        cur_brick_d = bricksdict[cur_key]
        draw_threshold = get_threshold(cm)

        adjacent_key, adj_brick_d = BRICKER_OT_draw_adjacent.get_brickd(bricksdict, adjacent_loc)

        # get duplicate of nearest_intersection tuple
        ni = cur_brick_d["near_intersection"]
        ni = tuple(ni) if type(ni) in [tuple, list] else ni
        # if key doesn't exist in bricksdict, create it
        if not adj_brick_d:
            co = BRICKER_OT_draw_adjacent.get_new_coord(cm, bricksdict, cur_key, cur_loc, adjacent_key, adjacent_loc, dimensions)
            bricksdict[adjacent_key] = create_bricksdict_entry(
                name=              "Bricker_%(n)s__%(adjacent_key)s" % locals(),
                loc=               adjacent_loc,
                co=                co,
                near_face=         cur_brick_d["near_face"],
                near_intersection= ni,
                mat_name=          cur_brick_d["mat_name"],
                custom_mat_name=   cur_brick_d["custom_mat_name"],
            )
            adj_brick_d = bricksdict[adjacent_key]
            # dir_bool = [side, False]
            # return {"val":False, "dir_bool":dir_bool, "report_type":"WARNING", "msg":"Matrix not available at the following location: %(adjacent_key)s" % locals()}

        # if brick exists there
        if adj_brick_d["draw"] and not (add_brick and adj_bricks_created[side][brick_num]):
            # if attempting to add brick
            if add_brick:
                # reset direction bool if no bricks could be added
                if not BRICKER_OT_draw_adjacent.is_brick_already_created(adj_locs, adj_bricks_created, brick_num, side):
                    dir_bool = [side, False]
                return {"val":False, "dir_bool":dir_bool, "report_type":"INFO", "msg":"Brick already exists in the following location: %(adjacent_key)s" % locals()}
            # if attempting to remove brick
            elif adj_brick_d["created_from"] == cur_key:
                # update bricksdict entries for brick being removed
                x0, y0, z0 = adjacent_loc
                brick_keys = [list_to_str((x0, y0, z0 + z)) for z in range((cm.zstep + 2) % 4 if side in (4, 5) else 1)]
                reset_bricksdict_entries(bricksdict, brick_keys)
                adj_bricks_created[side][brick_num] = False
                return {"val":True, "dir_bool":dir_bool, "report_type":None, "msg":None}
        # if brick doesn't exist there
        else:
            # if attempting to remove brick
            if not add_brick:
                return {"val":False, "dir_bool":dir_bool, "report_type":"INFO", "msg":"Brick does not exist in the following location: %(adjacent_key)s" % locals()}
            # check if locs above current are available
            cur_type = adj_bricks_created[side][brick_num] if adj_bricks_created[side][brick_num] else "STANDARD"
            if check_two_more_above:
                x0, y0, z0 = adjacent_loc
                for z in range(1, 3):
                    new_key = list_to_str((x0, y0, z0 + z))
                    # if brick drawn in next loc and not just rerunning based on new direction selection
                    if (new_key in bricksdict and bricksdict[new_key]["draw"] and
                        (not BRICKER_OT_draw_adjacent.is_brick_already_created(adj_locs, adj_bricks_created, brick_num, side) or
                         cur_type not in get_brick_types(height=3)) and not
                         (z == 2 and cur_type in get_brick_types(height=1) and target_type not in get_brick_types(height=1))):
                        # reset values at failed location, in case brick was previously drawn there
                        adj_bricks_created[side][brick_num] = False
                        adj_brick_d["draw"] = False
                        dir_bool = [side, False]
                        return {"val":False, "dir_bool":dir_bool, "report_type":"INFO", "msg":"Brick already exists in the following location: %(new_key)s" % locals()}
                    elif side in (4, 5):
                        keys_to_merge.add(new_key)
            # update dictionary of locations above brick
            if flat_brick_type(cm.brick_type) and side in (4, 5):
                update_brick_size_and_dict(dimensions, n, bricksdict, [1, 1, new_brick_height], adjacent_key, adjacent_loc, draw_threshold, dec=2 if side == 5 else 0, cur_type=cur_type, target_type=target_type, created_from=cur_key)
            # update dictionary location of adjacent brick created
            adj_brick_d["draw"] = should_draw_brick(adj_brick_d, 0) # draw_threshold)
            adj_brick_d["type"] = target_type
            adj_brick_d["flipped"] = cur_brick_d["flipped"]
            adj_brick_d["rotated"] = cur_brick_d["rotated"]
            set_brick_val(bricksdict, loc=adjacent_loc, key=adjacent_key)
            adj_brick_d["size"] = [1, 1, new_brick_height if side in (4, 5) else cm.zstep]
            adj_brick_d["parent"] = "self"
            adj_brick_d["rgba"] = cur_brick_d["rgba"]
            adj_brick_d["mat_name"] = cur_brick_d["mat_name"] if adj_brick_d["mat_name"] == "" else adj_brick_d["mat_name"]
            adj_brick_d["custom_mat_name"] = cur_brick_d["custom_mat_name"]
            adj_brick_d["near_face"] = adj_brick_d["near_face"] or cur_brick_d["near_face"]
            adj_brick_d["near_intersection"] = adj_brick_d["near_intersection"] or ni
            if is_placeholder_brick:
                adj_brick_d["top_exposed"] = True
                adj_brick_d["bot_exposed"] = False
            else:
                set_brick_exposure(bricksdict, cm.zstep, adjacent_key)
            adj_brick_d["created_from"] = cur_key
            keys_to_merge.add(adjacent_key)
            # set adj_bricks_created to target brick type for current side
            adj_bricks_created[side][brick_num] = target_type

            return {"val":True, "dir_bool":dir_bool, "report_type":None, "msg":None}

    #############################################
