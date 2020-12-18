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
import os
import requests
from bpy.types import  Operator
key = ""
url = "https://www.blenderlensflare.com/validation.php"
import importlib
from . import (
    function,
)
from bpy.props import EnumProperty, StringProperty, BoolProperty, IntProperty, CollectionProperty, FloatProperty, FloatVectorProperty, PointerProperty

def ShowMessageBoxLayer(message = "", title = "Flared Warning", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO', field='NONE'):

    def draw(self, context):
        idx = context.scene.lensflareitems_index
        
        layout = self.layout
        if field == 'PRESET':
            message = "Remove Preset?"
        else:
            message = "Remove Flare?"
        row = layout.row()
        row.label(text=message)
        
        
        row = layout.row()   
        
        row.operator("scene.lensflare_cancel", text= "NO")
        row = layout.row()
        
        
        if field == 'ACTIVE':
            remove = row.operator("scene.lensflare_item_remove", text= "YES")
            remove.idx = idx
            remove.active = True
            
        
        if field == 'SELECT':   
            row.operator("scene.lensflare_item_remove", text= "YES").select = True
        
        if field == 'NOT_SELECT':
            row.operator("scene.lensflare_item_remove", text= "YES").not_select = True
        
        if field == 'ALL':
            row.operator("scene.lensflare_item_remove", text= "YES").all = True
        
        if field == 'PRESET':
            row.operator("flared.add_preset", text= "YES").remove_active=True
        
                
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


class SCENE_OT_Cancel(Operator):
    """Cancel Button"""
    bl_idname = "scene.lensflare_cancel"
    bl_label = "Cancel Button"
    
        
    def execute(self, context):
        
        
        return {'CANCELLED'}

class SCENE_OT_Login(Operator):
    """Login to server"""
    bl_idname = "scene.lensflare_login"
    bl_label = "Login"
    
    
    reset : BoolProperty(default=False)
    activation : BoolProperty(default=False)
    validation : BoolProperty(default=False)
    close : BoolProperty(default=False)
    
    def execute(self, context):
        
        user_preferences = context.preferences
        addon_prefs = user_preferences.addons["flaredvfx"].preferences
        
        global key
        global url
        url = "https://www.blenderlensflare.com/validation.php"
        key = addon_prefs.key       
        if self.reset:
            addon_prefs.execute = False
            url = "https://www.blenderlensflare.com/reset.php"
            importlib.reload(function)
        if self.activation:
            addon_prefs.execute = False
            addon_prefs.start = False
            url = "https://www.blenderlensflare.com/activation.php"
            importlib.reload(function)    
        if self.validation:
            addon_prefs.execute = False
            url = "https://www.blenderlensflare.com/validation.php"
            importlib.reload(function)
        if self.close:
            #addon_prefs.execute = False
            url = "https://www.blenderlensflare.com/close.php"
            importlib.reload(function)
            
        self.reset = False  
        self.activation = False  
        self.validation = False  
        self.close = False  
  
        return {'FINISHED'}


class SCENE_OT_popup_remove_preset(Operator):
    """ """
    bl_idname = "scene.lensflare_popup_remove_preset"
    bl_label = "Remove Active Preset"
    
    field : StringProperty()
    
        
    def execute(self, context):
        #print ("ok")
        ShowMessageBox("Remove Flare?", "REMOVE FLARED", 'INFO', self.field)
        return {'FINISHED'}

class SCENE_OT_popup_remove_flare(Operator):
    """ """
    bl_idname = "scene.lensflare_popup_remove_flare"
    bl_label = "Remove Active Flare"
    
    field : StringProperty()
    
        
    def execute(self, context):
        #print ("ok")
        ShowMessageBox("Remove Flare?", "REMOVE FLARED", 'INFO', self.field)
        return {'FINISHED'} 

class SCENE_OT_flared_copy_settings(Operator):
    """Copy Setting from Active to selected"""
    bl_idname = "scene.flared_copy_settings"
    bl_label = "Copy Flared Settings"
    
        
    def execute(self, context):
        
        function.copy_prop(self,context)
        return {'FINISHED'}

class SCENE_OT_lensflare_item_view_layer(Operator):
    """Move selected flares on new view layer"""
    bl_idname = "scene.lensflare_item_view_layer"
    bl_label = ""
    
    name : StringProperty(default = "Eevee Scene Flared", name="New Scene")
    composite : BoolProperty(default=False, name="Add Composite Nodes", 
                                description = "Automatically Create a Compositor Nodes Setup? PAY ATTENTION: This could create a bad node setup if you are already using compositor nodes")
    update : BoolProperty(default=False, name="Update Eevee Scene", 
                                description = "Update Eevee Scene if you add extra Camera and modify Bind Marker")
    
    def execute(self, context):
        scene = context.scene
        items = scene.lensflareitems
        
        
            
            
        layer_name, s_name = function.add_view_layer_flare(self, context)
        
        if self.composite:
            function.composite_setup(self, context,layer_name, s_name)
        self.update = False
        return {'FINISHED'}
    def invoke(self, context, event):
        scene = context.scene
        items = scene.lensflareitems
        
        select = False
        
        list = []
        for it in items:
            if it.select:
                select = True
                list.append(it.name)
        if not self.update:
            for scn in bpy.data.scenes:
                if scn.flared_comp:
                    flared_scene = scn
                    if len(list) == 1:
                        item = items[list[0]]
                        if item.id not in flared_scene.collection:
                            ShowMessageBoxLayer("Flared already present", "Warning", 'ERROR')
                            return {'FINISHED'}
            
        if select:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            ShowMessageBoxLayer("Please, select flares first", "Warning", 'ERROR')
            return {'FINISHED'}
    def draw(self, context):
        scenes = bpy.data.scenes
        flared_comp = False
        for scene in scenes:
            if scene.flared_comp == True:
                flared_comp = True
                break
        
        row = self.layout
        if self.update:
            row.label(text="Update Eevee Flare Scene")
        else:
            row.label(text="Move selected Flares on a new Eevee Scene")
        
       
        if not flared_comp:
            row = self.layout
            row.label(text="Create new nodes?")
            row = self.layout
            row.prop(self, "composite")
            
            
            if self.composite:
                row = self.layout
                row.label(text="This operation will delete your node setup")
            
        
class SCENE_OT_lensflare_item_remove(Operator):
    """Remove item"""
    bl_idname = "scene.lensflare_item_remove"
    bl_label = "Remove Lensflare to list"
    
    idx : IntProperty()
    active : BoolProperty(default=False)
    select : BoolProperty(default=False)
    not_select : BoolProperty(default=False)
    all : BoolProperty(default=False)
    
    def execute(self, context):
        
        if self.active:
        
            function.remove_flare_active(self, context)
        else:    
            function.remove_flare(self, context)

        return {'FINISHED'}

class SCENE_OT_lensflare_item_select(Operator):
    """Select Flare"""
    bl_idname = "scene.lensflare_item_select"
    bl_label = "Select Lensflare in list"
    
    
    none : BoolProperty(default=False)
    invert : BoolProperty(default=False)
    all : BoolProperty(default=False)
    
    def execute(self, context):
        
        function.selection(self, context)

        return {'FINISHED'}

class SCENE_OT_lensflare_item_move(Operator):
    """Move item"""
    bl_idname = "scene.lensflare_item_move"
    bl_label = "Move Lensflare in list"
    
    move : StringProperty()
    idx : IntProperty()
    
    
    def execute(self, context):
        scene = context.scene
        lensflareitems = scene.lensflareitems
        idx = self.idx
        if self.move == 'UP':
            lensflareitems.move(idx, idx-1)
            scene.lensflareitems_index = idx-1    
        if self.move == 'DOWN':
            lensflareitems.move(idx, idx+1)
            scene.lensflareitems_index = idx+1

        return {'FINISHED'}    
    

class CAMERA_OT_LensFlareCamera(Operator):
    """ """
    bl_idname = "scene.lensflare_item_add"
    bl_label = "Add Lens Flare/s"
    bl_options = {'REGISTER', 'UNDO'}
    #bl_options = {'PRESET'}

    def execute(self, context):
        function.main(self, context)
        return {'FINISHED'}


