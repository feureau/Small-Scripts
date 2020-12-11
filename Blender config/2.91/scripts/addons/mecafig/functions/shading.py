import os
import bpy

from ..properties.shading import *
from ..utils import *

def apply_settings_for(context):
    ob = context.active_object
    parent = ob.parent
    asf = context.scene.mecafig.shading.apply_settings_for

    objects = []
    if asf == 'ACTIVE':
        objects.append(ob)
    elif asf == 'SELECTED':
        for object in context.selected_objects:
            if object in parent.children:
                objects.append(object)
    elif asf == 'ALL':
        for object in parent.children:
            if object.mecafig.geometry.name in MECAFIG:
                objects.append(object)

    return objects

def shading_reset(self, context, layer):
    objects = apply_settings_for(context)
    for ob in objects:
        #ob = context.active_object
        mat = ob.active_material
        nodes = get_nodes(mat)
        inputs = nodes[NODE].inputs
        data = mat.mecafig

        if layer == 'Base':
            base_id = ['1', '2']
            for b_id in base_id:
                base_data = data.base.base_id[b_id]
                color_id = '24'
                if base_data.enable_custom_base:
                    for prop in SHADING['Base']:
                        input = prop.title().replace('_', ' ')
                        if input in inputs.keys():
                            value = SHADING['Base'][prop]
                            value = value if 'color' not in prop else value + [1]
                            inputs[input].default_value = value
                else:
                    base_data.color_id = color_id

        elif layer == 'Maps':
            for map in SHADING['Maps']:
                for prop in SHADING['Maps'][map]:
                    input = '%s %s' %(map, prop.title())
                    if input in inputs.keys():
                        value = SHADING['Maps'][map][prop]
                        inputs[input].default_value = value

        elif layer == 'Wears':
            for wear in SHADING['Wears']:
                for prop in SHADING['Wears'][wear]:
                    input = '%s %s' %(wear, prop.title().replace('_', ' '))
                    if input in inputs.keys():
                        value = SHADING['Wears'][wear][prop]
                        value = value if prop != 'color' else value + [1]
                        inputs[input].default_value = value

    message = 'Values have been reset to default.'
    self.report({'INFO'}, message)

    return{'FINISHED'}

def copy_settings_to(self, context, copy_to):
    ob = context.active_object
    mat = ob.active_material
    data = mat.mecafig

    def copy_base(data, to_data):
        to_data.color = data.color
        to_data.subsurface = data.subsurface
        to_data.subsurface_color = data.subsurface_color
        to_data.metallic = data.metallic
        to_data.specular = data.specular
        to_data.specular_tint = data.specular_tint
        to_data.roughness = data.roughness
        to_data.transmission = data.transmission
        to_data.emission = data.emission
        to_data.emission_color = data.emission_color
        to_data.flatness_scale = data.flatness_scale
        to_data.flatness_strength = data.flatness_strength
        to_data.granulosity_scale = data.granulosity_scale
        to_data.granulosity_strength = data.granulosity_strength
        to_data.glitter_amount = data.glitter_amount
        to_data.glitter_scale = data.glitter_scale
        to_data.paint_intensity = data.paint_intensity
        to_data.paint_color = data.paint_color
        to_data.paint_metallic = data.paint_metallic
        to_data.paint_specular = data.paint_specular
        to_data.paint_specular_tint = data.paint_specular_tint
        to_data.paint_roughness = data.paint_roughness
        to_data.paint_scale = data.paint_scale
        to_data.paint_strength = data.paint_strength

        return {'FINISHED'}

    def copy_maps(map, data, to_data):
        props = SHADING['Maps'][map]
        if 'metallic' in props:
            to_data.metallic = data.metallic
        if 'speculer' in props:
            to_data.specular = data.specular
        if 'roughness' in props:
            to_data.roughness = data.roughness
        if 'strength' in props:
            to_data.strength = data.strength

        return {'FINISHED'}

    def copy_wears(wear, data, to_data):
        props = SHADING['Wears'][wear]
        if 'intensity' in props:
            to_data.intensity = data.intensity
        if 'amount' in props:
            to_data.amount = data.amount
        if 'color' in props:
            to_data.color = data.color
        if 'color_opacity' in props:
            to_data.color_opacity = data.color_opacity
        if 'speculer' in props:
            to_data.specular = data.specular
        if 'roughness' in props:
            to_data.roughness = data.roughness
        if 'strength' in props:
            to_data.strength = data.strength
        if 'seed' in props:
            to_data.seed = data.seed

        return {'FINISHED'}

    objects = []
    if copy_to == 'SELECTED':
        sel_ob = context.selected_objects
        if len(sel_ob) <= 1:
            message = 'No object on to copy settings is selected!'
            self.report({'WARNING'}, message)
            return{'FINISHED'}
        else:
            for object in sel_ob:
                if not object == ob:
                    try:
                        if object.active_material.mecafig.name == data.name:
                            objects.append(object)
                    except:
                        continue
    elif copy_to == 'ALL':
        for object in bpy.data.objects:
            if not object == ob:
                try:
                    if object.active_material.mecafig.name == data.name:
                        objects.append(object)
                except:
                    continue

    for object in objects:
        to_mat = object.active_material
        to_data = to_mat.mecafig

        context.view_layer.objects.active = object

        # Base
        to_data.base.enable_dual_base = data.base.enable_dual_base
        for b_id in ['1', '2']:
            b_data = data.base.base_id[b_id]
            to_b_data = to_data.base.base_id[b_id]
            if b_data.enable_custom_base:
                to_b_data.enable_custom_base = True
                copy_base(b_data, to_b_data)
            else:
                b_data.enable_custom_base = False
                to_b_data.color_id = b_data.color_id
        to_data.base.use_normal_map = data.base.use_normal_map

        # Maps
        to_data.maps.enable = data.maps.enable
        for map in SHADING['Maps']:
            copy_maps(map, data.maps.maps[map], to_data.maps.maps[map])

        # Wears
        to_data.wears.enable = data.wears.enable
        for wear in SHADING['Wears']:
            copy_wears(wear, data.wears.wears[wear], to_data.wears.wears[wear])

    context.view_layer.objects.active = ob
    self.report({'INFO'}, 'Settings copied to objects.')

    return {'FINISHED'}

