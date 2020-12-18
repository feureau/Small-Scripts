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
import random
import time
import bmesh
import os
from os.path import basename, dirname, abspath
import sys
import math
import shutil
import json
import marshal

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Module imports
from .bevel import BRICKER_OT_bevel
from .cache import *
from .delete_model import BRICKER_OT_delete_model
from ..lib.undo_stack import *
from ..subtrees.background_processing.classes.job_manager import JobManager
from ..functions import *


class BRICKER_OT_brickify(bpy.types.Operator):
    """Create brick sculpture from source object mesh"""
    bl_idname = "bricker.brickify"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        # return brickify_should_run(cm)
        return True

    def modal(self, context, event):
        if event.type == "TIMER":
            try:
                scn, cm, n = get_active_context_info(cm=self.cm)
                try:
                    self.source.name
                except ReferenceError:
                    self.source = cm.source_obj # protect against 'StructRNA has been removed' error
                remaining_jobs = self.job_manager.num_pending_jobs() + self.job_manager.num_running_jobs()
                anim_action = "ANIM" in self.action
                if anim_action and cm.frames_to_animate > 0:
                    cm.job_progress = round(cm.num_animated_frames * 100 / cm.frames_to_animate, 2)
                for job in self.jobs.copy():
                    # cancel if model was deleted before process completed
                    if scn in self.source.users_scene:
                        break
                    frame = int(job.split("__")[-1]) if anim_action else None
                    obj_frames_str = "_f_%(frame)s" % locals() if anim_action else ""
                    self.job_manager.process_job(job, debug_level=1, overwrite_data=True)
                    if self.job_manager.job_complete(job):
                        if anim_action: self.report({"INFO"}, "Completed frame %(frame)s of model '%(n)s'" % locals())
                        # cache bricksdict
                        retrieved_data = self.job_manager.get_retrieved_python_data(job)
                        bricksdict = None if retrieved_data["bricksdict"] in ("", "null") else marshal.loads(bytes.fromhex(retrieved_data["bricksdict"]))
                        cm.brick_sizes_used = retrieved_data["brick_sizes_used"]
                        cm.brick_types_used = retrieved_data["brick_types_used"]
                        cm.rgba_vals = retrieved_data["rgba_vals"]
                        cm.active_key = retrieved_data["active_key"]
                        if bricksdict is not None: cache_bricks_dict(self.action, cm, bricksdict[str(frame)] if anim_action else bricksdict, cur_frame=frame)
                        # process retrieved bricker data
                        bricker_instancer = bpy.data.objects.get("Bricker_%(n)s_instancer%(obj_frames_str)s" % locals())
                        bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent%(obj_frames_str)s" % locals())
                        bricker_bricks_coll = bpy_collections()["Bricker_%(n)s_bricks%(obj_frames_str)s" % locals()]
                        retrieved_bricks = [b for b in bricker_bricks_coll.objects if b.type == "MESH"]
                        for brick in retrieved_bricks:
                            if bricker_instancer is not None:
                                # brick.parent = bricker_instancer
                                bricker_instancer.parent = bricker_parent
                            else:
                                brick.parent = bricker_parent
                            # for i,mat_slot in enumerate(brick.material_slots):
                            #     mat = mat_slot.material
                            #     if mat is None:
                            #         continue
                            #     origMat = bpy.data.materials.get(mat.name[:-4])
                            #     if origMat is not None:
                            #         brick.material_slots[i].material = origMat
                            #         mat.user_remap(origMat)
                            #         bpy.data.materials.remove(mat)
                            if not b280():
                                safe_link(brick)
                                if anim_action:
                                    # hide obj unless on scene current frame
                                    adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
                                    brick.hide        = frame != adjusted_frame_current
                                    brick.hide_render = frame != adjusted_frame_current
                        if anim_action:
                            bricker_parent.parent = cm.parent_obj
                            if b280():
                                # link animation frames to animation collection and hide if not active
                                anim_coll = get_anim_coll(n)
                                if bricker_bricks_coll.name not in anim_coll.children:
                                    anim_coll.children.link(bricker_bricks_coll)
                                # hide obj unless on scene current frame
                                adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
                                bricker_bricks_coll.hide_viewport = frame != adjusted_frame_current
                                bricker_bricks_coll.hide_render   = frame != adjusted_frame_current
                            # add completed frame and remove job
                            cm.num_animated_frames += 1
                            add_completed_frame(cm, frame)
                            if not b280(): [safe_link(obj) for obj in bricker_bricks_coll.objects]
                        else:
                            link_brick_collection(cm, bricker_bricks_coll)
                        # link parent object to brick collection
                        if bricker_parent.name not in bricker_bricks_coll.objects:
                            bricker_bricks_coll.objects.link(bricker_parent)
                        hide(bricker_parent)
                        # remove job from queue
                        self.jobs.remove(job)
                    elif self.job_manager.job_dropped(job):
                        errormsg = self.job_manager.get_issue_string(job)
                        print_exception("Bricker log", errormsg=errormsg)
                        report_frames_str = " frame %(frame)s of" % locals() if anim_action else ""
                        self.report({"WARNING"}, "Dropped%(report_frames_str)s model '%(n)s'" % locals())
                        if anim_action: cm.num_animated_frames += 1
                        self.jobs.remove(job)
                # cancel and save finished frames if stopped
                if cm.stop_background_process:
                    self.cancel(context)
                    cm.stop_background_process = False
                    return {"CANCELLED"}
                # cancel if model was deleted before process completed
                if scn in self.source.users_scene:
                    self.cancel(context)
                    return {"CANCELLED"}
                # finish if all jobs completed
                elif self.job_manager.jobs_complete() or (remaining_jobs == 0 and self.job_manager.num_completed_jobs() > 0):
                    if "ANIM" in self.action:
                        finish_animation(self.cm)
                    self.report({"INFO"}, "Brickify background process complete for model '%(n)s'" % locals())
                    self.finish(context, cm)
                    return {"FINISHED"}
                elif remaining_jobs == 0:
                    self.report({"WARNING"}, "Background process failed for model '%(n)s'. Try disabling background processing in the Bricker addon preferences." % locals())
                    bpy.ops.bricker.stop_brickifying_in_background()
                tag_redraw_areas("VIEW_3D")
            except:
                bricker_handle_exception()
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def execute(self, context):
        # # NOTE: Temporary workaround for blender bug: https://developer.blender.org/T73761
        # for im in bpy.data.images:
        #     try:
        #         print(1, im.has_data)
        #         im.update()
        #         print(2, im.has_data)
        #     except RuntimeError:
        #         pass
        scn, cm, _ = get_active_context_info()
        wm = bpy.context.window_manager
        wm.bricker_running_blocking_operation = True
        try:
            if self.split_before_update:
                cm.split_model = True
            if cm.brickifying_in_background:
                if cm.animated or cm.model_created:
                    bpy.ops.bricker.delete_model()
                self.action = "CREATE" if self.action == "UPDATE_MODEL" else "ANIMATE"
            cm.version = bpy.props.bricker_version
            cm.job_progress = 0
            cm.stop_background_process = False
            previously_animated = cm.animated
            previously_model_created = cm.model_created
            success = self.run_brickify(context)
            if not success:
                return {"CANCELLED"}
        except KeyboardInterrupt:
            if self.action in ("CREATE", "ANIMATE"):
                for obj_n in self.created_objects:
                    obj = bpy.data.objects.get(obj_n)
                    if obj:
                        bpy.data.objects.remove(obj, do_unlink=True)
                for cn in get_collections(cm, typ="MODEL" if self.action == "CREATE" else "ANIM"):
                    if cn: bpy_collections().remove(cn, do_unlink=True)
                if cm.source_obj:
                    cm.source_obj.protected = False
                    select(self.source, active=True)
                cm.animated = previously_animated
                cm.model_created = previously_model_created
            self.report({"WARNING"}, "Process forcably interrupted with 'KeyboardInterrupt'")
        except:
            bricker_handle_exception()
        wm.bricker_running_blocking_operation = False
        if self.brickify_in_background:
            self.report({"INFO"}, "Brickifying in background...")
            # create timer for modal
            self._timer = wm.event_timer_add(0.1, window=bpy.context.window)
            wm.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.finish(context, cm)
            # update visible frame of bricker anim
            if cm.animated:
                handle_animation(context.scene)
            return {"FINISHED"}

    def cancel(self, context):
        scn, cm, n = get_active_context_info(cm=self.cm)
        self.finish(context, cm)
        if self.job_manager.num_running_jobs() + self.job_manager.num_pending_jobs() > 0:
            self.job_manager.kill_all()
            print("Background processes for '%(n)s' model killed" % locals())

    def finish(self, context, cm):
        if self._timer is not None:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
        cm.brickifying_in_background = False
        stopwatch("Total Time Elapsed", self.start_time, precision=2)

        # refresh model info
        prefs = get_addon_preferences()
        if prefs.auto_refresh_model_info:
            scn = bpy.context.scene
            bricksdict = get_bricksdict(cm, d_type="MODEL" if cm.model_created else "ANIM", cur_frame=scn.frame_current)
            set_model_info(bricksdict, cm)

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = get_active_context_info()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push("brickify", affected_ids=[cm.id])
        # initialize vars
        self.created_objects = list()
        self.action = get_action(cm)
        self.source = cm.source_obj
        self.orig_frame = scn.frame_current
        self.start_time = time.time()
        # initialize important vars
        self.job_manager = JobManager.get_instance(cm.id)
        prefs = get_addon_preferences()
        self.job_manager.max_workers = prefs.max_workers
        self.job_manager.max_attempts = 1
        self.completed_frames = []
        self.bricker_addon_path = get_addon_directory()
        self.jobs = list()
        self.cm = cm
        self._timer = None
        clear_pixel_cache()
        if self.source is not None:
            # set up model dimensions variables sX, sY, and sZ
            if self.action.startswith("UPDATE"):
                link_object(self.source)
            depsgraph_update()
            r = get_model_resolution(self.source, cm)
            if self.action.startswith("UPDATE"):
                unlink_object(self.source)
            self.brickify_in_background = should_brickify_in_background(cm, r, self.action)

    ###################################################
    # class variables

    split_before_update = BoolProperty(default=False)

    #############################################
    # class methods

    def run_brickify(self, context):
        # set up variables
        scn, cm, n = get_active_context_info(context, cm=self.cm)
        self.undo_stack.iterate_states(cm)

        # ensure that Bricker can run successfully
        if not self.is_valid(scn, cm, n, self.source):
            return False

        # initialize variables
        self.source.cmlist_id = cm.id
        matrix_dirty = matrix_really_is_dirty(cm)
        if self.brickify_in_background:
            cm.brickifying_in_background = True

        # check if source object is smoke simulation domain
        cm.is_smoke = is_smoke(self.source)
        if cm.is_smoke != cm.last_is_smoke:
            cm.matrix_is_dirty = True

        # clear cache if updating from previous version
        if created_with_unsupported_version(cm) and "UPDATE" in self.action:
            clear_cache(cm)
            cm.matrix_is_dirty = True

        # make sure matrix really is dirty
        if cm.matrix_is_dirty:
            if not matrix_dirty and get_bricksdict(cm) is not None:
                cm.matrix_is_dirty = False

        # store parent collections to source
        store_parent_collections_to_source(cm, self.source)

        if b280():
            # TODO: potentially necessary to ensure current View Layer includes collection with self.source
            # TODO: potentially necessary to ensure self.source (and its parent collections) are viewable?
            pass
        else:
            # set layers to source layers
            old_layers = list(scn.layers)
            source_layers = list(self.source.layers)
            if old_layers != source_layers:
                set_layers(source_layers)

        if "ANIM" not in self.action:
            self.brickify_model(context, scn, cm, n, matrix_dirty)
        else:
            self.brickify_animation(context, scn, cm, n, matrix_dirty)
            cm.anim_is_dirty = False

        # set cmlist_id for all created objects
        for obj_name in self.created_objects:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.cmlist_id = cm.id

        # set final variables
        cm.last_logo_type = cm.logo_type
        cm.last_split_model = cm.split_model
        cm.last_brick_type = cm.brick_type
        cm.last_legal_bricks_only = cm.legal_bricks_only
        cm.last_material_type = cm.material_type
        cm.last_use_abs_template = cm.use_abs_template
        cm.last_shell_thickness = cm.shell_thickness
        cm.last_instance_method = cm.instance_method
        cm.last_mat_shell_depth = cm.mat_shell_depth
        cm.last_matrix_settings = get_matrix_settings_str()
        cm.last_is_smoke = cm.is_smoke
        cm.matrix_is_dirty = False
        cm.matrix_lost = False
        cm.internal_is_dirty = False
        cm.expose_parent = False
        cm.model_created = "ANIM" not in self.action
        cm.animated = "ANIM" in self.action

        # link created brick collection
        if cm.animated:
            anim_coll = get_anim_coll(n)
            link_brick_collection(cm, anim_coll)
            if not self.brickify_in_background:
                finish_animation(self.cm)

        # unlink source from scene
        safe_unlink(self.source)
        if not b280():
            # reset layers
            if old_layers != source_layers:
                set_layers(old_layers)

        disable_relationship_lines()

        return True

    def brickify_model(self, context, scn, cm, n, matrix_dirty):
        """ create brick model """
        # set up variables
        source = None

        if self.action == "CREATE":
            # set model_created_on_frame
            cm.model_created_on_frame = scn.frame_current
        else:
            if self.orig_frame != cm.model_created_on_frame:
                scn.frame_set(cm.model_created_on_frame)

        # if there are no changes to apply, simply return "FINISHED"
        if self.action == "UPDATE_MODEL" and not update_can_run("MODEL"):
            return{"FINISHED"}

        if (matrix_dirty or self.action != "UPDATE_MODEL") and cm.customized:
            cm.customized = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrix_dirty or cm.build_is_dirty or cm.last_split_model != cm.split_model or self.brickify_in_background):
            # skip source, dupes, and parents
            skip_trans_and_anim_data = cm.animated or (cm.split_model or cm.last_split_model) and (matrix_dirty or cm.build_is_dirty)
            bpy.props.bricker_trans_and_anim_data = BRICKER_OT_delete_model.clean_up("MODEL", skip_dupes=True, skip_parents=True, skip_source=True, skip_trans_and_anim_data=skip_trans_and_anim_data)[4]
        else:
            store_transform_data(cm, None)
            bpy.props.bricker_trans_and_anim_data = []

        # get previously created source duplicate
        source_dup = get_duplicate_object(cm, self.source, self.created_objects)

        # link source_dup if it isn't in scene
        if source_dup.name not in scn.objects.keys():
            safe_link(source_dup)
        depsgraph_update()

        # get parent object
        bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent = bpy.data.objects.get(bricker_parent_on)
        # if parent doesn't exist, get parent with new location
        source_dup_details = bounds(source_dup)
        parent_loc = source_dup_details.mid
        if parent is None:
            parent = get_new_parent(bricker_parent_on, parent_loc)
        cm.parent_obj = parent
        children_clear(cm.parent_obj)  # clear children so they aren't sent to background processor
        parent["loc_diff"] = self.source.location - parent_loc
        self.created_objects.append(parent.name)

        # create, transform, and bevel bricks
        if self.brickify_in_background:
            filename = basename(bpy.data.filepath)[:-6]
            cur_job = "%(filename)s__%(n)s" % locals()
            # temporarily clear stored parents (prevents these collections from being sent to back proc)
            if b280():
                stored_parents = [p.collection for p in self.source.stored_parents]
                self.source.stored_parents.clear()
            # prepare bricksdict to send (or clear it if irrelevant)
            if cm.id in bricker_bfm_cache.keys() and cm.customized:
                light_to_deep_cache(bricker_bfm_cache, [cm.id])
            else:
                clear_cache(cm, brick_mesh=False, rgba_vals=False, images=False, dupes=False)
            # get the script to run in background
            script = os.path.join(self.bricker_addon_path, "lib", "brickify_in_background_template.py")
            # add scene with cmlist info to data blocks
            temp_scene = setup_temp_cmlist_scene(cm)
            # send job to the background processor
            data_blocks_to_send = {temp_scene, source_dup}
            job_added, msg = self.job_manager.add_job(cur_job, script=script, passed_data={"frame":None, "cmlist_id":cm.id, "action":self.action}, passed_data_blocks=data_blocks_to_send, use_blend_file=False)
            if not job_added: raise Exception(msg)
            self.jobs.append(cur_job)
            # remove scene
            bpy.data.scenes.remove(temp_scene)
            # replace stored parents to source object
            if b280():
                for p in stored_parents:
                    self.source.stored_parents.add().collection = p
        else:
            bcoll = self.brickify_active_frame(self.action)
            if bcoll:
                link_brick_collection(cm, bcoll)
                # select the bricks object unless it's massive
                if not cm.split_model and len(bcoll.objects) > 0:
                    obj = bcoll.objects[0]
                    # if len(obj.data.vertices) < 500000:
                    #     select(obj, active=True)

        # unlink source duplicate if created
        if source_dup != self.source:
            unlink_object(source_dup)

        # set active frame to original active frame
        if self.action != "CREATE" and scn.frame_current != self.orig_frame:
            scn.frame_set(self.orig_frame)

        cm.last_source_mid = vec_to_str(parent_loc)

    def brickify_animation(self, context, scn, cm, n, matrix_dirty):
        """ create brick animation """
        # set up variables
        objs_to_select = []

        if self.action == "UPDATE_ANIM":
            safe_link(self.source)
            self.source.name = n  # fixes issue with smoke simulation cache

        # if there are no changes to apply, simply return "FINISHED"
        self.updated_frames_only = False
        if self.action == "UPDATE_ANIM" and not update_can_run("ANIMATION"):
            if cm.anim_is_dirty:
                self.updated_frames_only = True
            else:
                return {"FINISHED"}

        if self.brickify_in_background:
            cm.completed_frames = ""
            cm.num_animated_frames = 0
            cm.frames_to_animate = (cm.stop_frame - cm.start_frame + 1) / cm.step_frame

        if (self.action == "ANIMATE" or cm.matrix_is_dirty or cm.anim_is_dirty) and not self.updated_frames_only:
            clear_cache(cm, brick_mesh=False, dupes=False)

        if cm.split_model:
            cm.split_model = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrix_dirty or cm.build_is_dirty or cm.last_split_model != cm.split_model or self.updated_frames_only):
            preserved_frames = None
            if self.updated_frames_only:
                # preserve duplicates, parents, and bricks for frames that haven't changed
                preserved_frames = [cm.start_frame, cm.stop_frame]
            BRICKER_OT_delete_model.clean_up("ANIMATION", skip_dupes=not self.updated_frames_only, skip_parents=not self.updated_frames_only, preserved_frames=preserved_frames, source_name=self.source.name)

        # get parent object
        bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        self.parent0 = bpy.data.objects.get(bricker_parent_on)
        if self.parent0 is None:
            self.parent0 = get_new_parent(bricker_parent_on, self.source.location)
        cm.parent_obj = self.parent0
        children_clear(cm.parent_obj)  # clear children so they aren't sent to background processor
        self.created_objects.append(self.parent0.name)

        # begin drawing status to cursor
        wm = bpy.context.window_manager
        wm.progress_begin(0, cm.stop_frame + 1 - cm.start_frame)

        # prepare duplicate objects for animation
        duplicates = get_duplicate_objects(scn, cm, self.action, cm.start_frame, cm.stop_frame, self.updated_frames_only)
        # [link_object(dup) for dup in duplicates]

        filename = basename(bpy.data.filepath)[:-6]
        overwrite_blend = True
        # iterate through frames of animation and generate Brick Model
        for cur_frame in range(cm.start_frame, cm.stop_frame + 1, cm.step_frame):
            if frame_unchanged(self.updated_frames_only, cm, cur_frame):
                print("skipped frame %(cur_frame)s" % locals())
                add_completed_frame(cm, cur_frame)
                cm.num_animated_frames += 1
                continue
            if self.brickify_in_background:
                cur_job = "%(filename)s__%(n)s__%(cur_frame)s" % locals()
                if b280():
                    # temporarily clear stored parents (prevents these collections from being sent to back proc)
                    stored_parents = [p.collection for p in self.source.stored_parents]
                    self.source.stored_parents.clear()
                # clear the bricksdict as we'll be creating a new one
                clear_cache(cm, brick_mesh=False, rgba_vals=False, images=False, dupes=False)
                # get the script to run in background
                script = os.path.join(self.bricker_addon_path, "lib", "brickify_in_background_template.py")
                # add scene with cmlist info to data blocks
                temp_scene = setup_temp_cmlist_scene(cm)
                # send job to the background processor
                data_blocks_to_send = {temp_scene} | set(duplicates.values())
                job_added, msg = self.job_manager.add_job(cur_job, script=script, passed_data={"frame":cur_frame, "cmlist_id":cm.id, "action":self.action}, passed_data_blocks=data_blocks_to_send, use_blend_file=False)
                if not job_added: raise Exception(msg)
                self.jobs.append(cur_job)
                overwrite_blend = False
                # remove scene
                bpy.data.scenes.remove(temp_scene)
                # replace stored parents to source object
                if b280():
                    for p in stored_parents:
                        self.source.stored_parents.add().collection = p
            else:
                success = self.brickify_current_frame(cur_frame, self.action)
                if not success:
                    break

        # set active frame to original active frame
        if scn.frame_current != self.orig_frame:
            scn.frame_set(self.orig_frame)

        # unlink source duplicates
        for obj in duplicates.values():
            unlink_object(obj)

        original_stop_frame = cm.last_stop_frame
        cm.last_start_frame = cm.start_frame
        cm.last_stop_frame = cm.stop_frame
        cm.last_step_frame = cm.step_frame

        # hide last frame of previous anim unless on scene current frame
        if self.action == "UPDATE_ANIM" and cm.stop_frame > original_stop_frame and scn.frame_current > original_stop_frame:
            set_frame_visibility(cm, original_stop_frame)

    @staticmethod
    def brickify_active_frame(action):
        # initialize vars
        scn, cm, n = get_active_context_info()
        parent = cm.parent_obj
        source_dup = bpy.data.objects.get(cm.source_obj.name + "__dup__")
        if source_dup.name not in scn.objects.keys():
            safe_link(source_dup)
        # depsgraph_update()
        source_dup_details, dimensions = get_details_and_bounds(source_dup)

        # create new bricks
        coll_name, _ = create_new_bricks(source_dup, parent, source_dup_details, dimensions, action, split=cm.split_model, cur_frame=None)

        bcoll = bpy_collections().get(coll_name)
        if bcoll:
            # transform bricks to appropriate location
            transform_bricks(bcoll, cm, parent, cm.source_obj, source_dup_details, action)
            # apply old animation data to objects
            for d0 in bpy.props.bricker_trans_and_anim_data:
                obj = bpy.data.objects.get(d0["name"])
                if obj is not None:
                    obj.location = d0["loc"]
                    obj.rotation_euler = d0["rot"]
                    obj.scale = d0["scale"]
                    if d0["action"] is not None:
                        obj.animation_data_create()
                        obj.animation_data.action = d0["action"]

        # add bevel if it was previously added
        if cm.bevel_added:
            bricks = get_bricks(cm, typ="MODEL")
            create_bevel_mods(cm, bricks)

        return bcoll

    @staticmethod
    def brickify_current_frame(cur_frame, action, in_background=False):
        scn, cm, n = get_active_context_info()
        wm = bpy.context.window_manager
        bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent0 = bpy.data.objects.get(bricker_parent_on)
        # orig_frame = scn.frame_current
        # scn.frame_set(orig_frame)
        scn.frame_set(cur_frame)
        # update brick layer offset (custom code for mantissa project)
        if cm.source_obj.name in ("ABC.Offset", "ABC.Base"):
            cm.offset_brick_layers = 2 - (cur_frame % 3)
        # get duplicated source
        source_dup = bpy.data.objects.get("Bricker_%(n)s_f_%(cur_frame)s" % locals())
        # get source info to update
        if in_background and scn not in source_dup.users_scene:
            # link source dup object to scene
            link_object(source_dup)
            depsgraph_update()

        # get source_details and dimensions
        source_details, dimensions = get_details_and_bounds(source_dup)

        # set up parent for this layer
        # TODO: Remove these from memory in the delete function, or don't use them at all
        p_name = "%(bricker_parent_on)s_f_%(cur_frame)s" % locals()
        parent = bpy.data.objects.get(p_name)
        if parent is None:
            parent = bpy.data.objects.new(p_name, None)
        parent.use_fake_user = True
        parent.location = source_details.mid - parent0.location
        parent.parent = parent0
        parent.update_tag()  # TODO: is it necessary to update this?

        # create new bricks
        try:
            coll_name, _ = create_new_bricks(source_dup, parent, source_details, dimensions, action, split=cm.split_model, cur_frame=cur_frame, clear_existing_collection=False, orig_source=cm.source_obj, select_created=False)
        except KeyboardInterrupt:
            if cur_frame != cm.start_frame:
                wm.progress_end()
                cm.last_start_frame = cm.start_frame
                cm.last_stop_frame = cur_frame - 1
                cm.animated = True
            return False

        # get collection with created bricks
        cur_frame_coll = bpy_collections().get(coll_name)
        if cur_frame_coll is not None and len(cur_frame_coll.objects) > 0:
            # get all_bricks_object
            obj = cur_frame_coll.objects[0]
            # hide collection/obj unless on scene current frame
            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.start_frame, cm.stop_frame, cm.last_step_frame)
            if cur_frame != adjusted_frame_current:
                hide(cur_frame_coll if b280() else obj)
            else:
                unhide(cur_frame_coll if b280() else obj)
            # lock location, rotation, and scale of created bricks
            obj.lock_location = (True, True, True)
            obj.lock_rotation = (True, True, True)
            obj.lock_scale    = (True, True, True)
            # add bevel if it was previously added
            if cm.bevel_added:
                create_bevel_mods(cm, [obj])

        wm.progress_update(cur_frame-cm.start_frame)
        print("-"*98)
        print("completed frame " + str(cur_frame))
        print("-"*98)
        return True

    def is_valid(self, scn, cm, source_name, source):
        """ returns True if brickify action can run, else report WARNING/ERROR and return False """
        # ensure custom object(s) are valid
        if (cm.brick_type == "CUSTOM" or cm.has_custom_obj1 or cm.has_custom_obj2 or cm.has_custom_obj3):
            warning_msg = custom_valid_object(cm)
            if warning_msg is not None:
                self.report({"WARNING"}, warning_msg)
                return False
        # ensure source is defined
        if source is None:
            self.report({"WARNING"}, "Source object '%(source_name)s' could not be found" % locals())
            return False
        # ensure source name isn't too long
        if len(source_name) > 39:
            self.report({"WARNING"}, "Source object name too long (must be <= 39 characters)")
            return False
        # verify Blender file is saved if running in background
        if self.brickify_in_background and bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return False
        # ensure custom material exists
        if cm.material_type == "CUSTOM" and cm.custom_mat is None:
            self.report({"WARNING"}, "Please choose a material in the 'Bricker > Materials' tab")
            return False
        if cm.material_type == "SOURCE" and cm.color_snap == "ABS":
            # ensure ABS Plastic materials are installed
            if not brick_materials_installed():
                self.report({"WARNING"}, "ABS Plastic Materials must be installed from Blender Market")
                return False
            # ensure ABS Plastic materials is updated to latest version
            if not hasattr(bpy.props, "abs_mat_properties"):
                self.report({"WARNING"}, "Requires ABS Plastic Materials v2.1.1 or later – please update via the addon preferences")
                return False
            # ensure ABS Plastic materials UI list is populated
            mat_obj = get_mat_obj(cm, typ="ABS")
            if mat_obj is None:
                mat_obj = create_mat_objs(cm)[1]
            if len(mat_obj.data.materials) == 0:
                self.report({"WARNING"}, "No ABS Plastic Materials found in Materials to be used")
                return False

        brick_coll_name = "Bricker_%(source_name)s_bricks" % locals()
        if self.action in ("CREATE", "ANIMATE"):
            # verify function can run
            if brick_coll_name in bpy_collections().keys():
                self.report({"WARNING"}, "Brickified Model already created.")
                return False
            # verify source exists and is of type mesh
            if source_name == "":
                self.report({"WARNING"}, "Please select a mesh to Brickify")
                return False
            # ensure source is not bricker model
            if source.is_brick or source.is_brickified_object:
                self.report({"WARNING"}, "Please bake the 'Bricker' source model before brickifying (Bricker > Bake/Export > Bake Model).")
                return False
            # ensure source exists
            if source is None:
                self.report({"WARNING"}, "'%(source_name)s' could not be found" % locals())
                return False
            # verify source is not a rigid body
            if source.rigid_body is not None and source.rigid_body.type == "ACTIVE":
                self.report({"WARNING"}, "First bake rigid body transformations to keyframes (SPACEBAR > Bake To Keyframes).")
                return False

        if self.action in ("ANIMATE", "UPDATE_ANIM"):
            # verify start frame is less than stop frame
            if cm.start_frame > cm.stop_frame:
                self.report({"ERROR"}, "Start frame must be less than or equal to stop frame (see animation tab below).")
                return False

        if self.action == "UPDATE_MODEL":
            # make sure 'Bricker_[source name]_bricks' collection exists
            if brick_coll_name not in bpy_collections().keys():
                self.report({"WARNING"}, "Brickified Model doesn't exist. Create one with the 'Brickify Object' button.")
                return False

        if cm.material_type == "SOURCE" and cm.use_uv_map:
            for mat_idx in range(len(source.material_slots)):
                img = get_first_img_from_nodes(source, mat_idx, verify_image=False)
                if img and not verify_img(img):
                    self.report({"WARNING"}, "Error: Image '{}' does not have any image data".format(img.name))
                    return False

        # check that custom logo object exists in current scene and is of type "MESH"
        if cm.logo_type == "CUSTOM" and cm.brick_type != "CUSTOM":
            if cm.logo_object is None:
                self.report({"WARNING"}, "Custom logo object not specified.")
                return False
            elif cm.logo_object.name == source_name:
                self.report({"WARNING"}, "Source object cannot be its own logo.")
                return False
            elif cm.logo_object.name.startswith("Bricker_%(source_name)s" % locals()):
                self.report({"WARNING"}, "Bricker object cannot be used as its own logo.")
                return False

        return True

    #############################################
