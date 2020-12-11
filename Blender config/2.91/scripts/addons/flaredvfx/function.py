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
import random
from mathutils import Vector
from . import (
    flare_a,
    flare_b,
    flare_c,
    flare_d,
    flare_e,
    flare_f,
    flare_g,
    flare_h,
    flare_i,
    particle,
    ui,
)
# Callback function for location changes
def obj_selection_callback(ob):
    
    # Do something here
    ob = bpy.context.object
    ob.select_set(True)
    scene = bpy.context.scene
    items = scene.lensflareitems
    idx = scene.lensflareitems_index
    if idx>-1:
                
        if ob.lensflare:
            id = ob.lensflareprop.id
            items_list = scene.lensflareitems.keys()
            index = items_list.index(id)
            scene.lensflareitems_index = index
    else:
        print(".")
# Subscribe to the context object (mesh)
def subscribe_to_obj_selection(ob):
    ob = bpy.context.object
    
#    if ob.type != 'MESH':
#        print ("OK")
#        return
    
    subscribe_to =  bpy.types.LayerObjects, "active"
    
    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        # owner of msgbus subcribe (for clearing later)
        owner=ob,
        # Args passed to callback function (tuple)
        args=(ob,),
        # Callback function for property update
        notify=obj_selection_callback,
    )

def active_collection(context,id):
    l_colls = context.view_layer.layer_collection.children[id]
    l_colls.exclude = False
    for coll in l_colls.children:
        coll.exclude = False
    

def light_select(self, context):
    items = self.lensflareitems
    flare = items[self.lensflareitems_index]
    light = flare.light
    light.select_set(True)
    
    if self.prev_light != "":
        prev_light = bpy.data.objects[self.prev_light]
        prev_light.select_set(False)
        #print(self.prev_light)
    self.prev_light = light.name
    
    #self.select_light = self.light.select_get()
        

def make_suffix(obs):
    s="abcdefghijklmnopqrstuvwxyz0123456789"
    suffix = "."
    for i in range(5):
        suffix += random.choice(s)
    
    for ob in obs:
        n = ob.name
        ob.cycles_visibility.camera = False
        ob.cycles_visibility.diffuse = False
        ob.cycles_visibility.glossy = False
        ob.cycles_visibility.scatter = False
        ob.cycles_visibility.shadow = False
        ob.cycles_visibility.transmission = False
        if "." in n:
            split = n.split(".")  
          
            ob.name = split[0].suffix
        else:
            ob.name += suffix
    return suffix

def copy_prop_test(self,context):
    lights = context.selected_objects
    active = context.active_object
    for light in lights:
        if light.lensflare:
            if light != active:
                props = light.lensflareprop
                keys = props.keys()
                for key in keys:
                    if props.flared_type==active.lensflareprop.flared_type:
                        props[key] = active.lensflareprop[key]
                        
def remove_flare_active(self,context):
    scene = context.scene
        
    if scene.lensflareitems.items() != []:
        
        bpy.ops.object.select_all(action='DESELECT')
        idx = self.idx
        colls = bpy.data.collections
        item = scene.lensflareitems[idx]
        data = bpy.data
        if item.light:
            item.light.lensflare = False
        
        coll = colls[item.id]
        active_collection(context, item.id)
                
        for ob in coll.all_objects:
            ob.select_set(True)
        bpy.ops.object.delete(use_global=False, confirm=False)
        for child in coll.children:
            colls.remove(child)
        colls.remove(coll)
        
        
        
        scene.lensflareitems.remove(idx)
        if scene.lensflareitems_index > - 1:
            scene.lensflareitems_index = len(scene.lensflareitems) - 1
    self.active = False
    
def get_index(item, context):
    items = context.scene.lensflareitems
    keys = items.keys()
    #print ("nome:"+item)
    index = keys.index(item)
    return index

def selection(self, context):
    items = context.scene.lensflareitems
    list = []
    for item in items:
        list.append(item.name)

    for item in items:
        
        if self.all:
            item.select = True
        if self.none:
            item.select = False
        if self.invert:
            s = item.select
            item.select = not s
    self.all = False
    self.none = False
    self.invert = False
    #items = 0