def get_id_text(id):
    mc = mecabricks_colors
    tp = type_settings
    cn = colors_name

    type = tp[mc[id]['type']]

    type_name = (('%s ' % type['name']) if not type == 'solid' else '')
    text = '%s%s (ID: %s)' %(type_name, cn[id], id)

    return text

def set_base_from_color_id(data, color_id):
    mc = mecabricks_colors
    ts = type_settings
    type = mc[color_id]['type']
    prop = ts[type]

    if type in ['chrome', 'metal', 'speckle']:
        # Set Paint
        data.paint_color = mc[color_id]['sRGB'] + [1]
        data.paint_metallic = prop['metallic']
        data.paint_specular = prop['specular']
        data.paint_specular_tint = prop['specular_tint']
        data.paint_roughness = prop['roughness']
        data.paint_scale = prop['scale']
        data.paint_strength = prop['strength']
        if type == 'speckle':
            data.paint_intensity = mc[color_id]['paint']
            if color_id == '2006':
                color_id = '199' # Dark Stone Grey
            else:
                color_id = '26' # Black
        else:
            data.paint_intensity = 1
            color_id = '20' # Milky Nature
    else:
        data.paint_intensity = 0

    # Set new type
    type = mc[color_id]['type']
    prop = ts[type]
    # Set Base
    data.color = mc[color_id]['sRGB'] + [1]
    data.subsurface = prop['subsurface']
    data.subsurface_color = mc[color_id]['sRGB'] + [1]
    data.metallic = prop['metallic']
    data.specular = prop['specular']
    data.specular_tint = prop['specular_tint']
    data.roughness = prop['roughness']
    data.transmission = prop['transmission']
    data.emission = 0
    if 'emission' in mc[color_id].keys():
        data.emission_color = mc[color_id]['emission'] + [1]
    else:
        data.emission_color = [0, 0, 0, 1]
    data.flatness_scale = prop['flatness'][0]
    data.flatness_strength = prop['flatness'][1]
    data.granulosity_scale = prop['granulosity'][0]
    data.granulosity_strength = prop['granulosity'][1]
    if 'glitter' in mc[color_id].keys():
        data.glitter_amount = mc[color_id]['glitter'][0]
        data.glitter_scale = mc[color_id]['glitter'][1]
    else:
        data.glitter_amount = 0

    return {'FINISHED'}

def get_nodes(material):
    return material.node_tree.nodes

def get_value(self, input):
    nodes = get_nodes(self.id_data)
    node = NODE
    if node in nodes.keys():
        if input in nodes[node].inputs.keys():
            return nodes[node].inputs[input].default_value

