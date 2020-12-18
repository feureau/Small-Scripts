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
import importlib

# Blender imports
import bpy
import bgl
from bpy.types import Operator
from bpy.props import *

# Module imports
from .bricksculpt_framework import *
from .bricksculpt_tools import *
from .bricksculpt_drawing import *
from ..functions import *


class BRICKSCULPT_OT_run_tool(Operator, BricksculptFramework, BricksculptTools, BricksculptDrawing):
    """Run the BrickSculpt editing tool suite"""
    bl_idname = "bricksculpt.run_tool"
    bl_label = "BrickSculpt Session"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = bpy.context.scene
        return is_bricker_installed() and bpy.props.bricker_initialized and scn.cmlist_index != -1

    def execute(self, context):
        try:
            scn, cm, _ = self.get_active_context_info(context)
            if scn.bricksculpt.running_active_session:
                return {"CANCELLED"}
            if self.mode == "DRAW" and self.brick_type == "":
                self.report({"WARNING"}, "Please choose a target brick type")
                return {"CANCELLED"}
            self.ui_start()
            scn.bricksculpt.running_active_session = True
            self.undo_stack.iterate_states(cm)
            cm.customized = True
            cm.build_is_dirty = False
            # get fresh copy of self.bricksdict
            self.bricksdict = self.bricksdict_fns.storage.get_bricksdict(cm)
            self.z_levels = sorted(self.get_keys_dict(self.bricksdict).keys())
            # get some random brick and store its uv_image pixels to the cache (that way this image won't have to load to cache when the sculpt tool is first used)
            brick_d = self.bricksdict[next(iter(self.bricksdict.keys()))]
            if brick_d["near_face"] is not None:
                image = get_uv_image(cm.source_obj, brick_d["near_face"])
                if image is not None:
                    color_depth = cm.color_depth if cm.color_snap == "RGB" else -1
                    get_pixels_cache(image, color_depth=color_depth)
            # append brick materials if not yet appended
            if self.prefs.auto_append_abs_materials and self.brick_materials_installed() and not self.brick_materials_imported():
                bpy.ops.abs.append_materials()
            # set up junk object
            self.junk_obj = junk_obj("BrickSculpt_temp_bricks", self.junk_mesh)
            clear_geom(self.junk_mesh)
            self.apply_brick_mesh_settings(self.junk_mesh)
            try:
                link_object(self.junk_obj)
            except:
                pass
            self.junk_obj.location = (0, 0, 0)
            self.junk_obj.parent = cm.parent_obj
            if len(bpy.data.materials) > 0:
                self.junk_obj.data.materials.clear()
                self.junk_obj.data.materials.append(bpy.data.materials[0])
                self.junk_obj.material_slots[0].material = None
            for mat in self.get_materials_in_model(cm):
                self.junk_obj.data.materials.append(mat)
            # setup new view_layer with only bricks from model
            self.ray_cast_view_layer = scn.view_layers.new("BrickSculpt_ray_cast_layer")
            # hide objects that aren't part of the Bricker model
            for obj in scn.objects:
                if not (obj.is_brick and obj.name.startswith("Bricker_{}".format(cm.source_obj.name)) and obj.visible_get()):
                    obj.hide_set(True, view_layer=self.ray_cast_view_layer)
                    if obj.visible_get():
                        obj.hide_set(True)
                        self.hidden_objects.add(obj)
            # set visibility for junk object
            self.junk_obj.hide_set(True, view_layer=self.ray_cast_view_layer)
            self.junk_obj.hide_set(False)
            # create modal handler
            wm = context.window_manager
            wm.modal_handler_add(self)
            # self._timer = wm.event_timer_add(0.01, window=bpy.context.window)
            return {"RUNNING_MODAL"}
        except:
            bricksculpt_handle_exception()
            self.cancel(context)
            return {"CANCELLED"}

    ################################################
    # initialization method

    def __init__(self):
        # import bricker module and define bricker functions
        bricker = importlib.import_module(bpy.props.bricker_module_name)
        self.bricksdict_fns = bricker.functions.bricksdict
        self.brick_fns = bricker.functions.brick
        self.get_active_context_info = bricker.functions.general.get_active_context_info
        self.get_parent_key = bricker.functions.general.get_parent_key
        self.get_brick_center = bricker.functions.brick.bricks.get_brick_center
        self.create_bricksdict_entry = bricker.functions.bricksdict.generate.create_bricksdict_entry
        self.draw_updated_bricks = bricker.functions.brickify_utils.draw_updated_bricks
        self.get_materials_in_model = bricker.functions.mat_utils.get_materials_in_model
        self.brick_materials_installed = bricker.functions.mat_utils.brick_materials_installed
        self.brick_materials_imported = bricker.functions.mat_utils.brick_materials_imported
        self.apply_brick_mesh_settings = bricker.functions.make_bricks_utils.apply_brick_mesh_settings
        self.get_adj_locs = bricker.functions.customize_utils.get_adj_locs
        self.get_dict_key = bricker.functions.general.get_dict_key
        self.get_dict_loc = bricker.functions.general.get_dict_loc
        self.get_keys_dict = bricker.functions.general.get_keys_dict
        self.get_keys_in_brick = bricker.functions.general.get_keys_in_brick
        self.get_brick_data = bricker.functions.make_bricks_utils.get_brick_data
        self.BRICKER_OT_draw_adjacent = bricker.operators.customization_tools.draw_adjacent.BRICKER_OT_draw_adjacent
        self.bricker_merge_bricks = bricker.functions.customize_utils.merge_bricks
        self.reset_bricksdict_entries = bricker.functions.customize_utils.reset_bricksdict_entries
        self.OBJECT_OT_delete_override = bricker.operators.overrides.delete_object.OBJECT_OT_delete_override
        # init vars
        scn, cm, n = self.get_active_context_info()
        # push to undo stack
        self.undo_stack = bricker.lib.undo_stack.UndoStack.get_instance()
        self.undo_stack.undo_push("bricksculpt_mode", affected_ids=[cm.id])
        # initialize vars
        self.hidden_objects = set()
        self.protected_until_release = set()
        self.parent_locs_to_merge_on_release = list()
        self.keys_to_update_on_release = set()
        self.keys_to_merge_on_commit = set()
        self.all_updated_keys = set()
        self.last_customized = cm.customized
        self.last_build_is_dirty = cm.build_is_dirty
        self.dimensions = self.brick_fns.bricks.get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
        self.dimensions_temp = self.brick_fns.bricks.get_brick_dimensions(cm.brick_height * 1.05, cm.zstep, cm.gap)
        self.draw_threshold = bricker.functions.bricksdict.generate.get_threshold(cm)
        self.obj = None
        self.loc = None
        self.prefs = get_addon_preferences()
        self.blender_prefs = get_preferences()
        self.cm_idx = cm.idx
        self.zstep = cm.zstep
        self.brick_height = cm.brick_height
        self.brick_type = self.brick_fns.types.get_brick_type(cm.brick_type)
        self.custom_meshes = (cm.custom_mesh1, cm.custom_mesh2, cm.custom_mesh3)
        self.hidden_bricks = set()
        self.last_hide_key = None
        self.last_hide_loc = None
        self.release_time = 0
        self.vertical = False
        self.horizontal = True
        self.mouse = Vector((0, 0))
        self.last_mouse = Vector((0, 0))
        self.mouse_travel = 0
        self.mode_switched = False
        self.ray_cast_view_layer = None
        self.junk_bme = bmesh.new()
        self.last_paintbrush_mat = scn.bricksculpt.paintbrush_mat
        self.parent = bpy.data.objects.get("Bricker_%(n)s_parent" % locals())
        deselect_all()
        self.junk_mesh = junk_mesh("BrickSculpt_temp_mesh")
        # ui properties
        self.left_click = False
        self.double_ctrl = False
        self.initialize_cursor = True
        self.cursor_text = ""
        self.cursor_type = ""
        self.last_cursor_type = "DEFAULT"
        self.ctrl_click_time = -1
        self.layer_solod = None
        self.possible_ctrl_disable = False
        self.draw_handlers = list()
        # context properties for CC interface
        self._area = bpy.context.area
        self._space = bpy.context.space_data
        self._window = bpy.context.window
        self._screen = bpy.context.screen
        self._region = bpy.context.region
        # self.points = [(math.cos(d*math.pi/180.0),math.sin(d*math.pi/180.0)) for d in range(0,361,10)]
        # self.ox = Vector((1,0,0))
        # self.oy = Vector((0,1,0))
        # self.oz = Vector((0,0,1))
        # self.radius = 50.0
        # self.falloff = 1.5
        # self.strength = 0.5
        # self.scale = 0.0
        # self.color = (1,1,1)
        # self.region = bpy.context.region
        # self.r3d = bpy.context.space_data.region_3d
        # self.clear_ui_mouse_pos()

    ###################################################
    # class variables

    # # get items for brick_type prop
    # def get_items(self, context):
    #     scn, cm, _ = self.get_active_context_info(context)
    #     legal_bs = bpy.props.bricker_legal_brick_sizes
    #     items = [iter_from_type(typ) for typ in legal_bs[cm.zstep]]
    #     if cm.zstep == 1:
    #         items += [iter_from_type(typ) for typ in legal_bs[3]]
    #     # items = get_available_types(by="ACTIVE", include_sizes="ALL")
    #     return items
    #
    # # define props for popup
    # brick_type = bpy.props.EnumProperty(
    #     name="Brick Type",
    #     description="Type of brick to draw adjacent to current brick",
    #     items=get_items,
    #     default=None)

    # define props for popup
    mode = EnumProperty(
        items=[
            ("DRAW", "DRAW", "", 0),
            ("MERGE_SPLIT", "MERGE/SPLIT", "", 1),
            ("PAINT", "PAINT", "", 2),
            ("HIDE", "HIDE", "", 3),
        ],
    )

    ###################################################
    # class methods

    def get_cur_loc_and_key(self):
        if self.near_key is not None:
            cur_key = self.near_key
        else:
            cur_key = self.get_dict_key(self.obj.name)
        cur_loc = self.get_dict_loc(self.bricksdict, cur_key)
        return cur_key, cur_loc

    def get_nearest_loc(self, key, loc, cm):
        obj_size = self.bricksdict[key]["size"]
        brick_keys = self.get_keys_in_brick(self.bricksdict, obj_size, cm.zstep, loc=loc)
        near_key = self.get_nearest_loc_to_cursor(brick_keys)
        near_loc = self.get_dict_loc(self.bricksdict, near_key)
        return near_loc

    def done(self, context):
        scn = context.scene
        # wm.event_timer_remove(self._timer)
        scn.bricksculpt.running_active_session = False
        self.ui_end()
        try:
            unlink_object(self.junk_obj)
        except:
            pass
        if self.ray_cast_view_layer is not None:
            scn.view_layers.remove(self.ray_cast_view_layer)
        bpy.context.window.cursor_set("DEFAULT")
        # set cmlist props
        scn, cm, n = self.get_active_context_info(context)
        cm.build_is_dirty = self.last_build_is_dirty
        # unhide any hidden objects
        for obj in self.hidden_objects:
            obj.hide_set(False)

    ###################################################
