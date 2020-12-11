import bpy
from bpy.types import Panel, UIList
import sys

#-------------------
# Icon globals.
#-------------------
icons_loaded = False
icons_collection = {}

#-------------------------------------------------
# UI list of onion skin objects.
#-------------------------------------------------
class TOOLS_UL_OSTObjectSlots( UIList):
    def draw_item( self, context, layout, data, item, icon, active_data, \
    active_propname, index):
        ob = item
        layout.label( text = "%s" % ob.name)
        
#-------------------------------------------------
# UI list of onion skin character sets.
#-------------------------------------------------
class TOOLS_UL_OSTCharacterSetSlots( UIList):
    def draw_item( self, context, layout, data, item, icon, active_data, \
    active_propname, index):
        set = item
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( item, "name", text = "", emboss = False)
        if set.final_collection_name:    
            try:
                icons = load_icons()
                ost_run = icons.get( "ost_run")
                row.label( text = "", icon_value = ost_run.icon_id)
            except:
                row.label( text = "", icon = 'FILE_REFRESH')
            
#-------------------------------------------------
# Panel for onion skinning properties and buttons.
#-------------------------------------------------
class TOOLS_PT_OST( Panel):
    bl_label = "Onion Skin Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "OST"
    
    def draw( self, context):
        layout = self.layout
        scene = context.scene
        ost = scene.ost
        sets_collection = ost.sets_collection
        
        # Operators.
        # Run operator.
        try:
            icons = load_icons()
            ost_run = icons.get( "ost_run")
            ost_remove = icons.get( "ost_remove")
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", icon_value = ost_run.icon_id, text = "Run")
            row.operator( "ost.run", 
                        icon_value = ost_remove.icon_id, 
                        text = "Remove").remove = True
        except:
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", text = "Run", icon = 'BLANK1')
            row.operator( "ost.run", text = "Remove", icon = 'BLANK1').remove = True
        
        # Objects to onion skin.
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_list",
                        icon = 'TRIA_DOWN' if ost.show_list else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Objects To Onion Skin")
        
        # Character sets list.   
        if ost.show_list:
            layout.prop( ost, "use_sets")
            if ost.use_sets:
                columns_row = layout.row()
                col = columns_row.column()     
                col.label( text = "Character Sets")
                row = col.row()
                subcol = row.column()
                subcol.template_list( "TOOLS_UL_OSTCharacterSetSlots",
                            "os_set_slots", sets_collection,
                            "sets", sets_collection, "index")
                row = col.row( align = True)
                row.operator( "ost.add_set", icon = 'ADD', text = "New")
                row.operator( "ost.remove_set", icon = 'REMOVE', text = "Delete")
            
                if len( sets_collection.sets) > 0:
                    # Objects list.
                    col2 = columns_row.column()
                    row = col2.row( align = True)
                    row.label( text = "Objects")
                    row = col2.row()
                    subcol = row.column()
                    obs_collection = sets_collection.active.obs_collection
                    subcol.template_list( "TOOLS_UL_OSTObjectSlots",
                                "os_object_slots", obs_collection,
                                "obs", obs_collection, "index")
                    row = col2.row( align = True)
                    row.operator( "ost.add_objects", icon = 'ADD', text = "Add")
                    row.operator( "ost.remove_objects", icon = 'REMOVE', text = "Remove")
            else:
                # Global objects list.
                col = layout.column()
                obs_collection = ost.obs_collection
                col.template_list( "TOOLS_UL_OSTObjectSlots",
                            "os_object_slots", obs_collection,
                            "obs", obs_collection, "index")
                row = col.row( align = True)
                row.operator( "ost.add_objects", icon = 'ADD', text = "Add")
                row.operator( "ost.remove_objects", icon = 'REMOVE', text = "Remove")
        
        # Frame range settings.
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_range",
                        icon = 'TRIA_DOWN' if ost.show_range else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Frame Range Settings")
        if ost.show_range:
            box = layout.box()
            box.prop( ost, "current_only")
            settings_column1 = box.column()
            settings_column1.prop( ost, "include_current")
            row = settings_column1.row()
            row.prop( ost, "keyed_only")
            if ost.keyed_only:
                row.prop( ost, "keyed_object", text = "Object")
            settings_column1.enabled = False if ost.current_only else True    
            
            settings_column2 = box.column()
            settings_column2.label( text = "Range Mode:")
            settings_column2.prop( ost, "range_mode", text = "")
            if ost.range_mode == 'relative':
                settings_column2.label( text = "Direction:")
                settings_column2.prop( ost, "direction", text = "")
            settings_column2.label( text = "Range:")
            row = settings_column2.row( align = True)
            if ost.range_mode == 'relative':
                if ost.direction == 'backward' or ost.direction == 'both':
                    row.prop( ost, "bwd_range", text = "Backward")
                if ost.direction == 'forward' or ost.direction == 'both':
                    row.prop( ost, "fwd_range", text = "Forward")
            else:
                row.prop( ost, "start_range", text = "Start")
                row.prop( ost, "end_range", text = "End")
            settings_column2.prop( ost, "step")
            settings_column2.enabled = False if ost.current_only or ost.keyed_only else True
        
        # Viewport draw settings.
        if ost.use_sets:
            settings = sets_collection.active
        else:
            settings = ost
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_settings", 
                        icon = 'TRIA_DOWN' if ost.show_settings else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Viewport Settings")
        if ost.show_settings:
            if ost.use_sets and len( sets_collection.sets) == 0:
                pass    
            else:
                box = layout.box()
                row = box.row()
                col = row.column()
                col.label( text = "Earlier Color:")
                col.prop( settings, "bwd_color", text = "")
                col = row.column()
                col.label( text = "Later Color:")
                col.prop( settings, "fwd_color", text = "")
                
                row = box.row()
                col = row.column()
                col.prop( settings, "show_transp")
                col2 = row.column()
                col2.prop( settings, "transp_factor", text = "Factor")
                col2.enabled = True if settings.show_transp else False
                
                row = box.row()
                row.prop( settings, "use_transp_range")
                row = box.row()
                row.prop( settings, "transp_range")
                row.enabled = True if settings.use_transp_range else False
                
                row = box.row()
                row.prop( settings, "xray")
                row.prop( settings, "xray_orig")
                
                # Visibility settings.
                box.label( text = "Hide Onion Skin Objects:")
                row = box.row()
                row.prop( settings, "hide_before", text = "Before")
                row.prop( settings, "hide_after", text = "After")
                row.prop( settings, "hide_all", text = "All")
                
                # Frame number drawing.
                row = box.row()
                row.operator( "ost.draw_frames", 
                            icon = 'REMOVE' if ost.display_frames else 'ADD',
                            text = "Disable Frame Numbers" if ost.display_frames else \
                            "Display Frame Numbers")
                if ost.display_frames:
                    row = box.row()
                    row.prop( ost, "font_size", expand = True)
                    row.prop( ost, "font_height", expand = True)
            
        # Auto update settings.
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_auto_settings", 
                        icon = 'TRIA_DOWN' if ost.show_auto_settings else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Auto Update Settings")
        if ost.show_auto_settings:
            box = layout.box()
            objects = scene.objects
            row = box.row()
            row.prop_search( ost, "updater_object", scene, "objects")
            op_text = "Disable Auto Updating" if ( ost.auto_update_on and \
            ost.update_context == 'VIEW_3D') else "Enable Auto Updating"
            try:
                box.operator( "ost.run", 
                        icon_value = 19 if ( ost.auto_update_on and \
                        ost.update_context == 'VIEW_3D') else ost_run.icon_id, 
                        text = op_text).auto = True
            except:
                box.operator( "ost.run", text = op_text, icon = 'BLANK1').auto = True
        
        # Help.
        if sys.platform.startswith( 'win') or sys.platform.startswith( 'linux'):
            row = layout.row( align = True)
            row.alignment = 'LEFT'
            row.operator( "ost.help_docs", text = "Documentation", icon = 'QUESTION', emboss = False)

