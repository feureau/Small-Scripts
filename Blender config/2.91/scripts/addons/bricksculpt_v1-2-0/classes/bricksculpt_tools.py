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
import bmesh
import math

# Blender imports
import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.types import Operator, SpaceView3D, bpy_struct
from bpy.props import *

# Module imports
from ..functions import *



class BricksculptTools:

    #############################################

    def add_brick(self, cm, n, cur_key, cur_loc):
        cur_brick_d = self.bricksdict[cur_key]
        prefs = get_addon_preferences()
        # get difference between intersection loc and object loc
        loc_diff = self.loc - transform_to_world(Vector(cur_brick_d["co"]), self.parent.matrix_world, self.junk_bme)
        loc_diff = transform_to_local(loc_diff, self.parent.matrix_world)
        next_loc = get_nearby_loc_from_vector(loc_diff, cur_loc, self.dimensions, cm.zstep, cur_brick_d["size"], width_divisor=3.15 if self.brick_type in self.brick_fns.types.get_round_brick_types() else 2.05)
        if self.layer_solod is not None and next_loc[2] not in range(self.layer_solod, self.layer_solod + 3 // cm.zstep):
            return None, None
        # draw brick at next_loc location
        next_key, adj_brick_d = self.BRICKER_OT_draw_adjacent.get_brickd(self.bricksdict, next_loc)
        if not adj_brick_d or self.bricksdict[next_key]["val"] == 0 or (prefs.allow_editing_of_internals and self.bricksdict[next_key]["val"] != 1 and not self.bricksdict[next_key]["draw"]):
            self.adj_locs = self.get_adj_locs(cm, self.bricksdict, cur_key)
            # add brick at next_key location
            status = self.BRICKER_OT_draw_adjacent.toggle_brick(cm, n, self.bricksdict, self.adj_locs, [[False]], self.dimensions, next_loc, cur_key, cur_loc, cur_brick_d["size"], self.brick_type, 0, 0, self.keys_to_merge_on_commit, is_placeholder_brick=True)
            if not status["val"]:
                self.report({status["report_type"]}, status["msg"])
            self.keys_to_update_on_release.add(next_key)
            self.all_updated_keys.add(cur_key)
            # update 'val' for adjacent bricksdict entries recursively
            self.OBJECT_OT_delete_override.update_adj_bricksdicts(self.bricksdict, cm.zstep, cur_key, self.get_dict_loc(self.bricksdict, cur_key), self.draw_threshold)
            # draw created bricks
            # self.draw_updated_bricks(cm, self.bricksdict, [next_key], action="adding new brick", select_created=False, placeholder_meshes=True)
            self.draw_temp_bricks([next_key])
            return next_key, next_loc
        return None, None

    def remove_brick(self, context, cm, n, event, cur_key, cur_loc):
        shallow_delete = cur_key in self.keys_to_update_on_release
        deep_delete = event.shift and self.obj.name not in self.protected_until_release
        if shallow_delete or deep_delete:
            # split bricks and mark near key for removal
            brick_keys, near_key = self.split_brick_and_get_nearest_1x1(cm, n, cur_key, cur_loc, self.bricksdict[cur_key]["size"])
            # re-merge all except removed key
            merged_keys = self.bricker_merge_bricks(self.bricksdict, brick_keys.difference({near_key}), cm, any_height=True)
            # update data structs as necessary
            self.all_updated_keys |= brick_keys
            self.keys_to_update_on_release |= brick_keys
            self.keys_to_update_on_release.discard(near_key)
            self.keys_to_merge_on_commit |= brick_keys
            self.keys_to_merge_on_commit.discard(near_key)
            # initialize vars
            cur_brick_d = self.bricksdict[near_key]
            near_loc = self.get_dict_loc(self.bricksdict, near_key)
            # reset bricksdict entry for removed key
            self.reset_bricksdict_entries(self.bricksdict, [near_key])
            # update bricksdict entries for adjacent keys
            all_keys_to_update, new_keys, newly_exposed_keys = self.OBJECT_OT_delete_override.update_adj_bricksdicts(self.bricksdict, cm.zstep, near_key, near_loc, self.draw_threshold)
            self.all_updated_keys |= all_keys_to_update
            if deep_delete:
                self.protected_until_release |= set(self.bricksdict[k]["name"] for k in newly_exposed_keys)
            self.keys_to_merge_on_commit |= new_keys
            # delete removed brick
            brick = bpy.data.objects.get(cur_brick_d["name"])
            if brick is not None:
                delete(brick)
            # draw created bricks
            self.draw_updated_bricks(cm, self.bricksdict, brick_keys.union(all_keys_to_update), action="updating surrounding bricks", select_created=False, placeholder_meshes=True)
            return near_key, near_loc
        return None, None

    def change_material(self, cm, n, cur_key, cur_loc, mat_name):
        cur_brick_d = self.bricksdict[cur_key]
        obj_size = cur_brick_d["size"]
        if max(obj_size[:2]) > 1 or obj_size[2] > cm.zstep:
            if cur_brick_d["mat_name"] == mat_name:
                return None, None
            parent_key = cur_key
            brick_keys, cur_key = self.split_brick_and_get_nearest_1x1(cm, n, cur_key, cur_loc, obj_size)
            cur_brick_d = self.bricksdict[cur_key]  # reset because key was updated
            self.bricksdict[parent_key]["orig_keys"] = brick_keys
        else:
            if "orig_keys" in cur_brick_d.keys():
                cur_key = self.get_nearest_loc_to_cursor(cur_brick_d["orig_keys"])
                cur_brick_d = self.bricksdict[cur_key]  # reset because key was updated
            if cur_brick_d["mat_name"] == mat_name:
                return None, None
            brick_keys = {cur_key}
        cur_brick_d["mat_name"] = mat_name
        cur_brick_d["custom_mat_name"] = True
        self.keys_to_update_on_release |= brick_keys
        self.keys_to_merge_on_commit |= brick_keys
        self.all_updated_keys |= brick_keys
        # draw created bricks
        # self.draw_updated_bricks(cm, self.bricksdict, brick_keys, action="updating material", select_created=False, placeholder_meshes=True)
        self.draw_temp_bricks([cur_key])
        return cur_key, cur_loc

    def get_material(self, scn, cm, n, cur_key, event):
        # get the current bricksdict entry
        if "orig_keys" in self.bricksdict[cur_key].keys():
            near_key = self.get_nearest_loc_to_cursor(self.bricksdict[cur_key]["orig_keys"])
            cur_brick_d = self.bricksdict[near_key]
        else:
            cur_brick_d = self.bricksdict[cur_key]
        # don't get a material if it's unnecessary
        if scn.bricksculpt.paintbrush_mat is not None and cur_brick_d["mat_name"] == scn.bricksculpt.paintbrush_mat.name:
            return
        # get the new material
        scn.bricksculpt.paintbrush_mat = bpy.data.materials.get(cur_brick_d["mat_name"])
        if scn.bricksculpt.paintbrush_mat is not None:
            self.report({"INFO"}, "Picked material: " + cur_brick_d["mat_name"])
        else:
            self.report({"WARNING"}, "No valid material found")
        self.set_cursor_type(event)
        tag_redraw_areas("VIEW_3D")

    def split_brick(self, cm, event, cur_key, cur_loc):
        cur_brick_d = self.bricksdict[cur_key]
        brick = bpy.data.objects.get(cur_brick_d["name"])
        if (event.alt and max(cur_brick_d["size"][:2]) > 1) or (event.shift and cur_brick_d["size"][2] > 1):
            brick_keys = self.brick_fns.bricks.split_brick(self.bricksdict, cur_key, cm.zstep, cm.brick_type, loc=cur_loc, v=event.shift, h=event.alt)
            self.all_updated_keys |= brick_keys
            self.keys_to_update_on_release.difference_update(brick_keys)
            self.keys_to_merge_on_commit.difference_update(brick_keys)
            # set material for all split keys to material of original brick
            for k in brick_keys:
                self.bricksdict[k]["mat_name"] = cur_brick_d["mat_name"]
                self.bricksdict[k]["custom_mat_name"] = True
            # remove large brick
            brick = bpy.data.objects.get(cur_brick_d["name"])
            delete(brick)
            # draw split bricks
            self.draw_updated_bricks(cm, self.bricksdict, brick_keys, action="splitting bricks", select_created=True, placeholder_meshes=True, run_pre_merge=False)
            # hide(brick)
            # self.draw_temp_bricks(brick_keys)
        else:
            select(brick)

    def merge_bricks(self, cm, source_name, cur_key=None, cur_loc=None, mode="DRAW", state="DRAG"):
        if state == "DRAG":
            # TODO: Light up bricks as they are selected to be merged
            self.parent_locs_to_merge_on_release.append((cur_loc, cur_key))
            select(self.obj)
        elif state == "RELEASE":
            scn, cm, n = self.get_active_context_info(cm=cm)
            # assemble keys_to_update_on_release
            for pl, pk in self.parent_locs_to_merge_on_release:
                brick_keys = self.get_keys_in_brick(self.bricksdict, self.bricksdict[pk]["size"], cm.zstep, key=pk)
                self.keys_to_update_on_release |= brick_keys
                self.all_updated_keys |= brick_keys
                self.keys_to_merge_on_commit.difference_update(brick_keys)
            self.parent_locs_to_merge_on_release = []
            self.keys_to_update_on_release = set(k for k in self.keys_to_update_on_release if self.bricksdict[k]["draw"])
            # merge those keys
            if len(self.keys_to_update_on_release) > (1 if mode == "MERGE_SPLIT" else 0):
                # delete outdated bricks
                for key in self.keys_to_update_on_release:
                    brick_name = "Bricker_%(source_name)s__%(key)s" % locals()
                    delete(bpy.data.objects.get(brick_name))
                # split up bricks
                self.brick_fns.bricks.split_bricks(self.bricksdict, cm.zstep, keys=self.keys_to_update_on_release)
                # merge bricks after they've been split
                merged_keys = self.bricker_merge_bricks(self.bricksdict, self.keys_to_update_on_release, cm, any_height=True, merge_inconsistent_mats=self.prefs.merge_inconsistent_mats if mode == "MERGE_SPLIT" else False)
                self.all_updated_keys |= merged_keys
                # draw merged bricks
                created_bricks = self.draw_updated_bricks(cm, self.bricksdict, self.keys_to_update_on_release, action="merging bricks", select_created=False, placeholder_meshes=True)
                # unhide from ray cast view layer
                for brick in created_bricks:
                    brick.hide_set(False, view_layer=self.ray_cast_view_layer)
            else:
                deselect_all()
            # reset lists
            if mode == "MERGE_SPLIT":
                self.keys_to_update_on_release = set()

    def run_post_action_cleanup(self, context, attempt_merge=True):
        scn, cm, n = self.get_active_context_info(context)
        self.last_paintbrush_mat = scn.bricksculpt.paintbrush_mat
        clear_geom(self.junk_mesh)
        # store object name before merge, in case object is deleted during merge
        last_target = self.obj
        if self.mode == "PAINT" and attempt_merge and last_target:
            obj_name = self.obj.name
        # attempt to merge the bricks
        if attempt_merge:
            self.merge_bricks(cm, n, mode=self.mode, state="RELEASE")
        # handle paint-specific things
        if self.mode == "PAINT":
            # pop orig_keys from keys to update on release
            for k in self.keys_to_update_on_release:
                self.bricksdict[k].pop("orig_keys", None)
            # update self.obj if the object was deleted during the merge
            if attempt_merge and last_target:
                targetted_key = self.get_dict_key(obj_name)
                if targetted_key in self.keys_to_update_on_release:
                    self.obj = bpy.data.objects.get(self.bricksdict[targetted_key]["name"])
        tag_redraw_areas("VIEW_3D")

    def move_solod_layer(self, event, zstep:int):
        if self.layer_solod is None:
            if event.type.startswith("UP"):
                layer_to_solo = self.z_levels[0]
            else:
                layer_to_solo = self.z_levels[-1]
        elif event.type.startswith("UP"):
            layer_to_solo = min(self.layer_solod + 1, self.z_levels[-1])
        elif event.type.startswith("DOWN"):
            layer_to_solo = max(self.layer_solod - 1, self.z_levels[0])
        self.solo_layer(layer_to_solo, zstep)

    @timed_call(label="Solod Layer")
    def solo_layer(self, layer:int, zstep:int):
        bricks_to_hide = set()
        bricks_to_solo = set()
        for key, brick_d in self.bricksdict.items():
            if brick_d["parent"] != "self" or not brick_d["draw"]:
                continue
            brick = bpy.data.objects[brick_d["name"]]
            loc = self.get_dict_loc(self.bricksdict, key)
            if loc[2] > layer or loc[2] + brick_d["size"][2] / zstep <= layer:
                bricks_to_hide.add(brick)
            else:
                bricks_to_solo.add(brick)
        # unhide bricks on current layer
        new_solod_bricks = bricks_to_solo.intersection(self.hidden_bricks)
        unhide(new_solod_bricks, render=False)
        self.hidden_bricks.difference_update(new_solod_bricks)
        # hide bricks not on current layer
        new_hidden_bricks = bricks_to_hide - self.hidden_bricks
        hide(new_hidden_bricks, render=False)
        self.hidden_bricks |= new_hidden_bricks
        # mark this layer as the current solod layer
        self.layer_solod = layer

    def unhide_all(self):
        unhide(self.hidden_bricks, render=False)
        self.hidden_bricks = set()

    def split_brick_and_get_nearest_1x1(self, cm, n, cur_key, cur_loc, obj_size):
        brick_keys = self.brick_fns.bricks.split_brick(self.bricksdict, cur_key, cm.zstep, cm.brick_type, loc=cur_loc, v=True, h=True)
        # brick = bpy.data.objects.get(self.bricksdict[cur_key]["name"])
        # delete(brick)
        near_key = self.get_nearest_loc_to_cursor(brick_keys)
        return brick_keys, near_key

    def draw_temp_bricks(self, keys:set, stud=True, circle_verts=12):  # , mat_name=None):
        bm = bmesh.new()
        bm.from_mesh(self.junk_mesh)
        for cur_key in keys:
            cur_brick_d = self.bricksdict[cur_key]
            if self.brick_type.startswith("CUSTOM"):
                brick_mesh = self.custom_meshes[int(self.brick_type[-1])]
            else:
                brick_mesh = self.get_brick_data(cur_brick_d, self.dimensions_temp, cur_brick_d["type"], brick_size=cur_brick_d["size"], circle_verts=circle_verts, use_stud=stud).copy()
            brick_center = self.brick_fns.bricks.get_brick_center(self.bricksdict, cur_key, self.zstep)
            brick_mesh.transform(Matrix.Translation(brick_center))
            # keep track of mats already used
            # mat_name = mat_name or cur_brick_d["mat_name"]
            mat_name = cur_brick_d["mat_name"]
            mat_idx = get_mat_idx(self.junk_obj, mat_name)
            for p in brick_mesh.polygons:
                p.material_index = mat_idx
            # combine meshes
            bm.from_mesh(brick_mesh)
        bm.to_mesh(self.junk_mesh)
        tag_redraw_areas("VIEW_3D")

    def get_nearest_loc_to_cursor(self, keys:set):
        # get difference between intersection loc and object loc
        min_diff = None
        for k in keys:
            brick_loc = transform_to_world(Vector(self.bricksdict[k]["co"]), self.parent.matrix_world, self.junk_bme)
            loc_diff = abs(self.loc[0] - brick_loc[0]) + abs(self.loc[1] - brick_loc[1]) + abs(self.loc[2] - brick_loc[2])
            if min_diff is None or loc_diff < min_diff:
                min_diff = loc_diff
                cur_key = k
        return cur_key

    def commit_changes(self, context):
        scn, cm, _ = self.get_active_context_info(context)
        # deselect any objects left selected, and show all objects
        deselect_all()
        self.unhide_all()
        # attempt to merge bricks queued for merge on commit
        self.keys_to_merge_on_commit = set(k for k in self.keys_to_merge_on_commit if self.bricksdict[k]["draw"])
        if self.brick_fns.types.mergable_brick_type(self.brick_type) and len(self.keys_to_merge_on_commit) > 1:
            # split up bricks
            self.brick_fns.bricks.split_bricks(self.bricksdict, cm.zstep, keys=self.keys_to_merge_on_commit)
            # merge split bricks
            merged_keys = self.bricker_merge_bricks(self.bricksdict, self.keys_to_merge_on_commit, cm, target_type=self.brick_type, any_height=cm.brick_type == "BRICKS_AND_PLATES")
        else:
            merged_keys = self.keys_to_merge_on_commit
        # remove 1x1 bricks merged into another brick
        for k in self.keys_to_merge_on_commit:
            delete(None if k in merged_keys else bpy.data.objects.get(self.bricksdict[k]["name"]))
        # set exposure of created/updated bricks
        keys_to_update = set(k for k in merged_keys.union(self.all_updated_keys) if self.bricksdict[k]["draw"])
        # draw updated bricks
        self.draw_updated_bricks(cm, self.bricksdict, keys_to_update, action="committing changes", select_created=False, run_pre_merge=False)
        # run final mode cleanups
        self.done(context)

    def cancel_changes(self, context):
        scn, cm, _ = self.get_active_context_info(context)
        reverted_bricksdict = self.undo_stack.revert_to_last_state(cm.id)  # may cause problems?
        cm.customized = self.last_customized
        affected_keys = self.all_updated_keys
        keys_to_update = set()
        for k in affected_keys:
            if k in reverted_bricksdict and reverted_bricksdict[k]["parent"] == "self" and reverted_bricksdict[k]["draw"]:
                keys_to_update.add(k)
            else:
                delete(bpy.data.objects.get(self.bricksdict[k]["name"]))
        if len(keys_to_update) > 0:
            self.draw_updated_bricks(cm, reverted_bricksdict, keys_to_update, action="reverting changes", select_created=False)
        scn.bricksculpt.cancel_session_changes = False
        # run final mode cleanups
        self.done(context)

    #############################################
