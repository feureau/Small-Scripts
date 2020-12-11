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


bl_info = {
    "name": "Flared",
    "author": "Beniamino Della Torre, Alfonso Annarumma",
    "version": (1, 6, 7),
    "blender": (2, 81, 0),
    "location": "View3D > Toolbox",
    "description": "Create Optical Lens Flare from Light to Camera ",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
    }
import importlib

if "bpy" in locals():
    
    importlib.reload(ui)
    
    importlib.reload(function)
    importlib.reload(func_part)
    importlib.reload(operators)

    

else:

    from . import (ui, func_part, operators)

import bpy
import os
from bpy.types import WindowManager
from bpy.types import Menu, Panel, UIList, PropertyGroup, Operator, AddonPreferences
from bpy.props import EnumProperty, StringProperty, BoolProperty, IntProperty, CollectionProperty, FloatProperty, FloatVectorProperty, PointerProperty
from bl_operators.presets import AddPresetBase
from bpy.app.handlers import persistent
    






    




preview_collections = {} 
# queste funzioni servono a filtrare i tipi di oggetti delle proprieta Camera e Luce da scegliere per
# aggiungere il Lensflare
#####################################################
def scene_CAMERA_poll(self, object):
    return object.type == 'CAMERA'

def scene_LIGHT_poll(self, object):
    return object.type == 'LIGHT'
#####################################################

# funzione per la ricerca delle immagini nella cartella icon dei preset del lensflare
def enum_previews_from_directory_items(self, context):
    """EnumProperty callback"""
    enum_items = []

    if context is None:
        return enum_items

    wm = context.window_manager
    config_dir = bpy.utils.resource_path('USER')+"/scripts/addons/flaredvfx/flared/"
    #directory = os.path.join(os.path.dirname(__file__), "icon")
    directory =os.path.join(config_dir, "icon")
    #print (directory)
    # Get the preview collection (defined in register func).
    pcoll = preview_collections["main"]

    if directory == pcoll.flared_previews_dir:
        return pcoll.flared_previews

    #print("Scanning directory: %s" % directory)
    
    user_preferences = bpy.context.preferences
    addon_prefs = user_preferences.addons["flaredvfx"].preferences

    #print(addon_prefs.start)
    

    if directory and os.path.exists(directory):
        # Scan the directory for png files
        image_paths = []
        for fn in os.listdir(directory):
            if fn.lower().endswith(".jpg"):
                image_paths.append(fn)

        for i, name in enumerate(image_paths):
            # generates a thumbnail preview for a file.
            filepath = os.path.join(directory, name)
            thumb = pcoll.load(filepath, filepath, 'IMAGE')
            enum_items.append((name, name, "", thumb.icon_id, i))

    pcoll.flared_previews = enum_items
    pcoll.flared_previews_dir = directory
    return pcoll.flared_previews

@persistent
def load_handler(dummy):
    scene = bpy.context.scene
    flares = scene.lensflareitems
    
    for flare in flares:
        if flare.multy_cam:
            cam = scene.camera
        else:
            cam = flare.camera
        coll = bpy.data.collections[flare.name]
        ob = coll.all_objects["EmptyCameraOrigin"+flare.suffix]
        for const in ob.constraints:
            const.target = cam 

            



class FlaredPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    key : StringProperty(default="",
            name="Key",
            )
    execute : BoolProperty(default=False)
    active : BoolProperty(default=False)
    reset : BoolProperty(default=False)
    start : BoolProperty(default=True)
    error : StringProperty(default='')
    
    
    def draw(self, context):
        layout = self.layout
#        if not self.execute:
#            row = layout.row()
#            row.label(text=self.error)
#            row.label(text="Insert Key")
#            
#            row = layout.row()
#            row.prop(self, "key", text="Key")
#            
#            row = layout.row()
#            
#            if self.active:
#                
#                row.operator("scene.lensflare_login").validation = True
#                
#                row.operator("scene.lensflare_login", text="Reset").reset = True
#            else:
#                
#                row.operator("scene.lensflare_login", text="Active").activation = True
#                
#                row.operator("scene.lensflare_login", text="Reset").reset = True
            


