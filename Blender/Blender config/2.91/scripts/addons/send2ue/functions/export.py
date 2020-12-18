# Copyright Epic Games, Inc. All Rights Reserved.

import os
import re
import bpy
import tempfile
from . import unreal
from . import utilities
from . import validations


def get_unreal_asset_name(asset_name, properties):
    """
    This function takes a given asset name and removes the postfix _LOD and other non-alpha numeric characters
    that unreal won't except.

    :param str asset_name: The original name of the asset to export.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return str: The formatted name of the asset to export.
    """
    if properties.use_ue2rigify:
        return utilities.get_action_name(re.sub(r"\W+", "_", re.sub(r'(_LOD\d)', '', asset_name)), properties)

    return re.sub(r"\W+", "_", re.sub(r'(_LOD\d)', '', asset_name))


def get_fbx_paths(asset_name, asset_type):
    """
    This function gets the export path if it doesn't already exist.  Then it returns the full path.

    :param str asset_name: The name of the asset that will be exported to an fbx file.
    :param str asset_type: The type of data being exported.
    :return str: The full path to the fbx file.
    """
    fbx_paths = {}
    properties_window_manger = bpy.context.window_manager.send2ue
    properties = bpy.context.preferences.addons[properties_window_manger.module_name].preferences

    if properties.path_mode in ['send_to_unreal', 'both']:
        fbx_paths['unreal'] = os.path.join(
            tempfile.gettempdir(),
            properties_window_manger.module_name,
            f'{get_unreal_asset_name(asset_name, properties)}.fbx'
        )

    if properties.path_mode in ['export_to_disk', 'both']:
        if asset_type == 'MESH':
            # Check for relative paths and also sanitize the path
            export_dir = utilities.resolve_path(properties.disk_mesh_folder_path)
            fbx_paths['disk'] = os.path.join(
                export_dir,
                f'{get_unreal_asset_name(asset_name, properties)}.fbx'
            )
        if asset_type == 'ACTION':
            export_dir = utilities.resolve_path(properties.disk_animation_folder_path)
            fbx_paths['disk'] = os.path.join(
                export_dir,
                f'{get_unreal_asset_name(asset_name, properties)}.fbx'
            )
    return fbx_paths


def get_from_collection(collection_name, object_type):
    """
    This function fetches the objects inside each collection according to type and returns the
    the list of object references.

    :param str collection_name: The collection that you would like to retrieve objects from.
    :param str object_type: The object type you would like to get.
    :param bool only_visible: A flag that specifies whether to get only the visible objects.
    :return list: A list of objects
    """
    group_objects = []

    # get the collection with the given name
    collection = bpy.data.collections.get(collection_name)
    if collection:

        # get all the objects in the collection
        for group_object in collection.all_objects:

            # if the object is the correct type
            if group_object.type == object_type:

                # if the object is visible
                if group_object.visible_get():
                    # add it to the group of objects
                    group_objects.append(group_object)

    return group_objects


def get_skeleton_game_path(rig_object, properties):
    """
    This function gets the game path to the skeleton.

    :param object rig_object: A object of type armature.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return str: The game path to the unreal skeleton asset.
    """
    # if a skeleton path is provided
    if properties.unreal_skeleton_asset_path:
        return properties.unreal_skeleton_asset_path

    else:
        if rig_object.children:
            # get all meshes from the mesh collection
            mesh_collection = get_from_collection(properties.mesh_collection_name, 'MESH')

            # use the child mesh that is in the mesh collection to build the skeleton game path
            for child in rig_object.children:
                if child in mesh_collection:
                    asset_name = get_unreal_asset_name(child.name, properties)
                    return f'{properties.unreal_mesh_folder_path}{asset_name}_Skeleton'

        utilities.report_error(
            f'"{rig_object.name}" needs its unreal skeleton asset path specified under the "Path" settings '
            f'so it can be imported correctly!'
        )


