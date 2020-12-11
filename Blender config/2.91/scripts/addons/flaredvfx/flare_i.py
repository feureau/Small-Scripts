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


def flare_i_prop(obs, context, lensflareprop, suffix):

    light = lensflareprop.light
    

##### FOCAL LENGTH #####    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["ArmatureCamera"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v = d.variables.new()
        v.name = "focal"
        #setto l'oggetto Light che contiene le proprietà della UI
        v.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v.targets[0].data_path = "lensflareprop.focal"
        #estressione matematica da fare con le variabili create
        d.expression = "focal"
          
##### DIRTY #### 
    d = obs["DirtAddB"+suffix].material_slots[0].material.node_tree.nodes['Emission'].inputs['Strength'].driver_add("default_value").driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "dirt_amount"
    v2 = d.variables.new()
    v2.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.dirt_amount"
    v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "(dirt_amount*3)*obstacle_occlusion"
    
    d = obs["DirtAddG"+suffix].material_slots[0].material.node_tree.nodes['Emission'].inputs['Strength'].driver_add("default_value").driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "dirt_amount"
    v2 = d.variables.new()
    v2.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.dirt_amount"
    v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "(dirt_amount*3)*obstacle_occlusion"
            
    d = obs["DirtAddR"+suffix].material_slots[0].material.node_tree.nodes['Emission'].inputs['Strength'].driver_add("default_value").driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "dirt_amount"
    v2 = d.variables.new()
    v2.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.dirt_amount"
    v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "(dirt_amount*3)*obstacle_occlusion"
    
    d = obs["DirtMulty"+suffix].material_slots[0].material.node_tree.nodes['Mix Shader.003'].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "dirt_amount"
    v2 = d.variables.new()
    v2.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.dirt_amount"
    v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "dirt_amount*obstacle_occlusion"

##### BEAM #####
    beam = obs["Beam"+suffix].material_slots[0].material.node_tree
        
    drvs = beam.nodes['ColorRamp.003'].color_ramp.elements[0].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
        
    d = beam.nodes['Mix'].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    
    d = beam.nodes['Emission'].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"
    v2 = d.variables.new()
    v2.name = "sun_beam_emission"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"
    v2.targets[0].data_path = "lensflareprop.sun_beam_emission"
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission)+sun_beam_emission"
    
    
    d = obs["Beam"+suffix].driver_add("delta_scale",2).driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_scale"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_scale"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_scale+1"

###### BEAM PARTICLE #####  
    bps = obs["BeamsParticle"+suffix].particle_systems[0].settings
#      
    d = bps.driver_add("size_random").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "sun_beam_rand"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.sun_beam_rand"    
    #estressione matematica da fare con le variabili create
    d.expression = "sun_beam_rand"
#    
    d = bps.driver_add("particle_size").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_scale"
    v2 = d.variables.new()
    v2.name = "sun_beam_scale"
    v3 = d.variables.new()
    v3.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_scale"
    v2.targets[0].data_path = "lensflareprop.sun_beam_scale"
    v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "(global_scale+sun_beam_scale)*obstacle_occlusion"
    
##### GLOW #####        
    gnt = obs["Glow"+suffix].material_slots[0].material.node_tree
    drvs = gnt.nodes['RGB.001'].outputs[0].driver_add("default_value")  
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = gnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = gnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "glow_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.glow_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_emission+glow_emission"

    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Glow"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"
        v2 = d.variables.new()
        v2.name = "glow_scale"
        v3 = d.variables.new()
        v3.name = "obstacle_occlusion"
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        v3.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.glow_scale"
        v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
        #estressione matematica da fare con le variabili create
        d.expression = "(global_scale+glow_scale)*obstacle_occlusion"

