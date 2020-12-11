# Copyright Epic Games, Inc. All Rights Reserved.

import bpy
from .ui import exporter
from .functions import scene
from .functions import nodes
from .functions import templates
from bpy_extras.io_utils import ImportHelper


class ConvertToRigifyRig(bpy.types.Operator):
    """Convert the source rig to a control rig"""
    bl_idname = "ue2rigify.convert_to_control_rig"
    bl_label = "Control"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.selected_mode = properties.control_mode
        return {'FINISHED'}


class RevertToSourceRig(bpy.types.Operator):
    """Revert the control rig back to the source rig"""
    bl_idname = "ue2rigify.revert_to_source_rig"
    bl_label = "Revert"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.selected_mode = properties.source_mode
        return {'FINISHED'}


class FreezeRig(bpy.types.Operator):
    """Freeze the rig if you are going to modify the control rig and don't want to lose your changes"""
    bl_idname = "ue2rigify.freeze_rig"
    bl_label = "Freeze"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.freeze_rig = True
        return {'FINISHED'}


class UnFreezeRig(bpy.types.Operator):
    """Un-freeze the rig so you can edit its bones and mappings"""
    bl_idname = "ue2rigify.un_freeze_rig"
    bl_label = "Un-Freeze? Data not generated with Rigify could be lost!"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify

        # un-freeze the rig
        properties.freeze_rig = False
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


class BakeActionsToSourceRig(bpy.types.Operator):
    """Bake the control rig actions to the source rig actions"""
    bl_idname = "ue2rigify.bake_from_rig_to_rig"
    bl_label = "Are you sure? Baking will delete your control rig animations!"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify

        # get the control and source rig objects
        control_rig = bpy.data.objects.get(properties.control_rig_name)
        source_rig = bpy.data.objects.get(properties.source_rig_name)

        # bake the control rig animations to the source rig animations
        scene.bake_from_rig_to_rig(control_rig, source_rig, properties, bake_to_source=True)
        properties.selected_mode = properties.source_mode
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


class SaveMetarig(bpy.types.Operator):
    """Save the metarig"""
    bl_idname = "ue2rigify.save_metarig"
    bl_label = "Save Metarig"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.selected_mode = properties.source_mode
        return {'FINISHED'}


class SaveRigNodes(bpy.types.Operator):
    """Save the node tree"""
    bl_idname = "ue2rigify.save_rig_nodes"
    bl_label = "Save Nodes"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.selected_mode = properties.source_mode
        return {'FINISHED'}


class SyncRigActions(bpy.types.Operator):
    """Sync the control rig actions to the source rig actions"""
    bl_idname = "ue2rigify.sync_rig_actions"
    bl_label = "Sync Rig Actions"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify

        # get the control and source rig objects
        control_rig = bpy.data.objects.get(properties.control_rig_name)
        source_rig = bpy.data.objects.get(properties.source_rig_name)

        # bake the control rig animations to the source rig animations
        scene.sync_actions(control_rig, source_rig, properties)
        return {'FINISHED'}


class RemoveTemplateFolder(bpy.types.Operator):
    """Remove this template from the addon"""
    bl_idname = "ue2rigify.remove_template_folder"
    bl_label = "Delete this template?"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        templates.remove_template_folder(properties)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)


class ExportRigTemplate(bpy.types.Operator, exporter.ExportRigTemplate):
    """Export a rig template"""
    bl_idname = "ue2rigify.export_rig_template"
    bl_label = "Export Template"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        templates.export_zip(self.filepath, properties)
        return {'FINISHED'}


class ImportRigTemplate(bpy.types.Operator, ImportHelper):
    """Import a rig template"""
    bl_idname = "ue2rigify.import_rig_template"
    bl_label = "Import Template"
    filename_ext = ".zip"

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        templates.import_zip(self.filepath, properties)
        return {'FINISHED'}


class CreateNodesFromSelectedBones(bpy.types.Operator):
    """Create nodes that will have sockets with names of the selected bones"""
    bl_idname = "ue2rigify.create_nodes_from_selected_bones"
    bl_label = "Nodes From Selected Bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        nodes.create_nodes_from_selected_bones(properties)
        return {'FINISHED'}


class CreateLinkFromSelectedBones(bpy.types.Operator):
    """Create a pair of linked nodes from the selected bones"""
    bl_idname = "ue2rigify.create_link_from_selected_bones"
    bl_label = "Link Selected Bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        nodes.create_link_from_selected_bones(properties)
        return {'FINISHED'}


class CombineSelectedNodes(bpy.types.Operator):
    """Combine the selected nodes into a new node that will have the name of the active node"""
    bl_idname = "wm.combine_selected_nodes"
    bl_label = "Combine Selected Nodes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR'

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        nodes.combine_selected_nodes(self, context, properties)
        return {'FINISHED'}


class AlignActiveNodeSockets(bpy.types.Operator):
    """Align the active node sockets with the sockets of the node it is linked to"""
    bl_idname = "wm.align_active_node_sockets"
    bl_label = "Align Active Node Sockets"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR'

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        nodes.align_active_node_sockets(context, properties)
        return {'FINISHED'}


class ConstrainSourceToDeform(bpy.types.Operator):
    """Constrain the source bones to the deform bones"""
    bl_idname = "ue2rigify.constrain_source_to_deform"
    bl_label = "Constrain source to deform"

    control_rig_name: bpy.props.StringProperty(default='')
    source_rig_name: bpy.props.StringProperty(default='')

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify

        # get the control and source rig objects
        if self.control_rig_name:
            control_rig = bpy.data.objects.get(self.control_rig_name)
        else:
            control_rig = bpy.data.objects.get(properties.control_rig_name)
        if self.source_rig_name:
            source_rig = bpy.data.objects.get(self.source_rig_name)
        else:
            source_rig = bpy.data.objects.get(properties.source_rig_name)

        # constrain the source rig to the deform rig
        scene.constrain_source_to_deform(source_rig, control_rig, properties)
        return {'FINISHED'}


class RemoveConstraints(bpy.types.Operator):
    """Remove all constraints on both the source rig and control rig"""
    bl_idname = "ue2rigify.remove_constraints"
    bl_label = "Remove Constraints"

    control_rig_name: bpy.props.StringProperty(default='')
    source_rig_name: bpy.props.StringProperty(default='')

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify

        # get the control and source rig objects
        if self.control_rig_name:
            control_rig = bpy.data.objects.get(self.control_rig_name)
        else:
            control_rig = bpy.data.objects.get(properties.control_rig_name)
        if self.source_rig_name:
            source_rig = bpy.data.objects.get(self.source_rig_name)
        else:
            source_rig = bpy.data.objects.get(properties.source_rig_name)

        # remove the constraints on the source rig and control rig
        scene.remove_bone_constraints(control_rig, properties)
        scene.remove_bone_constraints(source_rig, properties)
        return {'FINISHED'}


class SwitchModes(bpy.types.Operator):
    """Switch to the given mode"""
    bl_idname = "ue2rigify.switch_modes"
    bl_label = "Switch Modes"

    mode: bpy.props.StringProperty(default='')

    def execute(self, context):
        properties = bpy.context.window_manager.ue2rigify
        properties.freeze_rig = True
        properties.selected_mode = self.mode
        properties.freeze_rig = False
        scene.switch_modes()
        return {'FINISHED'}


class NullOperator(bpy.types.Operator):
    """This is an operator that changes nothing, but it used to clear the undo stack"""
    bl_idname = "ue2rigify.null_operator"
    bl_label = "Null Operator"

    def execute(self, context):
        return {'FINISHED'}