def get_pre_scaled_context():
    """
    This function fetches the current scene's attributes.

    :return dict: A dictionary containing the current data attributes.
    """
    # look for an armature object and get its name
    context = {}
    for selected_object in bpy.context.selected_objects:
        if selected_object.type == 'ARMATURE':
            context['source_object'] = {}
            context['source_object']['object_name'] = selected_object.name
            context['source_object']['armature_name'] = selected_object.data.name
            bpy.context.view_layer.objects.active = selected_object

            # save the current scene scale
            context['scene_scale'] = bpy.context.scene.unit_settings.scale_length
            context['objects'] = bpy.data.objects.values()
            context['meshes'] = bpy.data.meshes.values()
            context['armatures'] = bpy.data.armatures.values()
            context['actions'] = bpy.data.actions.values()

    return context


def set_action_mute_value(rig_object, action_name, mute):
    """
    This function sets a given action's nla track to the provided mute value.

    :param object rig_object: A object of type armature with animation data.
    :param str action_name: The name of the action mute value to modify
    :param bool mute: Whether or not to mute the nla track
    """
    if rig_object:
        if rig_object.animation_data:
            for nla_track in rig_object.animation_data.nla_tracks:
                for strip in nla_track.strips:
                    if strip.action:
                        if strip.action.name == action_name:
                            nla_track.mute = mute


def set_action_mute_values(rig_object, action_names):
    """
    This function un-mutes the values based of the provided list

    :param object rig_object: A object of type armature with animation data.
    :param list action_names: A list of action names to un-mute
    """
    if rig_object.animation_data:
        for nla_track in rig_object.animation_data.nla_tracks:
            for strip in nla_track.strips:
                if strip.action:
                    if strip.action.name in action_names:
                        nla_track.mute = False
                    else:
                        nla_track.mute = True


def set_all_action_mute_values(rig_object, mute):
    """
    This function set all mute values on all nla tracks on the provided rig objects animation data.

    :param object rig_object: A object of type armature with animation data.
    :param bool mute: Whether or not to mute all nla tracks

    """
    if rig_object:
        if rig_object.animation_data:
            for nla_track in rig_object.animation_data.nla_tracks:
                nla_track.mute = mute


def set_parent_rig_selection(mesh_object, properties):
    """
    This function recursively selects all parents of an object as long as the parent are in the rig collection.

    :param object mesh_object: A object of type mesh.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # if the scene object has a parent
    if mesh_object.parent:

        # if the scene object's parent is in the rig collection
        if mesh_object.parent in get_from_collection(properties.rig_collection_name, 'ARMATURE'):
            # select the parent object
            mesh_object.parent.select_set(True)

            # call the function again to see if this object has a parent that
            set_parent_rig_selection(mesh_object.parent, properties)


def set_selected_objects_to_center(properties):
    """
    This function gets the original world position and centers the objects at world zero for export.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return dict: A dictionary of tuple that are the original position values of the selected objects.
    """
    original_positions = {}

    if properties.use_object_origin:
        for index, selected_object in enumerate(bpy.context.selected_objects):
            # get the original locations
            original_x = selected_object.location.x
            original_y = selected_object.location.y
            original_z = selected_object.location.z

            # set the location to zero
            selected_object.location.x = 0.0
            selected_object.location.y = 0.0
            selected_object.location.z = 0.0

            original_positions[index] = original_x, original_y, original_z

    # return the original positions
    return original_positions


def set_source_rig_hide_value(hide_value):
    """
    This function gets the original hide value of the source rig and sets it to the given value.

    :param bool hide_value: The hide value to set the source rig to.
    :return bool: The original hide value of the source rig.
    """
    ue2rigify_properties = bpy.context.window_manager.ue2rigify

    # set the hide value on the source rig
    source_rig_object = bpy.data.objects.get(ue2rigify_properties.source_rig_name)
    source_rig_object.hide_set(hide_value)


def set_object_positions(original_positions):
    """
    This function sets the given object's location in world space.

    :param object original_positions: A dictionary of tuple that are the original position values of the
    selected objects.
    """
    if original_positions:
        for index, selected_object in enumerate(bpy.context.selected_objects):
            selected_object.location.x = original_positions[index][0]
            selected_object.location.y = original_positions[index][1]
            selected_object.location.z = original_positions[index][2]


def scale_control_rig(scale_factor, properties):
    """
    This function scales the control rig.

    :param float scale_factor: The amount to scale the control rig by.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # if the using the ue2rigify addon
    if properties.use_ue2rigify:
        # remove all the constraints
        bpy.ops.ue2rigify.remove_constraints()

        # get the control rig
        control_rig_name = bpy.context.window_manager.ue2rigify.control_rig_name
        control_rig = bpy.data.objects.get(control_rig_name)

        # scale the the control rig
        utilities.scale_object(control_rig, scale_factor)