def composite_setup(self, context,layer_name, s_name):
    
    
    
    scene = context.scene
    #attivo i nodi in scena
    scene.use_nodes = True
    scene.render.use_compositing = True
    data = bpy.data
    #scene = data.scenes.new("Flared_compositing")
    #scene.render.filepath = filepath
    
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
    
    footage = nodes.new("CompositorNodeRLayers")
    footage.location = Vector((-500,-500))
    composite = nodes.new("CompositorNodeComposite")
    
    flare = nodes.new("CompositorNodeRLayers")
    mix = nodes.new("CompositorNodeMixRGB")    
    mix.blend_type = 'ADD'
    flare.scene = data.scenes[s_name]

    links.new(footage.outputs[0], mix.inputs[1])
    links.new(flare.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], composite.inputs[0])
    composite.select = True
    nodes.active = composite
    
    footage.location = Vector((-500,-500))
    flare.location = Vector((-500,0))
    mix.location = Vector((-0,0))
    composite.location = Vector((500,0))
    

def add_view_layer_flare(self,context):
    
    _scene = context.scene
    #idx = scene.lensflareitems_index
    items = _scene.lensflareitems
    layer_name = "Flared Layer"
    s_name = self.name
    list = []
    data = bpy.data
    cameras = []
    #carico in list tutti i nomi delle collection dei flare selezionati
    for ob in _scene.collection.all_objects:
        if ob.type == 'CAMERA':
            cameras.append(ob.name)
            #print(cameras)
    for it in items:
        
        if it.select:
            list.append(it.name)      
    
    # se siamo in Cycles viene create una nuova scena        
    if _scene.render.engine == 'CYCLES':
        s_name = "Eevee_"+self.name
        if s_name not in data.scenes:
            scene = data.scenes.new(s_name)
        else:
            scene = data.scenes[s_name]
        scene.flared_comp = True
        scene.render.film_transparent = False
        w = bpy.data.worlds.new("FladerWorld")
        w.color = (0.0, 0.0, 0.0)
        scene.world = w
        
        layer = scene.view_layers[0]
        layer.name = layer_name
        for camera in cameras:
            if camera not in scene.collection.objects:
                cam = _scene.collection.all_objects[camera]
                scene.collection.objects.link(cam)
        active_cam = scene.collection.all_objects[_scene.camera.name]
        #print(active_cam)
        scene.camera = active_cam
        scene.timeline_markers.clear()
        for marker in _scene.timeline_markers:
            
            m = scene.timeline_markers.new(marker.name, frame=marker.frame)
            m.camera = marker.camera
        
        for coll in data.collections:
            if coll.name in list:
                if coll.name not in layer.layer_collection.collection.children:
                    layer.layer_collection.collection.children.link(coll)
                #camera = items[coll.name].camera
                
    else:
        layer = scene.view_layers.new(layer_name)
        
    
        for coll in layer.layer_collection.children:
            if coll.name in list:
                coll.exclude = False
            else:
                coll.exclude = True    
#    for coll in context.view_layer.layer_collection.children:
#        if coll.name in list:
#            if not coll.exclude:
#                coll.exclude = True
        
    return layer_name, s_name

def remove_flare(self,context):
    
    scene = context.scene
    #idx = scene.lensflareitems_index
    colls = bpy.data.collections
    items = scene.lensflareitems
    
    select = self.select
    not_select = self.not_select
    all = self.all
    
    bpy.ops.object.select_all(action='DESELECT')
    it_list = []
    not_list = []
    
    if scene.lensflareitems.items() != []:
        
        for it in items:
            
            if it.select:
                it_list.append(it.name)      
            else:
                not_list.append(it.name)
        #print(it_list)
        if select:
            list = it_list
        if not_select:
            list = not_list
        if all:
            list= it_list+not_list
            
        for name in list:
            item = items[name]
            if item.light:
                item.light.lensflare = False
            coll = colls[item.id]
            active_collection(context,item.id)
            for ob in coll.all_objects:
                ob.select_set(True)
            bpy.ops.object.delete(use_global=True, confirm=False)
            
            for child in coll.children:
                colls.remove(child)
            colls.remove(coll)
            i = items.find(item.name)
            
            
            scene.lensflareitems.remove(i)
    
            
                   
        if scene.lensflareitems_index > - 1:
            scene.lensflareitems_index = len(scene.lensflareitems) - 1
    self.select = False
    self.not_select = False
    self.all = False
        