def set_value(self, input, value):
    objects = apply_settings_for(bpy.context)
    for ob in objects:
        nodes = get_nodes(ob.active_material)
        node = NODE
        if node in nodes.keys():
            if input in nodes[node].inputs.keys():
                nodes[node].inputs[input].default_value = value

def get_pixel_color(image, pixel):
    pixel_color = []
    pixel = pixel * 4
    for i in range(pixel + 0, pixel + 4):
        pixel_color.append(image.pixels[i])

    return pixel_color

def set_map(context, map, image):
    ob = context.active_object
    mat = ob.active_material
    nodes = get_nodes(mat)
    # Set Decoration Base Color
    if map == 'Decoration':
        input = 'Decoration Base Color'
        color = get_pixel_color(image, 0)
        nodes[NODE].inputs[input].default_value = color

    nodes[map].image = image
    nodes[NODE].inputs[map].default_value = 1

    return {'FINISHED'}

def get_image(image_name, directory):
    image = None

    if image_name in bpy.data.images.keys():
        image = bpy.data.images[image_name]
    elif image_name in os.listdir(directory):
        filepath = directory + '/' + image_name
        image = bpy.data.images.load(filepath=filepath)

    return image

def set_image(material, node_name, image, colorspace, use):
    nodes = get_nodes(material)

    if image is not None:
        # Set Image
        image.colorspace_settings.name = colorspace
        nodes[node_name].image = image
        # Set Base Color
        if node_name == 'Decoration':
            color_input = 'Decoration Base Color'
            alpha_input = 'Decoration Base Alpha'
            color = get_pixel_color(image, 0)
            nodes[NODE].inputs[color_input].default_value = color
            nodes[NODE].inputs[alpha_input].default_value = color[3]
        # Use Image
        if use:
            nodes[NODE].inputs[node_name].default_value = 1
        else:
            nodes[NODE].inputs[node_name].default_value = 0

    return {'FINISHED'}

def set_image_texture(material, node, directory, image, image_settings):
    nodes = material.node_tree.nodes
    map = None
    if image in bpy.data.images.keys():
        map = bpy.data.images[image]
    elif image in os.listdir(directory):
        filepath = directory + '/' + image
        map = bpy.data.images.load(filepath=filepath)

    if node == 'Decoration':
        color_input = 'Decoration Base Color'
        alpha_input = 'Decoration Base Alpha'
        color = get_pixel_color(image, 0)
        nodes[NODE].inputs[color_input].default_value = color
        nodes[NODE].inputs[alpha_input].default_value = color[3]

    if map is not None:
        map.colorspace_settings.name = image_settings
        nodes[node].image = map
        nodes[NODE].inputs[node].default_value = 1

    return {'FINISHED'}

def set_shading(material, settings, filepath):
    data = material.mecafig
    maps_dir = os.path.dirname(filepath) + '/maps/'
    uv_map = settings[0]
    mat = settings[2]
    conf = settings[3]

    # Color ID
    color_id = mat[0]
    if not color_id == []:
        data.base.base_id[0].color_id = str(color_id[0])
        if len(color_id) > 1:
            data.base.enable_dual_base = True
            data.base.base_id[1].color_id = str(color_id[1])

    # MAPS
    if not uv_map == '':

		# Workflow
        if conf == 1:
            wf = 'DEC_MET'
        elif conf == 2:
            wf = 'COL_DAT'
        data.maps.workflow = wf

        # UV Map
        for elem in ['uv', 'UV']:
            if elem in uv_map:
                data.maps.uv_map = uv_map

        # Decoration / Color Map
        if not mat[1] == '':
            c_dir = ''
            for dir in os.listdir(maps_dir):
                if conf == 1:
                    if dir == 'decoration':
                        c_dir = maps_dir + 'decoration/'
                    elif dir == 'diffuse':
                        c_dir = maps_dir + 'diffuse/'
                elif conf == 2:
                    c_dir = maps_dir + 'color/'

            c_img = get_image('%s.png' % mat[1], c_dir)
            set_image(material, 'Decoration', c_img, 'sRGB', True)

            # Enable Maps
            data.maps.enable = True

        # Metalness / Data Map
        if not mat[2] == '':
            if conf == 1:
                d_dir = maps_dir + 'metalness/'
            elif conf == 2:
                d_dir = maps_dir + 'data/'

            d_img = get_image('%s.png' % mat[2], d_dir)
            set_image(material, 'Metalness', d_img, 'Non-Color', True)

    return {'FINISHED'}
