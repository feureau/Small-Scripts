#####################################################

# <FLARED is an add-on for Blender that creates lens flare VFX in Eevee.>
# Copyright (C) <2019-2020>  <Beniamino Della Torre e Alfonso Annarumma>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# You can contact the creator of Flared here: blenderlensflare@gmail.com

#####################################################


import bpy
from bpy.types import Panel, UIList
from bpy.props import FloatProperty



from . import (operators)
import flaredvfx 



def lensflare_type(type):
    t="none"
    if type == 'A':
        t = "OCT"
        i = 0
    if type == 'B':
        t = "SCI"
        i = 1 
    if type == 'C':
        t = "ROU" 
        i = 2
    if type == 'D':
        t = "SIM"
        i = 3
    if type == 'E':
        t = "GRE"
        i = 4 
    if type == 'F':
        t = "ADA"
        i = 5
    if type == 'G':
        t = "HRZ"
        i = 6 
    if type == 'H':
        t = "SUB"
        i = 7   
    if type == 'I':
        t = "HOO" 
        i = 8
    return t,i

class LIST_UL_lensflare(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        lensflare_item = item
        
        if item.multy_cam:
            i_cam = 'OUTLINER_OB_CAMERA'
        else:
            i_cam = 'CAMERA_DATA'
        if item.select:
            i_sel =  'RESTRICT_SELECT_OFF'
        else:
            i_sel = 'RESTRICT_SELECT_ON' 
        
        
#        if item.select_light:
#            i_light = 'OUTLINER_OB_LIGHT' 
#        else:
#            i_light = 'LIGHT_DATA'
        
        
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            light = item.light
            if light:
                lensflareprop = light.lensflareprop
                type,i = lensflare_type(lensflareprop.flared_type)
                
                #print(flaredvfx.preview_collections)
                pcoll = flaredvfx.preview_collections["main"]
                if pcoll.flared_previews != ():
                    pcoll.flared_previews.sort()
                    row = layout.row()
                    my_icon = pcoll.flared_previews[i]
            
            layout.alignment = 'RIGHT'
            
            row = layout.row(align=False)
            if light:
                row.prop(lensflare_item, "flared_type",  icon_value=my_icon[3], emboss=False)
            row.prop(lensflare_item, "multy_cam", text="", emboss=False, icon=i_cam)
            #row.prop(lensflare_item, "select_light", icon=i_light, text="", emboss=False)
            row.prop(lensflare_item, "name", text="", emboss=False,expand=False)
            row.prop(lensflare_item, "select", text="", emboss=False, icon=i_sel)
            
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
    


        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'

class OBJECT_MT_flared_extra_menu(bpy.types.Menu):
    bl_label = "Flared Extra Menu"
    bl_idname = "OBJECT_MT_flared_extra_menu"

    def draw(self, context):
        
        layout = self.layout
        engine = context.scene.render.engine
        layout.operator("scene.flared_copy_settings", icon='PASTEDOWN', text="Copy Settings from Active To Select")
        layout.operator("scene.lensflare_popup_remove_flare", icon='PANEL_CLOSE', text="Delete Select").field = 'SELECT'
        layout.operator("scene.lensflare_popup_remove_flare", icon='PANEL_CLOSE', text="Delete Not Select").field = 'NOT_SELECT'
        layout.operator("scene.lensflare_popup_remove_flare", icon='PANEL_CLOSE', text="Delete All").field = 'ALL'
        layout.operator("scene.lensflare_item_select", icon='SELECT_EXTEND', text="Select All").all = True
        layout.operator("scene.lensflare_item_select", icon='SELECT_SET', text="Select None").none = True
        layout.operator("scene.lensflare_item_select", icon='SELECT_DIFFERENCE', text="Invert Selection").invert = True
        if engine == 'CYCLES':
            layout.operator("scene.lensflare_item_view_layer", icon='RENDERLAYERS', text="Move Selected Flares on a new Eevee Scene")
            for scn in bpy.data.scenes:
                if scn.flared_comp:
                    layout.operator("scene.lensflare_item_view_layer", icon='FILE_REFRESH', text="Update Eevee Scene").update = True
    

class PANEL_PT_lensflare_type(Panel):
    """Flared Type Panel"""
    bl_label = "Flared Type"
    bl_idname = "PANEL_PT_lensflare_type"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Flared"
    
    def draw(self, context):
        
        scene = context.scene
        idx = scene.lensflareitems_index
        wm = context.window_manager
        obs = context.selected_objects
        layout = self.layout      
        
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons["flaredvfx"].preferences
        execute = True
        active = True
        operators.key = addon_prefs.key
        error = addon_prefs.error
        reset = addon_prefs.reset
        if not execute:
            row = layout.row()
            row.label(text=error)
            row.label(text="Insert Key")
            
            row = layout.row()
            row.prop(addon_prefs, "key", text="Key")
            
            row = layout.row()
            if active:
                
                row.operator("scene.lensflare_login").validation = True
            
                row.operator("scene.lensflare_login", text="Reset").reset = True
            else:
                
                row.operator("scene.lensflare_login", text="Active").activation = True
            
                row.operator("scene.lensflare_login", text="Reset").reset = True

        else:      
            row = layout.row()
            row.template_icon_view(wm, "flared_previews")
            
            
            row = layout.row()
            row.prop(scene, "lensflarecamera", text="Camera")
            row = layout.row()
            col = row.column()
            if obs == []:
                col.label(text="Select Lights sources")
            else:
                col.label(text="Selected Lights sources:")
            for ob in obs:
                row = col.row()
                row.label(text="- "+ob.name)
                
                #row.prop(ob, "lensflare", text="In Use")
            #row.prop(scene, "lensflarelight", text="Light")
            
            
            
            
            # This code goes in the panel's draw()
            
           
            
            row = layout.row()
            row.template_list("LIST_UL_lensflare", "", scene, "lensflareitems", scene, "lensflareitems_index")   
            col = row.column(align=True)
            col.operator("scene.lensflare_item_add", icon='ADD', text="")
            if idx != -1: 
                col.operator("scene.lensflare_popup_remove_flare", icon='REMOVE', text="").field = 'ACTIVE'
                
                col.separator()
                #col.operator("scene.flared_copy_settings", icon='PASTEDOWN', text="")
                col.menu("OBJECT_MT_flared_extra_menu", icon='DOWNARROW_HLT', text="")
                col.separator()
                
                up = col.operator("scene.lensflare_item_move", icon='TRIA_UP', text="")
                down =col.operator("scene.lensflare_item_move", icon='TRIA_DOWN', text="")
                up.idx = idx
                down.idx = idx
                up.move = 'UP'
                down.move = 'DOWN'
            if idx > -1:
                light = scene.lensflareitems[idx].light
                if light :
                    type,i = lensflare_type(light.lensflareprop.flared_type)
    #                ob_sel = context.object
    #                if ob_sel.lensflare:
    #                    id = ob_sel.lensflareprop.id
    #                    items_list = scene.lensflareitems.keys()
    #                    index = items_list.index(id)
    #                    scene.lensflareitems_index = index
                    #preset: 
                    row = layout.row()
                    
                    row.menu('SCENE_MT_FlaredPresets', text='Presets') 
                    row.operator('flared.add_preset', text='', icon='ADD').name = type+"_"
                    row.operator("scene.lensflare_popup_remove_preset", icon='REMOVE', text="").field = 'PRESET'
                    #row.operator('flared.add_preset', text='', icon='REMOVE').remove_active = True
                
        
# We can store multiple preview collections here,
# however in this example we only store "main"
preview_collections = {} 
    
class PANEL_PT_lensflare(Panel):
    """Flared Panel Tools"""
    bl_label = "Flared Proprieties"
    bl_idname = "PANEL_PT_lensflare"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "PANEL_PT_lensflare_type"
    

    
    def draw(self, context):
        
        colls = bpy.data.collections
        scene = context.scene
        idx = scene.lensflareitems_index
        
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons["flaredvfx"].preferences
        execute = True
        active = True
        if execute:    
        
            if idx > -1:
            
                item = scene.lensflareitems[idx]
                
                id = item.id
                light = item.light
                if light:
                    #coll = find_coll(colls, id)        
                    coll = light.lensflareprop
                    type = coll.flared_type
                    layout = self.layout
                    layout.use_property_split = True
                    
                    if type == 'F':
                        
                        row = layout.row() 
                        col = row.column(align=True)
                        
                        col.prop(coll,"focal")
                        col.prop(coll,"global_emission")
                        col.prop(coll,"global_color")
                        col.prop(coll,"global_color_influence")                
                        
                        row = layout.row()
                        col = row.column(align=True)                
                        col.prop(coll,"glow_scale")
                        col.prop(coll,"glow_emission")

                        row = layout.row()
                        col = row.column(align=True)                
                        col.prop(coll,"streak_emission")
                        
                        row = layout.row()
                        col = row.column(align=True)
                        col.prop(coll,"scale_x",text="Light Scale X")         
                        col.prop(coll,"scale_y",text="Light Scale Y")
                        col.prop(coll,"sun_beam_emission",text="Light Emission")
                        #col.prop(coll,"rot_glow_light")         
                                        
                        row = layout.row()
                        col = row.column(align=True)
                        col.prop(coll,"global_scale", text="Hoop Scale")
                        col.prop(coll,"iris_emission", text="Hoop Emission")
                        
                        row = layout.row()
                        row.prop(coll,"dirt_amount")
                        
                        row = layout.row()
                        row.prop(coll,"obstacle_occlusion")
                        
                    
                    else:
                        
                        row = layout.row() 
                        col = row.column(align=True)
                        
                        col.prop(coll,"focal")
                        col.prop(coll,"global_scale")
                        col.prop(coll,"global_emission")
                        col.prop(coll,"global_color")
                        col.prop(coll,"global_color_influence")
                        
                        row = layout.row()
                        col = row.column(align=True)
                        
                        col.prop(coll,"glow_scale")
                        col.prop(coll,"glow_emission")
                        
                        row = layout.row()
                        col = row.column(align=True)
                        
                        col.prop(coll,"streak_scale")
                        col.prop(coll,"streak_emission")
                        
                        row = layout.row()
                        col = row.column(align=True)
                        
                        col.prop(coll,"sun_beam_scale")
                        col.prop(coll,"sun_beam_number")
                        if type == 'B' or type == 'A' or type =="G":
                            col.prop(coll,"sun_beam_rand")
                        col.prop(coll,"sun_beam_emission")
                        
                        row = layout.row()
                        col = row.column(align=True)
                        
                        
                        col.prop(coll,"iris_scale", text="Ghost Scale")
                        if type != 'D':
                            col.prop(coll,"iris_number", text="Ghost Number")
                        col.prop(coll,"iris_emission", text="Ghost Emission")
                        
                        row = layout.row()
                        row.prop(coll,"dirt_amount")
                        
                        row = layout.row()
                        row.prop(coll,"obstacle_occlusion")
          