def copy_prop(self,context):
    
    scene = context.scene
    idx = scene.lensflareitems_index
    
    items = scene.lensflareitems
    active = items[idx]
    act_props = active.light.lensflareprop
    for item in items:
        #print("ok")
        lensflareprop = item.light.lensflareprop
        keys = lensflareprop.keys()
    
        if item != active and item.select and lensflareprop.flared_type==act_props.flared_type:
            
            
            lensflareprop.focal = act_props.focal
            lensflareprop.global_scale = act_props.global_scale
            lensflareprop.glow_scale = act_props.glow_scale
            lensflareprop.streak_scale = act_props.streak_scale
            lensflareprop.sun_beam_rand = act_props.sun_beam_rand
            lensflareprop.sun_beam_scale = act_props.sun_beam_scale
            lensflareprop.sun_beam_number = act_props.sun_beam_number
            lensflareprop.iris_scale = act_props.iris_scale
            lensflareprop.iris_number = act_props.iris_number
            lensflareprop.global_color = act_props.global_color
            lensflareprop.global_color_influence = act_props.global_color_influence
            lensflareprop.dirt_amount = act_props.dirt_amount
            lensflareprop.global_emission = act_props.global_emission
            lensflareprop.glow_emission = act_props.glow_emission
            lensflareprop.streak_emission = act_props.streak_emission
            lensflareprop.sun_beam_emission = act_props.sun_beam_emission
            lensflareprop.iris_emission = act_props.iris_emission
            lensflareprop.obstacle_occlusion = act_props.obstacle_occlusion
            lensflareprop.scale_x = act_props.scale_x
            lensflareprop.scale_y = act_props.scale_y
            
            
            depth = context.evaluated_depsgraph_get()
            depth.update()

                
def update_particle(self, context):
    colls = bpy.data.collections
    coll = colls[self.id]
    suffix = find_suffix(coll)
    obs = coll.all_objects
    lensflareprop = self
    type = lensflareprop.flared_type
    if type == 'A':
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'B':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'C':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'D':
        #print("Not implemend")
        particle.flare_d_particle(obs, context, lensflareprop, suffix)
    if type == 'E':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'G':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'H':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'I':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
        
def update_prop(self, context):
    colls = bpy.data.collections
    coll = colls[self.id]
    suffix = find_suffix(coll)
    obs = coll.all_objects
    lensflareprop = self
    type = lensflareprop.flared_type
    if type == 'A':
        flare_a.flare_a_prop(obs, context, lensflareprop, suffix)
    if type == 'B':
        #print("Not implemend")
        flare_b.flare_b_prop(obs, context, lensflareprop, suffix)
    if type == 'C':
        #print("Not implemend")
        flare_c.flare_c_prop(obs, context, lensflareprop, suffix)
    if type == 'D':
        #print("Not implemend")
        flare_d.flare_d_prop(obs, context, lensflareprop, suffix)
    if type == 'E':
        #print("Not implemend")
        flare_e.flare_e_prop(obs, context, lensflareprop, suffix)
    if type == 'F':
        #print("Not implemend")
        flare_f.flare_f_prop(obs, context, lensflareprop, suffix)
    if type == 'G':
        #print("Not implemend")
        flare_g.flare_g_prop(obs, context, lensflareprop, suffix)
    if type == 'H':
        #print("Not implemend")
        flare_h.flare_h_prop(obs, context, lensflareprop, suffix)
    if type == 'I':
        #print("Not implemend")
        flare_i.flare_i_prop(obs, context, lensflareprop, suffix)
#funzione che pesca la collection dal ID
def find_coll(colls, id):
    for coll in colls:
        if id == coll.lensflareprop.id:
            return coll

#funzioni che pescano gli oggetti dalla collection
def find_suffix(coll):
    suffix = bpy.context.scene.lensflareitems[coll.name].suffix
    
    return suffix

#messaggio di errore in caso di mancata selezione oggetti:

def MessageBox(message = "", title = "ERROR!", icon = 'ERROR'):

    def draw(self, context):
        
        layout = self.layout
        
        row = layout.row()
        row.label(text=message)
        

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

