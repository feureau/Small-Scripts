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
import time
import sys

# Blender imports
import bpy
import bmesh
from mathutils import Vector, Euler
props = bpy.props

# Module imports
from ..functions import *
from .cache import *
from ..subtrees.background_processing.classes.job_manager import JobManager


def get_model_type(cm):
    """ return 'MODEL' if model_created, 'ANIMATION' if animated """
    if cm.animated:
        model_type = "ANIMATION"
    elif cm.model_created:
        model_type = "MODEL"
    else:
        raise AttributeError("Brick object is in unexpected state")
    return model_type


class BRICKER_OT_delete_model(bpy.types.Operator):
    """Delete brickified model (restores original source object)"""
    bl_idname = "bricker.delete_model"
    bl_label = "Delete Brickified model from Blender"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        return True

    def execute(self, context):
        wm = context.window_manager
        wm.bricker_running_blocking_operation = True
        try:
            cm = get_active_context_info(context)[1]
            self.undo_stack.iterate_states(cm)
            self.run_full_delete()
        except:
            bricker_handle_exception()
        wm.bricker_running_blocking_operation = False

        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        cm = get_active_context_info()[1]
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push("delete", affected_ids=[cm.id])

    #############################################
    # class methods

    @classmethod
    def clean_up(cls, model_type, cm=None, skip_source=False, skip_dupes=False, skip_parents=False, skip_bricks=False, skip_trans_and_anim_data=True, preserved_frames=None, source_name=None):
        """ externally callable cleanup function for bricks, source, dupes, and parents """
        # set up variables
        scn, cm, n = get_active_context_info(cm=cm)
        source = bpy.data.objects.get(source_name or n)

        if not b280():
            # set all layers active temporarily
            cur_layers = list(scn.layers)
            set_layers([True]*20)
            # match source layers to brick layers
            b_group = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
            if b_group is not None and len(b_group.objects) > 0:
                brick = b_group.objects[0]
                source.layers = brick.layers

        # clean up 'Bricker_[source name]' collection
        if not skip_source:
            cls.clean_source(cm, n, source, model_type)

        # clean up source model duplicates
        if not skip_dupes:
            cls.clean_dupes(cm, n, preserved_frames, model_type)

        if not skip_parents:
            brick_loc, brick_rot, brick_scl = cls.clean_parents(cm, n, preserved_frames, model_type)
        else:
            brick_loc, brick_rot, brick_scl = None, None, None

        # initialize variables for cursor status updates
        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)
        print()

        if not skip_bricks:
            bricker_trans_and_anim_data = cls.clean_bricks(scn, cm, n, preserved_frames, model_type, skip_trans_and_anim_data)
        else:
            bricker_trans_and_anim_data = []

        if not b280():
            # set scene layers back to original layers
            set_layers(cur_layers)

        return source, brick_loc, brick_rot, brick_scl, bricker_trans_and_anim_data

    @classmethod
    def run_full_delete(cls, cm=None):
        """ externally callable cleanup function for full delete action (clears everything from memory) """
        scn, cm, n = get_active_context_info(cm=cm)
        model_type = get_model_type(cm)
        orig_frame = scn.frame_current
        if cm.model_created_on_frame != orig_frame:
            scn.frame_set(cm.model_created_on_frame)
        bricks = get_bricks()
        # store pivot point for model
        if (cm.last_split_model or cm.animated) and cm.parent_obj is not None:
            pivot_point = cm.parent_obj.matrix_world.to_translation()
        else:
            pivot_obj = bricks[0] if len(bricks) > 0 else cm.source_obj
            pivot_point = pivot_obj.matrix_world.to_translation()

        if cm.brickifying_in_background:
            job_manager = JobManager.get_instance(cm.id)
            job_manager.kill_all()

        source, brick_loc, brick_rot, brick_scl, _ = cls.clean_up(model_type, cm=cm, skip_source=cm.source_obj is None)

        # select source
        if source is None:
            print("[Bricker] Source object for model could not be found")
        else:
            select(source, active=True)

            # apply transformation to source
            if not cm.armature and len(bricks) > 0 and ((model_type == "MODEL" and cm.apply_to_source_object) or (model_type == "ANIMATION" and cm.apply_to_source_object)):
                l, r, s = get_transform_data(cm)
                if model_type == "MODEL":
                    loc = str_to_tuple(cm.last_source_mid, float)
                    if brick_loc is not None:
                        source.location = source.location + brick_loc - Vector(loc)
                    else:
                        source.location = Vector(l)# - Vector(loc)
                else:
                    source.location = Vector(l)
                source.scale = (source.scale[0] * s[0], source.scale[1] * s[1], source.scale[2] * s[2])
                # set rotation mode
                last_mode = source.rotation_mode
                source.rotation_mode = "XYZ"
                # create vert to track original source origin
                if len(source.data.vertices) == 0: source.data.vertices.add(1)
                last_co = source.data.vertices[0].co.to_tuple()
                source.data.vertices[0].co = (0, 0, 0)
                # set source origin to rotation point for transformed brick object
                depsgraph_update()
                set_obj_origin(source, pivot_point)
                # rotate source
                if cm.use_local_orient and not cm.use_animation:
                    source.rotation_euler = brick_rot or Euler(tuple(r))
                else:
                    rotateBy = Euler(tuple(r))
                    # if source.parent is not None:
                    #     # TODO: convert rotateBy to local with respect to source's parent
                    source.rotation_euler.rotate(rotateBy)
                # set source origin back to original point (tracked by last vert)
                depsgraph_update()
                set_obj_origin(source, mathutils_mult(source.matrix_world, source.data.vertices[0].co))
                source.data.vertices[0].co = last_co
                source.rotation_mode = last_mode
            # adjust source loc to account for local_orient_offset applied in transform_bricks()
            if cm.use_local_orient and not cm.use_animation:
                try:
                    source.location -= Vector(source["local_orient_offset"])
                except KeyError:
                    pass

        # clear_cache(cm, brick_mesh=False, dupes=False)

        # Scale brick height according to scale value applied to source
        cm.brick_height = cm.brick_height * cm.transform_scale

        # reset default values for select items in cmlist
        cls.reset_cmlist_attrs()

        clear_transform_data(cm)

        # reset frame (for proper update), update scene and redraw 3D view
        scn.frame_set(orig_frame)
        depsgraph_update()
        tag_redraw_areas("VIEW_3D")

    @classmethod
    def clean_source(cls, cm, n, source, model_type):
        scn = bpy.context.scene
        if b280():
            # link source to all collections containing Bricker model
            brick_coll = cm.collection
            brick_col_users = [cn for cn in bpy_collections() if brick_coll.name in cn.children and cn is not None] if brick_coll is not None else [item.collection for item in source.stored_parents if item.collection is not None]
        else:
            # set source layers to brick layers
            frame = cm.last_start_frame
            b_group = bpy_collections().get("Bricker_%(n)s_bricks" % locals() + ("_f_%(frame)s" % locals() if model_type == "ANIMATION" else ""))
            if b_group and len(b_group.objects) > 0:
                source.layers = list(b_group.objects[0].layers)
            brick_col_users = []
        safe_link(source, collections=brick_col_users)
        # reset source properties
        source.cmlist_id = -1

    @classmethod
    def clean_dupes(cls, cm, n, preserved_frames, model_type):
        scn = bpy.context.scene
        if model_type == "ANIMATION":
            dupe_name = "Bricker_%(n)s_f_" % locals()
            d_objects = [bpy.data.objects.get(dupe_name + str(fn)) for fn in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame)]
        else:
            d_objects = [bpy.data.objects.get("%(n)s__dup__" % locals())]
        # # if preserve frames, remove those objects from d_objects
        # objs_to_remove = []
        # if model_type == "ANIMATION" and preserved_frames is not None:
        #     for obj in d_objects:
        #         if obj is None:
        #             continue
        #         frame_num_idx = obj.name.rfind("_") + 1
        #         cur_frame_num = int(obj.name[frame_num_idx:])
        #         if cur_frame_num >= preserved_frames[0] and cur_frame_num <= preserved_frames[1]:
        #             objs_to_remove.append(obj)
        #     for obj in objs_to_remove:
        #         d_objects.remove(obj)
        if len(d_objects) > 0:
            delete(d_objects)

    @classmethod
    def clean_parents(cls, cm, n, preserved_frames, model_type):
        scn = bpy.context.scene
        brick_loc, brick_rot, brick_scl = None, None, None
        p = cm.parent_obj
        if p is None:
            return brick_loc, brick_rot, brick_scl
        if preserved_frames is None:
            if model_type == "ANIMATION" or cm.last_split_model:
                # store transform data of transformation parent object
                try:
                    loc_diff = p["loc_diff"]
                except KeyError:
                    loc_diff = None
                store_transform_data(cm, p, offset_by=loc_diff)
            if not cm.last_split_model and cm.collection is not None:
                bricks = get_bricks()
                if len(bricks) > 0:
                    b = bricks[0]
                    depsgraph_update()
                    brick_loc = b.matrix_world.to_translation().copy()
                    brick_rot = b.matrix_world.to_euler().copy()
                    brick_scl = b.matrix_world.to_scale().copy()  # currently unused
        # clean up Bricker_parent objects
        parents = [p] + (list(p.children) if model_type == "ANIMATION" else [])
        for parent in parents:
            if parent is None:
                continue
            # if preserve frames, skip those parents
            if model_type == "ANIMATION" and preserved_frames is not None:
                frame_num_idx = parent.name.rfind("_") + 1
                try:
                    cur_frame_num = int(parent.name[frame_num_idx:])
                    if cur_frame_num >= preserved_frames[0] and cur_frame_num <= preserved_frames[1]:
                        continue
                except ValueError:
                    continue
            bpy.data.objects.remove(parent, do_unlink=True)
        return brick_loc, brick_rot, brick_scl

    def update_animation_data(objs, bricker_trans_and_anim_data):
        """ add anim data for objs to 'bricker_trans_and_anim_data' """
        for obj in objs:
            obj.rotation_mode = "XYZ"
            bricker_trans_and_anim_data.append({"name":obj.name, "loc":obj.location.to_tuple(), "rot":tuple(obj.rotation_euler), "scale":obj.scale.to_tuple(), "action":obj.animation_data.action.copy() if obj.animation_data and obj.animation_data.action else None})

    @classmethod
    def clean_bricks(cls, scn, cm, n, preserved_frames, model_type, skip_trans_and_anim_data):
        bricker_trans_and_anim_data = []
        wm = bpy.context.window_manager
        if model_type == "MODEL":
            # clean up bricks collection
            sys.stdout.write("\rDeleting...")
            sys.stdout.flush()
            if cm.collection is not None:
                bricks = get_bricks()
                if not cm.last_split_model:
                    if len(bricks) > 0:
                        store_transform_data(cm, bricks[0])
                if not skip_trans_and_anim_data:
                    cls.update_animation_data(bricks, bricker_trans_and_anim_data)
                last_percent = 0
                # remove objects
                delete(bricks)
                # link any remaining objects to the scene
                for obj in cm.collection.objects:
                    if obj.name.startswith("Bricker_"):
                        continue
                    link_object(obj, scn)
                # remove the brick collection
                bpy_collections().remove(cm.collection, do_unlink=True)
            cm.model_created = False
        elif model_type == "ANIMATION":
            # clean up bricks collection
            for i in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                if preserved_frames is not None and i >= preserved_frames[0] and i <= preserved_frames[1]:
                    continue
                percent = (i - cm.last_start_frame + 1)/(cm.last_stop_frame - cm.last_start_frame + 1)
                if percent < 1:
                    update_progress("Deleting", percent)
                    wm.progress_update(percent*100)
                brick_coll = bpy_collections().get("Bricker_{n}_bricks_f_{i}".format(n=n, i=str(i)))
                if brick_coll:
                    bricks = list(brick_coll.objects)
                    if not skip_trans_and_anim_data:
                        cls.update_animation_data(bricks, bricker_trans_and_anim_data)
                    if len(bricks) > 0:
                        delete(bricks)
                    bpy_collections().remove(brick_coll, do_unlink=True)
            if preserved_frames is None:
                bpy_collections().remove(cm.collection, do_unlink=True)
                cm.animated = False
        # finish status update
        update_progress("Deleting", 1)
        wm.progress_end()
        return bricker_trans_and_anim_data

    def reset_cmlist_attrs():
        scn, cm, n = get_active_context_info()
        reset_attrs = [
            "model_loc",
            "model_rot",
            "model_scale",
            "transform_scale",
            "model_created_on_frame",
            "num_bricks_in_model",
            "num_materials_in_model",
            "model_weight",
            "real_world_dimensions",
            "last_source_mid",
            "last_logo_type",
            "last_split_model",
            "last_brick_type",
            "last_legal_bricks_only",
            "last_matrix_settings",
            "last_material_type",
            "last_is_smoke",
            "brickifying_in_background",
            "anim_is_dirty",
            "material_is_dirty",
            "model_is_dirty",
            "build_is_dirty",
            "matrix_is_dirty",
            "bricks_are_dirty",
            "armature",
            "expose_parent",
            "active_key",
            "is_smoke",
            "rgba_vals",
            "has_custom_obj1",
            "has_custom_obj2",
            "has_custom_obj3",
        ]
        for attr in reset_attrs:
            cm.property_unset(attr)
        cm.version = bpy.props.bricker_version