class PROP_PG_lensflare(PropertyGroup):
    
    
    focal : FloatProperty(default=1.0, description="", min=0.0, max=5000.0,
     name="Focal Length", options={'ANIMATABLE'})
    
    global_scale : FloatProperty(default=0.0, description="",
     name="Global Scale",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})
     
    glow_scale : FloatProperty(default=1.0, description="",
     name="Glow Scale",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})
    
    streak_scale : FloatProperty(default=1.33, description="",
     name="Streak Scale",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})
    
    sun_beam_rand : FloatProperty(default=0.888, description="",
     name="Sun Beam Random",min=0, soft_min=0, soft_max=1.0,options={'ANIMATABLE'})  
    
    sun_beam_scale : FloatProperty(default=0.39, description="",
     name="Sun Beam Scale",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})  
    
    sun_beam_number : IntProperty(default=22, min=0, max=2000, description="",
     name="Sun Beam Number",update=func_part.update_particle) 
    
    iris_scale : FloatProperty(default=0.47, description="",
     name="Iris Scale",min=0, soft_min=0, soft_max=4.0,options={'ANIMATABLE'}) 
    
    iris_number : IntProperty(default=58, description="", min=0, max=200,
     name="Iris Number", update=func_part.update_particle )   
    
    global_color : FloatVectorProperty(default=(1.0, 1.0, 1.0, 1.0), size=4, description="",
     name="Global Color",subtype='COLOR', min=0.0, max=1.0,options={'ANIMATABLE'} )
    
    global_color_influence : FloatProperty(default=0.0, description="",
     name="Global Color Influence",min=0, soft_min=0, soft_max=1.0,options={'ANIMATABLE'} )
    
    dirt_amount : FloatProperty(default=0.26, description="",
     name="Dirt Amount",min=0, soft_min=0, soft_max=1.0,options={'ANIMATABLE'})
    
    global_emission : FloatProperty(default=0.0, description="",
     name="Global Emission",min=0, soft_min=0, soft_max=1,options={'ANIMATABLE'})

    glow_emission : FloatProperty(default=0.64, description="",
     name="Glow Emission",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})
     
    streak_emission : FloatProperty(default=0.48, description="",
     name="Streak Emission",min=0, soft_min=0, soft_max=2.0,options={'ANIMATABLE'})
    
    sun_beam_emission : FloatProperty(default=0.78, description="",
     name="Sun Beam Emission",min=0, soft_min=0, soft_max=3.0,options={'ANIMATABLE'})
    
    iris_emission : FloatProperty(default=1.0, description="",
     name="Iris Emission",min=0, soft_min=0, soft_max=4.0,options={'ANIMATABLE'})
    
    obstacle_occlusion : FloatProperty(default=1.0, description="",
     name="Obstacle Occlusion",min=0, soft_min=0, soft_max=1.0,options={'ANIMATABLE'})
    
    exlude_dof : BoolProperty(default=True, description="",
     name="Exlude From DoF")    
    #numero identificativo di ogni lens flare che viene aggiunto in scena 
    id : StringProperty(
     name="Lensflare ID")
    
    flared_type : StringProperty(
     name="Flared Type")
    
    camera : PointerProperty(
        type=bpy.types.Object)
    light : PointerProperty(
        type=bpy.types.Object)   
    rot_glow_light : FloatVectorProperty(default=(0.0, 0.0, 0.0), name="Light Rotation", min = 0.0, max = 5000.0, 
    subtype='EULER', unit='ROTATION',options={'ANIMATABLE'})
    
    scale_x : FloatProperty(default=1.0, description="",
     name="Scale X",min=0, soft_min=0, soft_max=10.0,options={'ANIMATABLE'})
    
    scale_y : FloatProperty(default=1.0, description="",
     name="Scale Y",min=0, soft_min=0, soft_max=10.0,options={'ANIMATABLE'})
    
class SCENE_OT_lensflare_preset(AddPresetBase, Operator):
    """ """ 
    bl_idname = 'flared.add_preset' 
    bl_label = 'Save current Properties into a Preset' 
    preset_menu = 'SCENE_MT_FlaredPresets' 
    # Common variable used for all preset values 
    
    preset_defines = [  
    'idx = bpy.context.scene.lensflareitems_index',
    'light = bpy.context.scene.lensflareitems[idx].light.lensflareprop',  
      
    ] 
    
    # Properties to store in the preset 
    
    preset_values = [ 
    'light.focal',
    'light.global_scale', 
    'light.glow_scale', 
    'light.streak_scale', 
        'light.sun_beam_rand', 
    'light.sun_beam_scale', 
    'light.sun_beam_number', 
    'light.iris_scale', 
    'light.iris_number', 
    'light.global_color', 
    'light.global_color_influence', 
    'light.dirt_amount', 
    'light.global_emission', 
    'light.glow_emission', 
    'light.streak_emission', 
    'light.sun_beam_emission', 
    'light.iris_emission', 
    'light.obstacle_occlusion', 
    'light.exlude_dof', 
    'light.rot_glow_light', 
    'light.scale_x', 
    'light.scale_y', 
    ] 
    # Directory to store the presets 
    preset_subdir = 'flared'