# funzione principale che carica il lensflare in scena
def main(self, context):
    
    scene = context.scene    
     #camera della scena
    cam = scene.lensflarecamera
    #luce della scena
    #light = scene.lensflarelight
    
    for light in context.selected_objects:
        
        if not cam and not light:
            MessageBox("Not Camera and Light Selected")
            return print("not camera selected")
        if not cam:
            MessageBox("Not Camera Selected")
            return print("not camera selected")
        if not light:
            MessageBox("Not Light Selected")
            return print("not light selected")
        
        
        lensflareprop = light.lensflareprop
        if (not light.lensflare):
            light.lensflare = True
            id = "Flared_From_"+light.name
            preview = context.window_manager.flared_previews
            
            flared_type = preview.split(".")[0]
            colls = bpy.data.collections
            
            #path = config_dir = bpy.utils.resource_path('USER')+"/scripts/addons/flaredvfx/flared/"
            path = config_dir = os.path.dirname(__file__)+"/flared/"
            
            
            blendfile = path + "lens_flare_"+flared_type+".blend"
            section   = "\\Collection\\"
            object    = "Flare01"
            
           
            
            filepath  = blendfile + section + object
            directory = blendfile + section
            filename  = object

            bpy.ops.wm.append(
                filepath=filepath, 
                filename=filename,
                directory=directory,
                autoselect=False,
                active_collection=False
                )    
            
            lensflareitems = scene.lensflareitems
            
            
            colls["Flare01"].name = id
            
            coll = colls[id]
            lensflareprop.id = id
            lensflareprop.camera = cam
            lensflareprop.light = light
            lensflareprop.flared_type = flared_type
            type = lensflareprop.flared_type
            
            idx = len(lensflareitems)
            item = lensflareitems.add()
            item.name = id
            item.camera = cam 
            item.light = light
            t,i = ui.lensflare_type(type)
            item.flared_type = t
            
            scene.lensflareitems_index = idx
            obs = coll.all_objects
            item.id = id
            #crea suffisso univoco per il flare aggiunto e aggiungilo
            #a tutti gli oggetti del flare
            suffix = make_suffix(obs)
            for child in coll.children:
                    
                n = child.name
                #print(n)
                if "." in n:
                    split = n.split(".")  
                  
                    child.name = split[0]+suffix
                else:
                    child.name += suffix
            #il suffisso lo salvo nell'ID dell'item
            item.suffix = suffix
            #con il suffisso posso facilmente pescare gli oggetti dalla collection
            
            flared_cam = obs["EmptyCameraOrigin"+suffix]
            
            if not "F" in type:
                iris_particles = obs["IrisParticles"+suffix]
            
            arm = obs["ArmatureCameraCentro"+suffix]
            ctrl = obs["Controller"+suffix]
            
            ctrl.constraints.new('COPY_LOCATION')
            ctrl.constraints[-1].target = light
            
            flared_cam.constraints.new('COPY_LOCATION')
            flared_cam.constraints[-1].target = cam 
            
            flared_cam.constraints.new('COPY_ROTATION')
            flared_cam.constraints[-1].target = cam 
            coll.hide_select = True
            coll.children['Structure'+suffix].hide_viewport = True
            obs["Controller"+suffix].hide_set(True)
            if type!='B' and type!="G":
                obs["Parameters"+suffix].hide_set(True)             
                  
            update_prop(lensflareprop, context)
            
            #operazione da fare per settare valori di default sul tipo B
            
            if type == 'A':
                lensflareprop.focal = 1.0
                lensflareprop.global_scale = 0.0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 1.33
                lensflareprop.sun_beam_rand = 0.888
                lensflareprop.sun_beam_scale = 0.39
                lensflareprop.sun_beam_number = 22
                lensflareprop.iris_scale = 0.47
                lensflareprop.iris_number = 58
                #lensflareprop.global_color = (1.0,1.0,1.0,1.0)
                lensflareprop.global_color_influence = 0.0
                lensflareprop.dirt_amount = 0.26
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.64
                lensflareprop.streak_emission = 0.48
                lensflareprop.sun_beam_emission = 0.78
                lensflareprop.iris_emission = 1.0
                lensflareprop.obstacle_occlusion = 1.0 
                obs["Beam"+suffix].hide_set(True)            
            
            if type == 'B':
                #settaggio del driver sul delta scale del IrisParticles
                #iris_particles.animation_data.drivers[0].driver.variables['var'].targets[0].id = cam
                lensflareprop.focal = 1.0
                lensflareprop.global_scale = 0.0
                lensflareprop.glow_scale = 1.00
                lensflareprop.streak_scale = 1.0
                lensflareprop.sun_beam_rand = 0.888
                lensflareprop.sun_beam_scale = 0.810
                lensflareprop.sun_beam_number = 173
                lensflareprop.iris_scale = 1.30
                lensflareprop.iris_number = 38
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.1
                lensflareprop.global_emission = 0
                lensflareprop.glow_emission = 0.13
                lensflareprop.streak_emission = 0.24
                lensflareprop.sun_beam_emission = 1.32
                lensflareprop.iris_emission = 2.40
                lensflareprop.obstacle_occlusion = 1       
                obs["Beam"+suffix].hide_set(True)
                obs["Iris03"+suffix].hide_set(True)
       		
            if type == 'C':
                lensflareprop.focal = 1
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 0.60
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.19
                lensflareprop.sun_beam_number = 549
                lensflareprop.iris_scale = 0.55
                lensflareprop.iris_number = 200
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.26
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.6
                lensflareprop.streak_emission = 0.6
                lensflareprop.sun_beam_emission = 1.4
                lensflareprop.iris_emission = 1
                lensflareprop.obstacle_occlusion = 1
                obs["Beam"+suffix].hide_set(True)
            
            if type == 'D':
                lensflareprop.focal = 1
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 0
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.57
                lensflareprop.sun_beam_number = 449
                lensflareprop.iris_scale = 1.0
                lensflareprop.iris_number = 0
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.26
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.72
                lensflareprop.streak_emission = 0
                lensflareprop.sun_beam_emission = 1.4
                lensflareprop.iris_emission = 0.80
                lensflareprop.obstacle_occlusion = 1
                obs["Beam"+suffix].hide_set(True)
            
            if type == 'E':
                lensflareprop.focal = 1.21
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 0.60
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.13
                lensflareprop.sun_beam_number = 62
                lensflareprop.iris_scale = 1.0
                lensflareprop.iris_number = 0
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.05
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.6
                lensflareprop.streak_emission = 0.6
                lensflareprop.sun_beam_emission = 1.4
                lensflareprop.iris_emission = 1.0
                lensflareprop.obstacle_occlusion = 1.0
                obs["Beam"+suffix].hide_set(True)
                        
            if type == 'F':
                lensflareprop.focal = 1
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 0
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0
                lensflareprop.sun_beam_number = 0
                lensflareprop.iris_scale = 0
                lensflareprop.iris_number = 0
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.14
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.4
                lensflareprop.streak_emission = 0.9
                lensflareprop.sun_beam_emission = 0.8
                lensflareprop.iris_emission = 0.75
                lensflareprop.obstacle_occlusion = 1
            
            if type == 'G':
                lensflareprop.focal = 1
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 0.46
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.30
                lensflareprop.sun_beam_number = 90
                lensflareprop.iris_scale = 2.47
                lensflareprop.iris_number = 12
                lensflareprop.global_color[0] = 1.0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.10
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.13
                lensflareprop.streak_emission = 0.06
                lensflareprop.sun_beam_emission = 10.00
                lensflareprop.iris_emission = 0.24
                lensflareprop.obstacle_occlusion = 1 
                obs["Beam"+suffix].hide_set(True)
                obs["Iris03"+suffix].hide_set(True)

            if type == 'H':
                lensflareprop.focal = 1.0
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 2.0
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.49
                lensflareprop.sun_beam_number = 53
                lensflareprop.iris_scale = 1.0
                lensflareprop.iris_number = 7
                #lensflareprop.global_color = 0
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.06
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.6
                lensflareprop.streak_emission = 1.0
                lensflareprop.sun_beam_emission = 0.31
                lensflareprop.iris_emission = 1.0
                lensflareprop.obstacle_occlusion = 1.0
                obs["Beam"+suffix].hide_set(True)                
            if type == 'I':
                lensflareprop.focal = 0.9760000705718994
                lensflareprop.global_scale = 0
                lensflareprop.glow_scale = 1.0
                lensflareprop.streak_scale = 1.0199999809265137
                lensflareprop.sun_beam_rand = 1
                lensflareprop.sun_beam_scale = 0.4599999785423279
                lensflareprop.sun_beam_number = 11
                lensflareprop.iris_scale = 0.5289999842643738
                lensflareprop.iris_number = 140
                lensflareprop.global_color = (1.0, 1.0, 1.0, 1.0)
                lensflareprop.global_color_influence = 0
                lensflareprop.dirt_amount = 0.05000000074505806
                lensflareprop.global_emission = 0.0
                lensflareprop.glow_emission = 0.6000000238418579
                lensflareprop.streak_emission = 2.0
                lensflareprop.sun_beam_emission = 1.8600000143051147
                lensflareprop.iris_emission = 0.2200000286102295
                lensflareprop.obstacle_occlusion = 1.0
                obs["Beam"+suffix].hide_set(True)
                    
            subscribe_to_obj_selection(light)
            layer = context.view_layer
            layer.update()
            
        else:
            print("Select Another Source of light")

#funzione per nascondere in automatico il flare (da implementare)
def hide_element(dumm):
    
    
    context = bpy.context
    data = bpy.data
    cam = context.scene.objects['LensFlare_camera']
    em = context.scene.objects['LensFlare_Controller']


    view = context.scene.view_layers['View Layer']
    start = cam.location
    end = em.location - cam.location 
    end.normalize()
    
    coll = data.collections["Flare01"]
    #coll.hide_viewport = False
    for ob in context.scene.objects:
        #print(coll.name)
        #ob = context.scene.objects["Cube"]
        flare = ob.name in coll.all_objects
        print("Flare=")
        #print(flare)
        if not flare:
            coll.hide_viewport=True
            success = context.scene.ray_cast (view, start, end, distance=10.00)
            coll.hide_viewport=False
            #print(success[0])
            if success[0]:
            
                coll.hide_viewport=True