def duplicate_objects_for_export(scene_scale, scale_factor, context, properties):
    """
    This function duplicates and prepares the selected objects for export.

    :param float scene_scale: The value to set the scene scale to.
    :param float scale_factor: The amount to scale the control rig by.
    :param dict context: A dictionary containing the current data attributes.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return dict: A dictionary containing the current data attributes.
    """
    # switch to object mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # change scene scale to 0.01
    bpy.context.scene.unit_settings.scale_length = scene_scale

    # scale the control rig if needed
    scale_control_rig(scale_factor, properties)

    # duplicate the the selected objects so the originals are not modified
    bpy.ops.object.duplicate()

    context['duplicate_objects'] = bpy.context.selected_objects

    return context


def fix_armature_scale(armature_object, scale_factor, context, properties):
    """
    This function scales the provided armature object and it's animations.

    :param object armature_object: A object of type armature.
    :param float scale_factor: The amount to scale the control rig by.
    :param dict context: A dictionary containing the current data attributes.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return dict: A dictionary containing the current data attributes.
    """
    # deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # scale the duplicate rig object
    utilities.scale_object(armature_object, scale_factor)

    # select the rig object
    armature_object.select_set(True)

    # apply the scale transformations on the selected object
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # scale up the objects action location keyframes to fix the applied scale
    actions = utilities.get_actions(armature_object, properties)
    context['source_object']['actions'] = actions
    utilities.scale_object_actions([armature_object], actions, scale_factor)

    return context


def rename_duplicate_object(duplicate_object, context, properties):
    """
    This function renames the duplicated objects to match their original names and save a reference to them.
    :param object duplicate_object: A scene object.
    :param dict context: A dictionary containing the current data attributes.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return dict: A dictionary containing the current data attributes.
    """
    # Get a the root object name and save the object reference. This needs to happen so when the
    # duplicate armature is renamed to correctly to match the original object. For example a
    # duplicated object named 'Armature' is automatically given the name 'Armature.001' by Blender.
    # By saving this object reference, its name can be restored back to 'Armature' after the export.
    context['source_object']['object'] = bpy.data.objects.get(context['source_object']['object_name'])
    context['source_object']['armature'] = bpy.data.armatures.get(context['source_object']['armature_name'])

    # use the armature objects name as the root in unreal
    if properties.import_object_name_as_root:
        duplicate_object.name = context['source_object']['object_name']
        duplicate_object.data.name = context['source_object']['armature_name']

    # otherwise don't use the armature objects name as the root in unreal
    else:
        # Rename the armature object to 'Armature'. This is important, because this is a special
        # reserved keyword for the Unreal FBX importer that will be ignored when the bone hierarchy
        # is imported from the FBX file. That way there is not an additional root bone in the Unreal
        # skeleton hierarchy.
        duplicate_object.name = 'Armature'

    return context