class SCENE_MT_FlaredPresets(Menu): 
    bl_label = 'Menu Preset' 
    preset_subdir = 'flared' 
    preset_operator = 'script.execute_preset' 
    draw = Menu.draw_preset      
    
class ITEM_PG_lensflare(PropertyGroup):
    flared_type : StringProperty(name="", description ="Flared Type")
    id : StringProperty(
     name="")
    suffix : StringProperty(
     name="")
     
    light : PointerProperty(
        type=bpy.types.Object
    )
    
    select : BoolProperty(name="Select", default = False, description = "Select Flares. Use the Extra Menu on the right to apply multiple functions")
    multy_cam : BoolProperty(name="MultiCamera", default = False, description = "If active, the flare follows active camera change in animation")
    
    camera : PointerProperty(
        type=bpy.types.Object,
        poll=scene_CAMERA_poll
    )    

classes = ( FlaredPreferences,
            
            ui.PANEL_PT_lensflare_type, 
            ITEM_PG_lensflare,
            ui.PANEL_PT_lensflare,             
            PROP_PG_lensflare,
            ui.LIST_UL_lensflare,
            ui.OBJECT_MT_flared_extra_menu,
            operators.SCENE_OT_lensflare_item_remove,
            operators.SCENE_OT_lensflare_item_select,
            operators.SCENE_OT_lensflare_item_move,
            SCENE_OT_lensflare_preset,
            SCENE_MT_FlaredPresets,
            operators.CAMERA_OT_LensFlareCamera,
            operators.SCENE_OT_popup_remove_preset,
            operators.SCENE_OT_popup_remove_flare,
            operators.SCENE_OT_Cancel,
            operators.SCENE_OT_flared_copy_settings,
            operators.SCENE_OT_Login,
            operators.SCENE_OT_lensflare_item_view_layer,
           
         
            
            
)

def register():
    
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    WindowManager.flared_previews_dir = StringProperty(
        name="Folder Path",
        subtype='DIR_PATH',
        default=""
    )

    WindowManager.flared_previews = EnumProperty(
        items=enum_previews_from_directory_items,
    )
    
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()
    pcoll.flared_previews_dir = ""
    pcoll.flared_previews = ()

    preview_collections["main"] = pcoll
    
    bpy.app.handlers.frame_change_post.append(load_handler)
    bpy.types.Scene.lensflareitems = CollectionProperty(type=ITEM_PG_lensflare)
    # Unused, but this is needed for the TemplateList to work...
    bpy.types.Scene.lensflareitems_index = IntProperty(default=-1,update=function.light_select)
    bpy.types.Scene.prev_light = StringProperty(default="")
    bpy.types.Scene.flared_comp = BoolProperty(default=False)
    # oggetto camera da scegliere
    bpy.types.Scene.lensflarecamera = PointerProperty(
        type=bpy.types.Object,
        poll=scene_CAMERA_poll,
        name="Select the camera",
        description="",
    )
    # oggetto luce da scegliere
    bpy.types.Scene.lensflarelight = PointerProperty(
        type=bpy.types.Object
    )
    bpy.types.Object.lensflareprop = PointerProperty(type=PROP_PG_lensflare)  
    
    bpy.types.Object.lensflare = BoolProperty(default=False)
    
    # creare la directory dei preset e copiarci dentro il preset
    config_dir = bpy.utils.resource_path('USER')
    my_presets = config_dir+'/scripts/presets/flared'
    # Ensure only meshes are passed to this function
    
#    if not os.path.isdir(my_presets): 
#        # makedirs() will also create all the parent folders (like "object") 
#        os.makedirs(my_presets) 
#        # Get a list of all the files in your bundled presets folder 
#        files = os.listdir(my_bundled_presets) 
#        # Copy them 
#        [shutil.copy2(os.path.join(my_bundled_presets, f), my_presets) for f in files]
    #import importlib
    #importlib.reload(function)


def unregister():
    bpy.app.handlers.frame_change_post.remove(load_handler)
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    
    del WindowManager.flared_previews
    del WindowManager.flared_previews_dir
    del bpy.types.Scene.lensflareitems
    del bpy.types.Scene.lensflareitems_index
    del bpy.types.Scene.lensflarecamera
    del bpy.types.Scene.lensflarelight
    del bpy.types.Scene.flared_comp
    del bpy.types.Scene.prev_light
    del bpy.types.Object.lensflare
    del bpy.types.Object.lensflareprop
    
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    


    