#-------------------------------------------------
# Panel for graph editor auto-update button.
#-------------------------------------------------
class UI_PT_OST_GraphEditor( Panel):
    bl_label = "Onion Skin Tools"
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw( self, context):
        layout = self.layout
        scene = context.scene
        ost = scene.ost
        
        try:
            icons = load_icons()
            ost_run = icons.get( "ost_run")
            ost_remove = icons.get( "ost_remove")
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", icon_value = ost_run.icon_id, text = "Run")
            row.operator( "ost.run", 
                        icon_value = ost_remove.icon_id, 
                        text = "Remove").remove = True
        except:
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", text = "Run", icon = 'BLANK1')
            row.operator( "ost.run", text = "Remove", icon = 'BLANK1').remove = True
            
        # Auto update settings.
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_auto_settings", 
                        icon = 'TRIA_DOWN' if ost.show_auto_settings else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Graph Editing Auto Update Settings")
        if ost.show_auto_settings:
            box = layout.box()
            objects = scene.objects
            row = box.row()
            row.prop_search( ost, "updater_object", scene, "objects")
            if ost.auto_update_on and ost.update_context == 'GRAPH_EDITOR':
                op_text = "Disable Auto Updating" 
                icon_val = 19
            else:
                op_text = "Enable Auto Updating"
                icon_val = ost_run.icon_id
            try:
                box.operator( "ost.run", 
                        icon_value = icon_val, 
                        text = op_text).auto = True
            except:
                box.operator( "ost.run", text = op_text, icon = 'BLANK1').auto = True
        

