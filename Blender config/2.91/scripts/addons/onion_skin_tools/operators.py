import bpy
from bpy.types import Operator
from bpy.props import BoolProperty
from .util import *
import platform, sys, os
from .run import *

#-------------------------------------------------
# Operator to add objects to onion skinning list.
#-------------------------------------------------
class VIEW3D_OT_AddOSTObjects( Operator):
    bl_idname = "ost.add_objects"
    bl_label = "Add Objects"
    bl_description = "Add selected to list of objects to be onion-skinned. " \
                     "If an armature is selected, all mesh objects parented " \
                     "to and deformed by the armature will be added to the list."
    
    def execute( self, context):
        scene = context.scene
        ost = scene.ost
        if ost.use_sets:
            sets_collection = ost.sets_collection
            obs_collection = sets_collection.active.obs_collection
        else:
            obs_collection = ost.obs_collection
        obj = context.object
        if obj.type == 'ARMATURE':
            # Could be an armature proxy.
            if obj.proxy is not None:
                obj = obj.proxy
            # Search the scene for objects that are deformed by the armature.
            for ob in bpy.data.objects:
                if ob.modifiers:
                    for mod in ob.modifiers:
                        if mod.type == 'ARMATURE':
                            if mod.object == bpy.data.objects[ obj.name]:
                                item = obs_collection.obs.add()
                                item.name = ob.name
                if ob.parent and ob.parent.name == obj.name and \
                   ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'} and \
                   ob.name not in [ item.name for item in obs_collection.obs]:
                    item = obs_collection.obs.add()
                    item.name = ob.name
        else:
            for ob in context.selected_objects:
                if ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'}:
                    item = obs_collection.obs.add()
                    item.name = ob.name
                if ob.type == 'EMPTY':
                    # Possible it's a linked group.
                    # Is it safe to assume a linked group will be 
                    # a deforming rig?
                    if ob.instance_type == 'COLLECTION':
                        inst_collection = ob.instance_collection
                        for inst_ob in inst_collection.all_objects:
                            if inst_ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'}:
                                if inst_ob.is_deform_modified( scene, 'PREVIEW') or 'wgt' not in inst_ob.name.lower():
                                    item = obs_collection.obs.add()
                                    item.name = inst_ob.name
                                    item.inst = ob.name
        obs_collection.index = len( obs_collection.obs) - 1
        return {'FINISHED'}
    
    
#-------------------------------------------------
# Operator to remove objects from onion skinning list.
#-------------------------------------------------
class VIEW3D_OT_RemoveOSTObjects( Operator):
    bl_idname = "ost.remove_objects"
    bl_label = "Remove Objects"
    bl_description = "Remove selected list item from onion skinning list"
    
    def execute( self, context):
        scene = context.scene
        ost = scene.ost
        if ost.use_sets:
            sets_collection = ost.sets_collection
            obs_collection = sets_collection.active.obs_collection
        else:
            obs_collection = ost.obs_collection
        index = obs_collection.index
        obs_collection.obs.remove( index)
        if obs_collection.obs.__len__() > 0:
            if index > 0:
                obs_collection.index = index - 1 
        if obs_collection.obs.__len__() == 1:
            obs_collection.index = 0
        return {'FINISHED'}


#-------------------------------------------------
# Operator to add character set.
#-------------------------------------------------
class VIEW3D_OT_AddOSTSet( Operator):
    bl_idname = "ost.add_set"
    bl_label = "Add Set"
    bl_description = "Add a character set. Any selected objects will be added to the set. " \
                     "If an armature is selected, all mesh objects parented " \
                     "to and deformed by the armature will be added to the list."
    
    def execute( self, context):
        scene = context.scene
        ost = scene.ost
        sets_collection = ost.sets_collection
        
        # Create the set.
        item = sets_collection.sets.add()
        index = len( sets_collection.sets)
        item.name = "Set " + str( index)
        sets_collection.index = len( sets_collection.sets) - 1
        
        # Add any selected objects.
        obs_collection = sets_collection.active.obs_collection
        obj = context.object
        if obj.type == 'ARMATURE':
            # Search the scene for objects that are deformed by the armature.
            for ob in scene.objects:
                if ob.modifiers:
                    for mod in ob.modifiers:
                        if mod.type == 'ARMATURE':
                            if mod.object == bpy.data.objects[ obj.name]:
                                item = obs_collection.obs.add()
                                item.name = ob.name
                if ob.parent and ob.parent.name == obj.name and \
                   ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'} and \
                   ob.name not in [ item.name for item in obs_collection.obs]:
                    item = obs_collection.obs.add()
                    item.name = ob.name
        else:
            for ob in context.selected_objects:
                if ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'}:
                    item = obs_collection.obs.add()
                    item.name = ob.name
                if ob.type == 'EMPTY':
                    # Possible it's a linked group.
                    if ob.instance_type == 'COLLECTION':
                        inst_collection = ob.instance_collection
                        for inst_ob in inst_collection.objects:
                            if inst_ob.type in {'MESH', 'CURVE', 'META', 'FONT', 'SURFACE'}:
                                item = obs_collection.obs.add()
                                item.name = inst_ob.name
                                item.inst = ob.name
        return {'FINISHED'}
    
    