def scale_rig_objects(properties):
    """
    This function changes the scene scale to 0.01 and scales the selected rig objects to offset that scene scale change.
    Then it return to original context.

    :return dict: The original context of the scene scale and its selected objects before changes occurred.
    """
    scene_scale = 0.01
    # get the context of the scene before any of the scaling operations
    context = get_pre_scaled_context()

    # only scale the rig object if there was a root object added to the context and automatically scaling bones is on
    if properties.automatically_scale_bones and context:
        # scale the rig objects by the scale factor needed to offset the 0.01 scene scale
        scale_factor = context['scene_scale'] / scene_scale

        context = duplicate_objects_for_export(scene_scale, scale_factor, context, properties)

        for duplicate_object in context['duplicate_objects']:
            if duplicate_object.type == 'ARMATURE':
                # rename the duplicated objects and save the original object references to the context
                context = rename_duplicate_object(duplicate_object, context, properties)

                # fix the armature scale and its animation and save that information to the context
                context = fix_armature_scale(duplicate_object, scale_factor, context, properties)

        # constrain the source rig to the control rig if using ue2rigify
        if properties.use_ue2rigify:
            bpy.ops.ue2rigify.constrain_source_to_deform()

        # restore the duplicate object selection for the export
        for duplicate_object in context['duplicate_objects']:
            duplicate_object.select_set(True)

    return context


def restore_rig_objects(context, properties):
    """
    This function takes the previous context of the scene scale and rig objects and sets them to the values in
    the context dictionary.

    :param dict context: The original context of the scene scale and its selected objects before changes occurred.
    :param properties:
    """
    if properties.automatically_scale_bones and context:
        scale_factor = bpy.context.scene.unit_settings.scale_length / context['scene_scale']

        # scale the control rig if needed
        scale_control_rig(scale_factor, properties)

        # restore action scale the duplicated actions
        utilities.scale_object_actions(context['duplicate_objects'], context['source_object']['actions'], scale_factor)

        # remove all the duplicate objects
        utilities.remove_extra_data(bpy.data.objects, context['objects'])

        # remove all the duplicate meshes
        utilities.remove_extra_data(bpy.data.meshes, context['meshes'])

        # remove all the duplicate armatures
        utilities.remove_extra_data(bpy.data.armatures, context['armatures'])

        # remove all the duplicate actions
        utilities.remove_extra_data(bpy.data.actions, context['actions'])

        # restore the scene scale
        bpy.context.scene.unit_settings.scale_length = context['scene_scale']

        # restore the original object name on the root object name if needed
        source_object = context['source_object'].get('object')
        if source_object:
            source_object.name = context['source_object']['object_name']
            source_object.data.name = context['source_object']['armature_name']

        if properties.use_ue2rigify:
            bpy.ops.ue2rigify.constrain_source_to_deform()