#-------------------------------------------------
# Panel for graph editor auto-update button.
#-------------------------------------------------
class UI_PT_OST_DopesheetEditor( Panel):
    bl_label = "Onion Skin Tools"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw( self, context):
        layout = self.layout
        scene = context.scene
        ost = scene.ost
        
        try:
            icons = load_icons()
            ost_run = icons.get( "ost_run")
            ost_remove = icons.get( "ost_remove")
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", icon_value = ost_run.icon_id, text = "Run")
            row.operator( "ost.run", 
                        icon_value = ost_remove.icon_id, 
                        text = "Remove").remove = True
        except:
            row = layout.row( align = True)
            row.scale_y = 1.5
            row.operator( "ost.run", text = "Run", icon = 'BLANK1')
            row.operator( "ost.run", text = "Remove", icon = 'BLANK1').remove = True
            
        # Auto update settings.
        row = layout.row( align = True)
        row.alignment = 'LEFT'
        row.prop( ost, "show_auto_settings", 
                        icon = 'TRIA_DOWN' if ost.show_auto_settings else 'TRIA_RIGHT', 
                        toggle = False, icon_only = True, emboss = False)
        row.label( text = "Dopesheet Auto Update Settings")
        if ost.show_auto_settings:
            box = layout.box()
            objects = scene.objects
            row = box.row()
            row.prop_search( ost, "updater_object", scene, "objects")
            if ost.auto_update_on and ost.update_context == 'DOPESHEET_EDITOR':
                op_text = "Disable Auto Updating" 
                icon_val = 19
            else:
                op_text = "Enable Auto Updating"
                icon_val = ost_run.icon_id
            try:
                box.operator( "ost.run", 
                        icon_value = icon_val, 
                        text = op_text).auto = True
            except:
                box.operator( "ost.run", text = op_text, icon = 'BLANK1').auto = True
                
                
def load_icons():
    global icons_loaded
    global icons_collection
    import os
    dir = os.path.join(os.path.dirname( __file__))
    if not icons_loaded:
        import bpy.utils.previews
        icons = bpy.utils.previews.new()
        icons.load( "ost_run", os.path.join( dir, "icons", "ost_run.png"), 'IMAGE')
        icons.load( "ost_remove", os.path.join( dir, "icons", "ost_remove.png"), 'IMAGE')
        icons_collection[ "icons"] = icons
        icons_loaded = True
    return icons_collection[ "icons"]

def remove_icons():
    global icons_collection
    if icons_loaded:
        bpy.utils.previews.remove( icons_collection["icons"])


classes = ( TOOLS_UL_OSTCharacterSetSlots, TOOLS_UL_OSTObjectSlots, TOOLS_PT_OST, UI_PT_OST_GraphEditor, UI_PT_OST_DopesheetEditor)
def register():
    for cls in classes:
        bpy.utils.register_class( cls)
        
def unregister():
   for cls in reversed( classes):
        bpy.utils.unregister_class( cls)