#-------------------------------------------------
# Operator to remove character set.
#-------------------------------------------------
class VIEW3D_OT_RemoveOSTSet( Operator):
    bl_idname = "ost.remove_set"
    bl_label = "Remove Set"
    bl_description = "Delete selected character set"
    
    def execute( self, context):
        self.scene = context.scene
        self.remove = True
        ost = self.scene.ost
        sets_collection = ost.sets_collection
        index = sets_collection.index
        
        if len( sets_collection.sets) == 0:
            return {'FINISHED'}
            
        # Remove any onion skinning before removing the set.
        if sets_collection.active.final_collection_name:
            current_only = ost.current_only
            ost.current_only = False
            run_onion_skinning( self, context)
            ost.current_only = current_only
            
        sets_collection.sets.remove( index)
        if sets_collection.sets.__len__() > 0:
            if index > 0:
                sets_collection.index = index - 1 
        if sets_collection.sets.__len__() == 1:
            sets_collection.index = 0
        return {'FINISHED'}

#-------------------------------------------------
# Operator to create onion skinning in the viewport.
#-------------------------------------------------
class VIEW3D_OT_DrawFramesOST( Operator):
    bl_idname = "ost.draw_frames"
    bl_label = "Display Frame Numbers"
    bl_description = "Display frame numbers of onion skin objects"
    
    # Store the draw handler for removing.
    _draw_handler = None
    
    @staticmethod
    def _add_handler( self, context):
        args = ( self, context)
        VIEW3D_OT_DrawFramesOST._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_frames, args, 'WINDOW', 'POST_PIXEL')
        context.scene.ost.display_frames = True
        
    @staticmethod
    def _remove_handler( context):
        if VIEW3D_OT_DrawFramesOST._draw_handler != None:
            bpy.types.SpaceView3D.draw_handler_remove( VIEW3D_OT_DrawFramesOST._draw_handler, 'WINDOW')
            VIEW3D_OT_DrawFramesOST._draw_handler = None
        context.scene.ost.display_frames = False
            
    def modal( self, context, event):
        if context.area.type != 'VIEW_3D':
            return {'PASS_THROUGH'}
        
        ost = context.scene.ost
        
        # Check if frame display has been turned off.
        if not ost.display_frames:
            return {'FINISHED'}
        
        if not context.area or not context.region or event.type == 'NONE':
            context.area.tag_redraw()
        return {'PASS_THROUGH'}
    
    def invoke( self, context, event):
        scene = context.scene
        ost = scene.ost
        
        if context.area.type == 'VIEW_3D':
            if not ost.display_frames:
                # Drawing not enabled yet. Enable, if there is onion skinning.
                if ost.use_sets and ost.sets_collection.sets.__len__() > 0:
                    if ost.sets_collection.active.final_collection_name != "":
                        VIEW3D_OT_DrawFramesOST._add_handler( self, context)
                        context.area.tag_redraw()
                    else:
                        return {'CANCELLED'}
                if not ost.use_sets and ost.final_collection_name != "":
                    VIEW3D_OT_DrawFramesOST._add_handler( self, context)
                    context.area.tag_redraw()
                else:
                    return {'CANCELLED'}
            else:
                # Enabled already. Removing.
                VIEW3D_OT_DrawFramesOST._remove_handler( context)
                context.area.tag_redraw()
                
            context.window_manager.modal_handler_add( self)
            return {'RUNNING_MODAL'}
        else:
            # Not a 3D view.
            return {'CANCELLED'}
            
    
