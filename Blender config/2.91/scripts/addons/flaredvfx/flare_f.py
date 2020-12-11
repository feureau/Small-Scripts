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


def flare_f_prop(obs, context, lensflareprop, suffix):

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
    
    
    d = gnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
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
    drvs = obs["Glow"+suffix].driver_add("delta_scale")
    
    
    d = drvs[0].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_x"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_x"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_x*glow_scale"
    
    d = drvs[1].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_y"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_y"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_y*glow_scale"
    
    
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
    v2 = d.variables.new()
    v1.name = "global_emission"    
    v2.name = "sun_beam_emission"    
       
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
       
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.sun_beam_emission"    
    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission*10+3)*sun_beam_emission*2"

    #creo il driver, faccio poi un ciclo perché sono in realà 3 valori quindi tre driver
    drvs = obs["GlowLight"+suffix].driver_add("delta_scale")
    d = drvs[0].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_x"
    
    v3 = d.variables.new()
    v3.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_x"
    
    v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_x*obstacle_occlusion"
    
    d = drvs[1].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_y"
    
    v3 = d.variables.new()
    v3.name = "obstacle_occlusion"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_y"
    
    v3.targets[0].data_path = "lensflareprop.obstacle_occlusion"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_y*obstacle_occlusion"
    
    #rotazione:
    drvs = obs["GlowLight"+suffix].driver_add("delta_rotation_euler")
    i = 0
    for ob in drvs:
        d = ob.driver
        #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
        v1 = d.variables.new()
        v1.name = "rot_glow_light"    
        #setto l'oggetto Light che contiene le proprietà della UI
        v1.targets[0].id = light    
        # setto la path che porta alla proprietà dell'UI
        v1.targets[0].data_path = "lensflareprop.rot_glow_light"    
        #estressione matematica da fare con le variabili create
        d.expression = "rot_glow_light["+str(i)+"]"
        i += 1
    
    
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
    v2.name = "iris_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    v2.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    v2.targets[0].data_path = "lensflareprop.iris_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "(global_emission+0.8)*iris_emission"
    
    d = hnt.nodes["Mix Shader.002"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "global_emission"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.global_emission"    
    #estressione matematica da fare con le variabili create
    d.expression = "global_emission+0.8"
    
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
    d.expression = "(global_emission*5+8)*streak_emission"
    
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
    d = drvs[0].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_x"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_x"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_x*glow_scale"
    
    d = drvs[1].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_y"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_y"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_y*glow_scale"

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
    
    d = strnt.nodes["occlusion"].inputs[0].driver_add("default_value").driver    
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    v1.name = "obstacle_occlusion"    
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light    
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.obstacle_occlusion"    
    #estressione matematica da fare con le variabili create
    d.expression = "obstacle_occlusion"
    
    
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
    d.expression = "(global_emission+6.1)*streak_emission"
    
    drvs = obs["Streak"+suffix].driver_add("delta_scale")
    d = drvs[0].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_x"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_x"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_x*glow_scale"
    
    d = drvs[1].driver
    #aggiungo una variabile, per comodità la chiamo come la proprietà da cui è infuenzata
    v1 = d.variables.new()
    
    v1.name = "scale_y"
    
    v3 = d.variables.new()
    v3.name = "glow_scale"
    #setto l'oggetto Light che contiene le proprietà della UI
    v1.targets[0].id = light 
    v2.targets[0].id = light 
    v3.targets[0].id = light
    # setto la path che porta alla proprietà dell'UI
    v1.targets[0].data_path = "lensflareprop.scale_y"
    
    v3.targets[0].data_path = "lensflareprop.glow_scale"
    #estressione matematica da fare con le variabili create
    d.expression = "scale_y*glow_scale"