##### GLOW LIGHT #####
    gnt = obs["GlowLight"+suffix].material_slots[0].material.node_tree
    drvs = gnt.nodes['RGB.001'].outputs[0].driver_add("default_value")  
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = gnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = gnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
       
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
       
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    
    #estressione matematica da fare con le variabili create
    d.expression = "global_emission+1.5"

    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["GlowLight"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"
        v2 = d.variables.new()
        v2.name = "glow_scale"
        v3 = d.variables.new()
        v3.name = "obstacle_occlusion"
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        v3.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.glow_scale"
        v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
        #estressione matematica da fare con le variabili create
        d.expression = "(global_scale+glow_scale)*obstacle_occlusion"
                 
##### HOOP #####    
    hnt = obs["Hoop"+suffix].material_slots[0].material.node_tree
    
    drvs = hnt.nodes['ColorRamp.002'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    
    d = hnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = hnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = hnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "sun_beam_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.sun_beam_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.8)*sun_beam_emission"
    
    d = hnt.nodes["Mix Shader.002"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_emission*5+0.8"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Hoop"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "(global_scale/4)+1"   

##### IRIS 01#####    
    irnt = obs["Iris01"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.25)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris01"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"   

##### IRIS 02 #####
    irnt = obs["Iris02"+suffix].material_slots[0].material.node_tree
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1

    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.3)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris02"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"
                
##### IRIS 03 #####            
    irnt = obs["Iris03"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.4)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris03"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"    
        
##### IRIS 04 #####            
    irnt = obs["Iris04"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+1)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris04"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"

##### IRIS 05 #####
    irnt = obs["Iris05"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.7)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris05"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"           

##### IRIS 06 #####  
    irnt = obs["Iris06"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+1.5)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris06"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"          

##### IRIS 07 #####
    for slot in obs["Iris07"+suffix].material_slots:
        mat = slot.material
        irnt = slot.material.node_tree
    
    
        drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
        i = 0
        for ob in drvs:
            d = ob.driver
            #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
            v1 = d.variables.new()
            v1.name = "global_color"    
            #setto l'oggetto Light che contiene le proprietà della UI
            v1.targets[0].id = light    
            # setto la path che porta alla proprietà dell'UI
            v1.targets[0].data_path = "lensflareprop.global_color"    
            #estressione matematica da fare con le variabili create
            d.expression = "global_color["+str(i)+"]"
            i += 1
        
        d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color_influence"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color_influence"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color_influence"
            
        d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "obstacle_occlusion"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
        #estressione matematica da fare con le variabili create
        d.expression = "obstacle_occlusion"
        
        d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_emission"    
        v2 = d.variables.new()
        v2.name = "iris_emission"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        v2.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_emission"    
        v2.targets[0].data_path = "lensflareprop.iris_emission"    
        #estressione matematica da fare con le variabili create
        if "b" in mat.name:
            d.expression = "((global_emission/8)+0.75)*iris_emission"
        else:    
            d.expression = "((global_emission/8)+0.75)*iris_emission"
        
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris07"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"          

##### IRIS 08 ##### 
    irnt = obs["Iris08"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.7)*iris_emission"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris08"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"            

##### IRIS 09 #####
    irnt = obs["Iris09"+suffix].material_slots[0].material.node_tree
    
    drvs = irnt.nodes['ColorRamp.001'].color_ramp.elements[1].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = irnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
        
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v2 = d.variables.new()
    v1.name = "global_scale"        
    v2.name = "iris_scale"        
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light
    v2.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_scale"
    v2.targets[0].data_path = "lensflareprop.iris_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "global_scale+iris_scale" 
    
    d = irnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.5)*iris_emission"
    
    d = irnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["Iris09"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v2 = d.variables.new()
        v1.name = "global_scale"        
        v2.name = "iris_scale"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.iris_scale"
        #estressione matematica da fare con le variabili create
        d.expression = "global_scale+iris_scale"            

###### IRIS PARTICLES ####    
    irps = obs["IrisParticles"+suffix].particle_systems[0].settings
#   
#    d = irps.driver_add("count").driver    
#    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
#    v1 = d.variables.new()
#    v1.name = "iris_number"    
#    #setto l'oggetto Light che contiene le proprietà della UI
#    v1.targets[0].id = light    
#    # setto la path che porta alla proprietà dell'UI
#    v1.targets[0].data_path = "lensflareprop.iris_number"    
#    #estressione matematica da fare con le variabili create
#    d.expression = "iris_number"
#    
    d = irps.driver_add("particle_size").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_scale"    
    v2 = d.variables.new()
    v2.name = "iris_scale"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_scale"    
    v2.targets[0].data_path = "lensflareprop.iris_scale"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_scale+iris_scale"
         

##### REFLECT GLOW #####
    rgnt = obs["ReflectGlow"+suffix].material_slots[0].material.node_tree
    drvs = rgnt.nodes['RGB.001'].outputs[0].driver_add("default_value")  
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = rgnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = rgnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = rgnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "glow_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.glow_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+6)*glow_emission"
    
    d = rgnt.nodes["Mix Shader.002"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    drvs = obs["ReflectGlow"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"        
        v2 = d.variables.new()
        v2.name = "obstacle_occlusion"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
        #estressione matematica da fare con le variabili create
        d.expression = "((1+global_scale*10)*obstacle_occlusion)"            

##### REFLECT STREAk #####        
    rsnt = obs["ReflectStreak"+suffix].material_slots[0].material.node_tree
    
    
    drvs = rsnt.nodes['ColorRamp.001'].color_ramp.elements[0].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = rsnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = rsnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    d = rsnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "streak_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.streak_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+8)*streak_emission"
    
    d = rsnt.nodes["Mix Shader.003"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"       
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light        
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    drvs = obs["ReflectStreak"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"        
        v2 = d.variables.new()
        v2.name = "obstacle_occlusion"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.obstacle_occlusion"
        #estressione matematica da fare con le variabili create
        d.expression = "((1+global_scale*10)*obstacle_occlusion)"

##### STREAK #####
    strnt = obs["Streak"+suffix].material_slots[0].material.node_tree

    drvs = strnt.nodes['ColorRamp.001'].color_ramp.elements[0].driver_add("color")   
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_color"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_color"    
        #estressione matematica da fare con le variabili create
        d.expression = "global_color["+str(i)+"]"
        i += 1
    
    d = strnt.nodes["Mix"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_color_influence"       
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light        
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_color_influence"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_color_influence"
    
    d = strnt.nodes["Emission"].inputs[1].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    v2 = d.variables.new()
    v2.name = "streak_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.streak_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission) + streak_emission*10"
    
    drvs = obs["Streak"+suffix].driver_add("delta_scale")
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "global_scale"        
        v2 = d.variables.new()
        v2.name = "streak_scale"        
        v3 = d.variables.new()
        v3.name = "obstacle_occlusion"        
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light
        v2.targets[0].id = light
        v3.targets[0].id = light
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.global_scale"
        v2.targets[0].data_path = "lensflareprop.streak_scale"
        v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
        #estressione matematica da fare con le variabili create
        d.expression = "((global_scale+streak_scale))*obstacle_occlusion"