#-------------------------------------------------
# Operator to create onion skinning in the viewport.
#-------------------------------------------------
class VIEW3D_OT_RunOST( Operator):
    bl_idname = "ost.run"
    bl_label = "Run Onion Skinning"
    bl_description = "Create onion skinning in the viewport for the listed objects"
    
    remove : BoolProperty( default = False)
    auto : BoolProperty( default = False)
    
    def modal( self, context, event):
        try:
            # TODO: figure out passing CTRL+Z
            ost = self.scene.ost
        except: 
            ost = context.scene.ost

        # Check if auto-update's been disabled.
        if not ost.auto_update_on:
            self.report( {'INFO'}, "Disabling onion skinning auto update.")
            return {'FINISHED'}
        
        # Check that there's actually an updater object. Could have been removed while modal.
        if not ost.updater_object:
            self.report( {'INFO'}, "No updater object, disabling auto update.")
            self.auto = False
            ost.auto_update_on = False
            return {'CANCELLED'}
        
        if not context.area or not context.region or \
        event.type == 'NONE' or context.area.type not in { 'VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'}:
            return {'PASS_THROUGH'}
        
        # If mouse focus isn't in the region, dont register the event. 
        if 0 > event.mouse_region_x or event.mouse_region_x > context.region.width or \
        0 > event.mouse_region_y or event.mouse_region_y > context.region.height:
                self.transformed = False
                return {'PASS_THROUGH'}
        
        active_ob = context.active_object
        if active_ob is not None:
            is_armature = ( active_ob.type == 'ARMATURE')
            is_pose_mode = active_ob.mode == 'POSE'
        else:
            is_armature = False
            is_pose_mode = False
    
        if active_ob is not None and ost.updater_object == active_ob.name and \
        context.area.type in { 'VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'}:
            # Check if the event is finished.
            if event.type == 'MOUSEMOVE':
                return {'PASS_THROUGH'}
                
            if event.type == 'ESC':
                self.transformed = False
                if self.is_delete_menu:
                    self.is_delete_menu = False
                return {'PASS_THROUGH'}
            
            Debug( event.type, event.value, event.ctrl)
            if event.type == 'RIGHTMOUSE': 
                if context.area.type == 'VIEW_3D':
                    self.transformed = False
            
            if event.type == 'X' and context.area.type == 'VIEW_3D':
                self.transformed = False
                return {'PASS_THROUGH'}
            
            if self.transformed:
                # From ost_run.
                run_update( self, context, event)
            
            # Selection handling.
            if context.area.type == 'VIEW_3D':
                if event.type == 'MOUSE' and event.value == 'PRESS' \
                and not self.already_selected and not event.shift and not event.alt \
                and not event.ctrl and ( bpy.ops.view3d.select.poll() or bpy.ops.graph.clickselect.poll()):
                    self.transformed = False
                    bpy.ops.view3d.select('INVOKE_DEFAULT')
            elif context.area.type == 'GRAPH_EDITOR':
                if event.type == 'MOUSE' and event.value == 'PRESS' \
                and not self.already_selected and not event.shift and not event.alt \
                and not event.ctrl and bpy.ops.graph.select.poll():
                    self.transformed = False
                    bpy.ops.graph.clickselect('INVOKE_DEFAULT')
            elif context.area.type == 'DOPESHEET_EDITOR':
                if event.type == 'MOUSE' and event.value == 'PRESS' \
                and not self.already_selected and not event.shift and not event.alt \
                and not event.ctrl and bpy.ops.action.select.poll():
                    self.transformed = False
                    bpy.ops.action.clickselect('INVOKE_DEFAULT')
                    
            # Update selection.
            selected = context.selected_pose_bones.copy() if ( is_armature and is_pose_mode) \
            else context.selected_objects
                
            if self.is_delete_menu:
                # Previous command was delete menu.
                self.transformed = True
                self.is_delete_menu = False
                self.stored = selected
                
            # Check for deletes in graph editor.
            if event.type == 'X' and event.value == 'PRESS' and \
            ( context.area.type == 'GRAPH_EDITOR' or context.area.type == 'DOPESHEET_EDITOR'):
                # Wait to see if user deletes or cancels.
                self.is_delete_menu = True
                self.transformed = False
            
            # Check for hotkey events.
            values = self.update_actions.values()
            if event.type in [ val[0] for val in values]:
                if event.value == 'PRESS' and \
                self.already_selected and self.stored == selected:
                    for val in values:
                        if event.type == val[0] and \
                        event.alt == val[1] and \
                        event.ctrl == val[2] and \
                        event.shift == val[3] and \
                        event.oskey == val[4]:
                            self.transformed = True
                            self.stored = selected
                            id = val[5]
                if event.type == 'RIGHTMOUSE' and event.value == 'CLICK' and \
                event.ctrl and ( context.area.type == 'GRAPH_EDITOR' or context.area.type == 'DOPESHEET_EDITOR') \
                and self.already_selected and self.stored == selected:
                    self.transformed = True
                    self.stored = selected
            else:
                Debug( "transformed =", self.transformed, event.type)
            
            #-----------------------------------
            # Store the selection for reference.
            #-----------------------------------
            if selected:
                # There are pose bones selected.
                if not self.stored:
                    # Nothing stored yet. Store the new selection.
                    self.stored = selected
                    self.already_selected = False
                else:
                    # Something stored. Is everything that's selected stored in the list?
                    if self.stored == selected:
                        self.already_selected = True
                    else:
                        # They're not all stored in the list yet (eg., two selected before, selecting only one now). Update the list.
                        self.already_selected = False
                        self.stored = selected
            else:
                # No pose bones selected. Update the list and variable to reflect that.
                self.stored = []
                self.already_selected = False
                    
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}
            
    
    def execute( self, context):
        return_val = run_onion_skinning( self, context)
        return return_val
    
    def invoke( self, context, event):
        self.scene = context.scene
        if not self.auto:
            # Run or remove.
            return_val = self.execute( context)
            if self.remove:
                self.remove = False
            return return_val
        else:
            # Automatically updating existing onion skinning.
            ost = self.scene.ost
            if ost.use_sets:
                active_set = ost.sets_collection.active
                final_obs = active_set.final_obs
            else:
                final_obs = ost.final_obs
            if final_obs.__len__() > 0:
                # Onion skinning exists.
                if not ost.auto_update_on:
                    # Not enabled yet. Enable it, run modal.
                    ost.auto_update_on = True
                    ost.update_context = context.area.type
                    self.auto = False
                elif ost.auto_update_on and ost.update_context != context.area.type:
                    # Called from other context. Disable it and restart modal.
                    ost.auto_update_on = True
                    ost.update_context = context.area.type
                    self.auto = False
                else:
                    # Disable it.
                    ost.auto_update_on = False
                    self.auto = False
                    ost.update_context = ""
                    return {'FINISHED'}
            else:
                # No existing onion skinning.
                ost.auto_update_on = False
                self.auto = False
                ost.update_context = ""
                self.report( {'INFO'}, "No onion skinning found to update!")
                return {'CANCELLED'}
                
            self.is_delete_menu = False
            """
            Get user-specific mouse and hotkey settings.
            Only looking for transforms that change keyframes for now.
            TODO: 
            1) Include shape keys.
            2) Use the new timeline keyframe manipulation.
            3) Dopesheet and F-Curve editor changes.
            TODO: turn into a dict, with alt, ctrl, shift, oskey values as 
            list of values for each keymap_item key. 
            """
            self.already_selected = False
            self.transformed = False
            self.stored = []
            self.update_actions = {}
            keymaps = [ context.window_manager.keyconfigs.user.keymaps['3D View'],
                       context.window_manager.keyconfigs.user.keymaps['Pose'],
                       context.window_manager.keyconfigs.user.keymaps['Graph Editor'],
                       context.window_manager.keyconfigs.user.keymaps['Graph Editor Generic'],
                       context.window_manager.keyconfigs.user.keymaps['Dopesheet']]
            for keymap in keymaps:
                keymap_items = keymap.keymap_items
                if keymap.name == '3D View':
                    for item in keymap_items:
                        '''
                        if item.idname in {'transform.translate', 
                        'transform.rotate', 'transform.resize'} and \
                        item.map_type == 'KEYBOARD' and \
                        item.key_modifier == 'NONE' and not item.oskey and not \
                        item.shift and not item.alt and not item.any and not item.ctrl:
                            self.update_actions[ item.idname] = [ item.type, False, False, False, False, item.idname]
                        '''
                        props = item.properties
                        if item.map_type == 'KEYBOARD' and item.key_modifier == 'NONE':
                            if item.idname in { 'transform.translate', 'transform.rotate', 'transform.resize'}:
                                if props.gpencil_strokes:
                                    continue
                                if hasattr( props, "cursor_transform"):
                                    if props.cursor_transform:
                                        continue
                                if hasattr( props, "texture_space"):
                                    if props.texture_space:
                                        continue
                                self.update_actions[ item.idname] = [ item.type, item.alt, item.ctrl, item.shift, item.oskey, item.idname]
                            
                if keymap.name == 'Pose':
                    for item in keymap_items:
                        if item.map_type == 'KEYBOARD' and \
                        item.idname in { 'pose.breakdown', 
                                        'pose.paste', 
                                        'pose.push', 
                                        'pose.relax', 
                                        'pose.loc_clear', 
                                        'pose.rot_clear', 
                                        'pose.scale_clear'}:
                            self.update_actions[ item.idname] = [ item.type, item.alt, item.ctrl, item.shift, item.oskey, item.idname]
                if keymap.name == 'Graph Editor':
                    for item in keymap_items:
                        if item.map_type in {'KEYBOARD', 'TWEAK', 'MOUSE'} and \
                        item.idname in { 'graph.mirror',
                                         'graph.handle_type',
                                         'graph.interpolation_type',
                                         'graph.easing_type',
                                         'graph.smooth',
                                         'graph.sample',
                                         'graph.bake',
                                         'graph.duplicate_move',
                                         'graph.keyframe_insert',
                                         'graph.paste',
                                         'transform.transform',
                                         'graph.click_insert'}:
                            self.update_actions[ item.idname] = [ item.type, item.alt, item.ctrl, item.shift, item.oskey, item.idname]
                        if item.idname == 'wm.call_menu' and item.type == 'X':
                            self.update_actions[ item.idname] = [ item.type, False, False, False, False, item.idname]
                if keymap.name == 'Graph Editor Generic':
                    for item in keymap_items:
                        if item.map_type == 'KEYBOARD' and \
                        item.idname == 'graph.extrapolation_type':
                            self.update_actions[ item.idname] = [ item.type, item.alt, item.ctrl, item.shift, item.oskey, item.idname]
                if keymap.name == 'Dopesheet':
                    for item in keymap_items:
                        if item.idname in { 'action.mirror',
                                            'action.handle_type',
                                            'action.interpolation_type',
                                            'action.extrapolation_type',
                                            'action.duplicate_move',
                                            'action.keyframe_insert',
                                            'action.paste'}:
                            self.update_actions[ item.idname] = [ item.type, item.alt, item.ctrl, item.shift, item.oskey, item.idname]
            context.window_manager.modal_handler_add( self)
            return {'RUNNING_MODAL'}
            
class OT_HelpDocsOST( Operator):
    bl_idname = "ost.help_docs"
    bl_label = "Documentation"
    bl_description = "Open documentation PDF"
    
    def execute( self, context):
        dir_path = os.path.dirname( os.path.realpath( __file__))
        pdf_path = os.path.join( dir_path, "OST Documentation.pdf")
        if os.path.isfile( pdf_path):
            if sys.platform.startswith( 'win'):
                os.startfile( pdf_path)
            elif sys.platform.startswith( 'linux'):
                import subprocess
                subprocess.call(["xdg-open", pdf_path])
        else:
            self.report( {'INFO'}, "Could not find documentation file.")
        return {'FINISHED'}
    

classes = ( VIEW3D_OT_AddOSTObjects, VIEW3D_OT_RemoveOSTObjects, VIEW3D_OT_DrawFramesOST, VIEW3D_OT_RunOST, VIEW3D_OT_AddOSTSet, VIEW3D_OT_RemoveOSTSet, OT_HelpDocsOST)
def register():
    for cls in classes:
        bpy.utils.register_class( cls)
    
def unregister():
    for cls in reversed( classes):
        bpy.utils.unregister_class( cls)