def export_fbx_files(file_paths, properties):
    """
    This function calls the blender fbx export operator with specific settings.

    :param dict file_paths: A dictionary of full file paths to be exported to FBX files.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # gets the original position and sets the objects position according to the selected properties.
    original_positions = set_selected_objects_to_center(properties)

    # change the scene scale and scale the rig objects and get their original context
    context = scale_rig_objects(properties)

    for file_path in file_paths.values():
        # if the folder does not exists create it
        folder_path = os.path.abspath(os.path.join(file_path, os.pardir))
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # export the fbx file
        bpy.ops.export_scene.fbx(
            filepath=file_path,
            use_selection=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            use_custom_props=properties.use_custom_props,
            global_scale=properties.global_scale,
            apply_scale_options=properties.apply_scale_options,
            axis_forward=properties.axis_forward,
            axis_up=properties.axis_up,
            apply_unit_scale=properties.apply_unit_scale,
            bake_space_transform=properties.bake_space_transform,
            mesh_smooth_type=properties.mesh_smooth_type,
            use_subsurf=properties.use_subsurf,
            use_mesh_modifiers=properties.use_mesh_modifiers,
            use_mesh_edges=properties.use_mesh_edges,
            use_tspace=properties.use_tspace,
            primary_bone_axis=properties.primary_bone_axis,
            secondary_bone_axis=properties.secondary_bone_axis,
            armature_nodetype=properties.armature_nodetype,
            use_armature_deform_only=properties.use_armature_deform_only,
            add_leaf_bones=properties.add_leaf_bones,
            bake_anim=properties.bake_anim,
            bake_anim_use_all_bones=properties.bake_anim_use_all_bones,
            bake_anim_force_startend_keying=properties.bake_anim_force_startend_keying,
            bake_anim_step=properties.bake_anim_step,
            bake_anim_simplify_factor=properties.bake_anim_simplify_factor,
            use_metadata=properties.use_metadata
        )

    # restores original positions
    set_object_positions(original_positions)

    # restores the original rig objects
    restore_rig_objects(context, properties)


def is_collision_of(asset_name, mesh_object_name):
    return bool(re.fullmatch(r"U(BX|CP|SP|CX)_" + asset_name + r"(_\d+)?", mesh_object_name))


def select_asset_collisions(asset_name, properties):
    collision_objects = get_from_collection(properties.collision_collection_name, 'MESH')
    for mesh_object in collision_objects:
        if is_collision_of(asset_name, mesh_object.name):
            mesh_object.select_set(True)


def export_mesh_lods(asset_name, properties):
    """
    This function exports a set of lod meshes to an fbx file.

    :param str asset_name: The name of the mesh set to export minus the _LOD postfix.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return str: The fbx file path of the exported mesh
    """
    mesh_collection = bpy.data.collections.get(properties.mesh_collection_name)

    if mesh_collection:
        lod_objects = []

        # deselect everything
        utilities.deselect_all_objects()

        # create an empty object with a property that will define this empties children as a lod group in the fbx file
        empty_object = bpy.data.objects.new(f'LOD_{asset_name}', None)
        empty_object['fbx_type'] = 'LodGroup'

        # link the empty object to the mesh collection
        mesh_collection.objects.link(empty_object)
        empty_object.select_set(True)

        # get all the lod mesh objects that contain the same name as the asset
        for mesh_object in get_from_collection(properties.mesh_collection_name, 'MESH'):
            if asset_name in mesh_object.name:
                # add it to the list of lod objects
                lod_objects.append((mesh_object, mesh_object.parent))

                # select any rig the mesh is parented to
                set_parent_rig_selection(mesh_object, properties)

                # parent lod objects to the lod empty
                mesh_object.parent = empty_object

                # select the lod mesh
                mesh_object.select_set(True)
        
        # select collsion meshes
        select_asset_collisions(asset_name, properties)

        # export the selected lod meshes and empty
        fbx_file_paths = get_fbx_paths(asset_name, 'MESH')
        export_fbx_files(fbx_file_paths, properties)

        # un-parent the empty from the lod objects and deselect them
        for lod_object, lod_object_parent in lod_objects:
            lod_object.parent = lod_object_parent
            lod_object.select_set(False)

        # remove the empty object
        bpy.data.objects.remove(empty_object)

        return fbx_file_paths


def export_mesh(mesh_object, properties):
    """
    This function exports a mesh to an fbx file.

    :param object mesh_object: A object of type mesh.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return str: The fbx file path of the exported mesh
    """
    # get file path for the fbx
    fbx_file_paths = get_fbx_paths(mesh_object.name, 'MESH')

    # deselect everything
    utilities.deselect_all_objects()

    # select the scene object
    mesh_object.select_set(True)

    # select any rigs this object is parented too
    set_parent_rig_selection(mesh_object, properties)

    # select collision meshes
    select_asset_collisions(mesh_object.name, properties)

    # export selection to an fbx file
    export_fbx_files(fbx_file_paths, properties)

    # deselect the exported object
    mesh_object.select_set(False)

    return fbx_file_paths


def export_action(rig_object, action_name, properties):
    """
    This function exports a single action from a rig object to an fbx file.

    :param object rig_object: A object of type armature with animation data.
    :param str action_name: The name of the action to export.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return str: The fbx file path of the exported action
    """
    control_rig_object = None
    if rig_object.animation_data:
        rig_object.animation_data.action = None

    # if using ue2rigify get the control rig and removes its active animation
    if properties.use_ue2rigify:
        ue2rigify_properties = bpy.context.window_manager.ue2rigify
        control_rig_object = bpy.data.objects.get(ue2rigify_properties.control_rig_name)
        if control_rig_object.animation_data:
            control_rig_object.animation_data.action = None

    fbx_file_paths = get_fbx_paths(action_name, 'ACTION')

    # deselect everything
    utilities.deselect_all_objects()

    # select the scene object
    rig_object.select_set(True)

    # un-mute the action
    if properties.export_all_actions:
        set_action_mute_value(rig_object, action_name, False)
        set_action_mute_value(control_rig_object, utilities.get_action_name(action_name, properties), False)

    # export the action
    export_fbx_files(fbx_file_paths, properties)

    # mute the action
    if properties.export_all_actions:
        # ensure the rigs are in rest position before setting the mute values
        utilities.clear_pose(rig_object)
        utilities.clear_pose(control_rig_object)

        set_action_mute_value(rig_object, action_name, True)
        set_action_mute_value(control_rig_object, utilities.get_action_name(action_name, properties), True)

    # deselect the exported object
    rig_object.select_set(False)

    return fbx_file_paths


def create_action_data(rig_objects, properties):
    """
    This function collects and creates all the action data needed for an animation import.

    :param list rig_objects: A list of rig objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the action import data.
    """
    action_data = []

    if properties.import_animations:
        # get the asset data for the skeletal animations
        for rig_object in rig_objects:

            control_rig_object = None
            unmuted_action_names = []
            current_pose = utilities.get_pose(rig_object)
            current_control_pose = None

            # if using ue2rigify get the control rig
            if properties.use_ue2rigify:
                ue2rigify_properties = bpy.context.window_manager.ue2rigify
                control_rig_object = bpy.data.objects.get(ue2rigify_properties.control_rig_name)
                current_control_pose = utilities.get_pose(control_rig_object)

                # if there is animation data on the control rig
                if control_rig_object.animation_data:
                    # if there is not animation data on the source rig
                    if not rig_object.animation_data:
                        # create animation data on the source rig
                        rig_object.animation_data_create()

                    # get the names of the un-muted actions
                    unmuted_action_names = utilities.get_action_names(control_rig_object, properties, all_actions=False)
            else:
                # get the names of the un-muted actions
                unmuted_action_names = utilities.get_action_names(rig_object, properties, all_actions=False)

            # if using ue2rigify and the auto sync nla strips option is on
            if properties.use_ue2rigify and properties.auto_sync_control_nla_to_source:
                bpy.ops.ue2rigify.sync_rig_actions()

            # if using ue2rigify and the auto stash active action option is on
            if not properties.use_ue2rigify and properties.auto_stash_active_action:
                # stash the active animation data in the rig object's nla strips
                utilities.stash_animation_data(rig_object, properties)

            # mute all actions on the control and source rigs
            if properties.export_all_actions:
                set_all_action_mute_values(control_rig_object, True)
                set_all_action_mute_values(rig_object, True)

            # get the names of all the actions to export
            action_names = utilities.get_action_names(
                rig_object,
                properties,
                all_actions=properties.export_all_actions
            )

            # export the actions and create the action import data
            for action_name in action_names:
                fbx_file_paths = export_action(rig_object, action_name, properties)

                # save the import data
                action_data.append({
                    'fbx_file_path': fbx_file_paths.get('unreal'),
                    'game_path': properties.unreal_animation_folder_path,
                    'skeleton_game_path': get_skeleton_game_path(rig_object, properties),
                    'animation': True
                })

            # set the action mute values back to their original state
            if properties.use_ue2rigify:
                set_action_mute_values(control_rig_object, unmuted_action_names)
            else:
                set_action_mute_values(rig_object, unmuted_action_names)

            # set the rig poses back to their original states
            utilities.set_pose(rig_object, current_pose)
            utilities.set_pose(control_rig_object, current_control_pose)

    return action_data


def create_mesh_data(mesh_objects, rig_objects, properties):
    """
    This function collects and creates all the asset data needed for the import process.

    :param list mesh_objects: A list of mesh objects.
    :param list rig_objects: A list of rig objects.
    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the mesh import data.
    """
    mesh_data = []
    # don't import meshes if importing onto an existing skeleton
    if not properties.unreal_skeleton_asset_path:
        # if importing lods
        if properties.import_lods:
            exported_asset_names = []

            # recreate the lod meshes to ensure the correct order
            mesh_objects = utilities.recreate_lod_meshes(mesh_objects)

            for mesh_object in mesh_objects:
                # get the name of the asset without the lod postfix
                asset_name = get_unreal_asset_name(mesh_object.name, properties)

                # if this asset name is not in the list of exported assets names
                if asset_name not in exported_asset_names:
                    # export the asset's lod meshes
                    fbx_file_paths = export_mesh_lods(asset_name, properties)

                    # save the asset data
                    mesh_data.append({
                        'fbx_file_path': fbx_file_paths.get('unreal'),
                        'game_path': properties.unreal_mesh_folder_path,
                        'skeletal_mesh': bool(rig_objects),
                        'import_mesh': True,
                        'lods': True
                    })

                    # add this asset to the list of exported assets
                    exported_asset_names.append(asset_name)

        # otherwise if not importing lods
        else:
            # get the asset data for the scene objects
            for mesh_object in mesh_objects:
                # export the object
                fbx_file_paths = export_mesh(mesh_object, properties)

                # save the asset data
                mesh_data.append({
                    'fbx_file_path': fbx_file_paths.get('unreal'),
                    'game_path': properties.unreal_mesh_folder_path,
                    'skeletal_mesh': bool(rig_objects),
                    'import_mesh': True
                })
    return mesh_data


def create_import_data(properties):
    """
    This function collects and creates all the asset data needed for the import process.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return list: A list of dictionaries containing the both the mesh and action import data.
    """
    # if using ue2rigify un-hide the source rig
    if properties.use_ue2rigify:
        set_source_rig_hide_value(False)

    # get the mesh and rig objects from their collections
    mesh_objects = get_from_collection(properties.mesh_collection_name, 'MESH')
    rig_objects = get_from_collection(properties.rig_collection_name, 'ARMATURE')

    # get the asset data for all the mesh objects
    mesh_data = create_mesh_data(mesh_objects, rig_objects, properties)

    # get the asset data for all the actions on the rig objects
    action_data = create_action_data(rig_objects, properties)

    # if using ue2rigify re-hide the source rig
    if properties.use_ue2rigify:
        set_source_rig_hide_value(True)

    return mesh_data + action_data


def validate(properties):
    """
    This function validates the assets before they get exported.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    :return bool: True if the assets pass all the validations.
    """
    # get the objects that will be exported
    mesh_objects = get_from_collection(properties.mesh_collection_name, 'MESH')

    # run through the selected validations
    if not validations.validate_collections_exist(properties):
        return False

    if not validations.validate_geometry_exists(mesh_objects):
        return False

    if not validations.validate_disk_paths(properties):
        return False

    if not validations.validate_unreal_paths(properties):
        return False

    if not validations.validate_unreal_skeleton_path(unreal, properties):
        return False

    if properties.validate_materials:
        if not validations.validate_geometry_materials(mesh_objects):
            return False

    if properties.validate_textures:
        if not validations.validate_texture_references(mesh_objects):
            return False

    if properties.import_lods:
        if not validations.validate_lod_names(mesh_objects):
            return False

    return True


def send2ue(properties):
    """
    This function sends assets to unreal.

    :param object properties: The property group that contains variables that maintain the addon's correct state.
    """
    # check to see if ue2rigify should be used
    utilities.set_ue2rigify_state(properties)

    # if there are no validation errors import the assets to unreal
    if validate(properties):
        # first get the current state of the scene and its objects
        context = utilities.get_current_context()

        # get the asset data for the import
        assets_data = create_import_data(properties)

        # restore the previous context
        utilities.set_context(context)

        if assets_data:
            # check path mode to see if exported assets should be imported to unreal
            if properties.path_mode in ['send_to_unreal', 'both']:
                for assets_data in assets_data:
                    result = unreal.import_asset(assets_data, properties)
                    if not result:
                        break
        else:
            utilities.report_error(
                f'You do not have the correct objects under the "{properties.mesh_collection_name}" or '
                f'"{properties.rig_collection_name}" collections or your rig does not have any '
                f'actions to export!'
            )
