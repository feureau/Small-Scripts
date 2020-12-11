import bpy
import math

from ..functions.shading import *

def update_show_panel(self, context):
    elem = self.name

    if elem == 'Base':
        base_data = self.base_id
        for id in ['1', '2']:
            if id not in base_data.keys():
                new_base_data = base_data.add()
                new_base_data.name = id
    elif elem == 'Maps':
        maps_data = self.maps
        for map in SHADING['Maps']:
            if map not in maps_data.keys():
                map_data = maps_data.add()
                map_data.name = map
    elif elem == 'Wears':
        wears_data = self.wears
        for wear in SHADING['Wears']:
            if wear not in wears_data.keys():
                wear_data = wears_data.add()
                wear_data.name = wear

# ------------
# ### Base ###
# ------------

def get_dual_base(self):
    nodes = get_nodes(self.id_data)
    value = nodes[NODE].inputs['Base'].default_value
    return (True if value == 1 else False)

def set_dual_base(self, value):
    objects = apply_settings_for(bpy.context)
    for ob in objects:
        part = ob.mecafig.geometry.name
        nodes = get_nodes(ob.active_material)
        if part in ['Leg.L', 'Leg.R', 'Arm.L', 'Arm.R']:
            val = (1 if value else 0)
        else:
            val = 0
        nodes[NODE].inputs['Base'].default_value = val

def update_color_id(self, context):
    if not self.enable_custom_base:
        set_base_from_color_id(self, self.color_id)

def update_enable_custom_base(self, context):
    objects = apply_settings_for(context)
    for ob in objects:
        ob_data = ob.active_material.mecafig.base.base_id[self.name]
        if not ob_data.enable_custom_base == self.enable_custom_base:
            ob_data.enable_custom_base = self.enable_custom_base
        if not self.enable_custom_base:
            set_base_from_color_id(self, self.color_id)

def get_color(self):
    input = 'Color %s' % self.name
    return get_value(self, input)

def set_color(self, value):
    input = 'Color %s' % self.name
    set_value(self, input, value)
    self.id_data.diffuse_color = value

def get_subsurface(self):
    input = 'Subsurface %s' % self.name
    return get_value(self, input)

def set_subsurface(self, value):
    input = 'Subsurface %s' % self.name
    set_value(self, input, value)

def get_subsurface_color(self):
    input = 'Subsurface Color %s' % self.name
    return get_value(self, input)

def set_subsurface_color(self, value):
    input = 'Subsurface Color %s' % self.name
    set_value(self, input, value)

def get_metallic(self):
    input = 'Metallic %s' % self.name
    return get_value(self, input)

def set_metallic(self, value):
    input = 'Metallic %s' % self.name
    set_value(self, input, value)
    self.id_data.metallic = value

def get_specular(self):
    input = 'Specular %s' % self.name
    return get_value(self, input)

def set_specular(self, value):
    input = 'Specular %s' % self.name
    set_value(self, input, value)

def get_specular_tint(self):
    input = 'Specular Tint %s' % self.name
    return get_value(self, input)

def set_specular_tint(self, value):
    input = 'Specular Tint %s' % self.name
    set_value(self, input, value)

def get_roughness(self):
    input = 'Roughness %s' % self.name
    return get_value(self, input)

def set_roughness(self, value):
    input = 'Roughness %s' % self.name
    set_value(self, input, value)
    self.id_data.roughness = value

def update_transmission(self, context):
    value = (False if self.transmission == 0 else True)
    context.active_object.active_material.use_screen_refraction = value

def get_transmission(self):
    input = 'Transmission %s' % self.name
    return get_value(self, input)

def set_transmission(self, value):
    input = 'Transmission %s' % self.name
    set_value(self, input, value)

def get_emission(self):
    input = 'Emission %s' % self.name
    return get_value(self, input)

def set_emission(self, value):
    input = 'Emission %s' % self.name
    set_value(self, input, value)

def get_emission_color(self):
    input = 'Emission Color %s' % self.name
    return get_value(self, input)

def set_emission_color(self, value):
    input = 'Emission Color %s' % self.name
    set_value(self, input, value)

def get_flatness_scale(self):
    input = 'Flatness Scale %s' % self.name
    return get_value(self, input)

def set_flatness_scale(self, value):
    input = 'Flatness Scale %s' % self.name
    set_value(self, input, value)

def get_flatness_strength(self):
    input = 'Flatness Strength %s' % self.name
    return get_value(self, input)

def set_flatness_strength(self, value):
    input = 'Flatness Strength %s' % self.name
    set_value(self, input, value)

def get_granulosity_scale(self):
    input = 'Granulosity Scale %s' % self.name
    return get_value(self, input)

def set_granulosity_scale(self, value):
    input = 'Granulosity Scale %s' % self.name
    set_value(self, input, value)

def get_granulosity_strength(self):
    input = 'Granulosity Strength %s' % self.name
    return get_value(self, input)

def set_granulosity_strength(self, value):
    input = 'Granulosity Strength %s' % self.name
    set_value(self, input, value)

def get_glitter_amount(self):
    input = 'Glitter Amount %s' % self.name
    return get_value(self, input)

def set_glitter_amount(self, value):
    input = 'Glitter Amount %s' % self.name
    set_value(self, input, value)

def get_glitter_scale(self):
    input = 'Glitter Scale %s' % self.name
    return get_value(self, input)

def set_glitter_scale(self, value):
    input = 'Glitter Scale %s' % self.name
    set_value(self, input, value)

def get_paint_intensity(self):
    input = 'Paint Intensity %s' % self.name
    return get_value(self, input)

def set_paint_intensity(self, value):
    input = 'Paint Intensity %s' % self.name
    set_value(self, input, value)

def get_paint_color(self):
    input = 'Paint Color %s' % self.name
    return get_value(self, input)

def set_paint_color(self, value):
    input = 'Paint Color %s' % self.name
    set_value(self, input, value)

def get_paint_metallic(self):
    input = 'Paint Metallic %s' % self.name
    return get_value(self, input)

def set_paint_metallic(self, value):
    input = 'Paint Metallic %s' % self.name
    set_value(self, input, value)

def get_paint_specular(self):
    input = 'Paint Specular %s' % self.name
    return get_value(self, input)

def set_paint_specular(self, value):
    input = 'Paint Specular %s' % self.name
    set_value(self, input, value)

def get_paint_specular_tint(self):
    input = 'Paint Specular Tint %s' % self.name
    return get_value(self, input)

def set_paint_specular_tint(self, value):
    input = 'Paint Specular Tint %s' % self.name
    set_value(self, input, value)

def get_paint_roughness(self):
    input = 'Paint Roughness %s' % self.name
    return get_value(self, input)

def set_paint_roughness(self, value):
    input = 'Paint Roughness %s' % self.name
    set_value(self, input, value)

def get_paint_scale(self):
    input = 'Paint Scale %s' % self.name
    return get_value(self, input)

def set_paint_scale(self, value):
    input = 'Paint Scale %s' % self.name
    set_value(self, input, value)

def get_paint_strength(self):
    input = 'Paint Strength %s' % self.name
    return get_value(self, input)

def set_paint_strength(self, value):
    input = 'Paint Strength %s' % self.name
    set_value(self, input, value)

def get_use_normal_map(self):
    nodes = get_nodes(self.id_data)
    value = nodes[NODE].inputs['Normal'].default_value
    return (True if value == 1 else False)

def set_use_normal_map(self, value):
    objects = apply_settings_for(bpy.context)
    for ob in objects:
        nodes = get_nodes(ob.active_material)
        value = (1 if value else 0)
        nodes[NODE].inputs['Normal'].default_value = value

# -------------------
# ### Maps ###
# -------------------

def get_enable_maps(self):
    nodes = get_nodes(self.id_data)
    value = nodes[NODE].inputs[self.name].default_value
    return (True if value == 1 else False)

def set_enable_maps(self, value):
    objects = apply_settings_for(bpy.context)
    for ob in objects:
        nodes = get_nodes(ob.active_material)
        value = (1 if value else 0)
        nodes[NODE].inputs[self.name].default_value = value

def get_workflow(self):
    nodes = get_nodes(self.id_data)
    value = nodes[NODE].inputs['Workflow'].default_value
    return (0 if value < 1 else 1)

def set_workflow(self, value):
    nodes = get_nodes(self.id_data)
    value = (1 if value else 0)
    nodes[NODE].inputs['Workflow'].default_value = value

def enum_items_maps_uv_map(self, context):
    ob = context.active_object
    name = ob.mecafig.geometry.name
    enum_items = []
    for part in MECAFIG:
        if part == name:
            uv_maps = MECAFIG[part]['uv_maps']
            for i, uv_map in enumerate(uv_maps):
                enum_items.append((uv_map, uv_map, '', i))

    return enum_items

def update_maps_uv_map(self, context):
    nodes = get_nodes(self.id_data)
    nodes['UV Maps'].uv_map = self.uv_map

def enum_items_images(self, context):
    images = bpy.data.images
    enum_items = []

    for i, image in enumerate(images):
        id = image.name
        name = '%s %s' %('F' if image.use_fake_user else ' ', image.name)
        description = ''
        icon = image.preview.icon_id
        number = i
        item = (id, name, description, icon, number)

        enum_items.append(item)

    return enum_items

def get_maps_metallic(self):
    input = '%s Metallic' % self.name
    return get_value(self, input)

def set_maps_metallic(self, value):
    input = '%s Metallic' % self.name
    set_value(self, input, value)

def get_maps_specular(self):
    input = '%s Specular' % self.name
    return get_value(self, input)

def set_maps_specular(self, value):
    input = '%s Specular' % self.name
    set_value(self, input, value)

def get_maps_roughness(self):
    input = '%s Roughness' % self.name
    return get_value(self, input)

def set_maps_roughness(self, value):
    input = '%s Roughness' % self.name
    set_value(self, input, value)

def get_maps_strength(self):
    input = '%s Strength' % self.name
    return get_value(self, input)

def set_maps_strength(self, value):
    input = '%s Strength' % self.name
    set_value(self, input, value)

# -------------
# ### Wears ###
# -------------

def get_enable_wears(self):
    nodes = get_nodes(self.id_data)
    value = nodes[NODE].inputs[self.name].default_value
    return (True if value == 1 else False)

def set_enable_wears(self, value):
    objects = apply_settings_for(bpy.context)
    for ob in objects:
        nodes = get_nodes(ob.active_material)
        value = (1 if value else 0)
        nodes[NODE].inputs[self.name].default_value = value

def get_wears_intensity(self):
    input = '%s Intensity' %self.name
    return get_value(self, input)

def set_wears_intensity(self, value):
    input = '%s Intensity' %self.name
    set_value(self, input, value)

def get_wears_amount(self):
    input = '%s Amount' %self.name
    return get_value(self, input)

def set_wears_amount(self, value):
    input = '%s Amount' %self.name
    set_value(self, input, value)

def get_wears_color(self):
    input = '%s Color' %self.name
    return get_value(self, input)

def set_wears_color(self, value):
    input = '%s Color' %self.name
    set_value(self, input, value)

def get_wears_color_opacity(self):
    input = '%s Color Opacity' %self.name
    return get_value(self, input)

def set_wears_color_opacity(self, value):
    input = '%s Color Opacity' %self.name
    set_value(self, input, value)

def get_wears_specular(self):
    input = '%s Specular' %self.name
    return get_value(self, input)

def set_wears_specular(self, value):
    input = '%s Specular' %self.name
    set_value(self, input, value)

def get_wears_roughness(self):
    input = '%s Roughness' %self.name
    return get_value(self, input)

def set_wears_roughness(self, value):
    input = '%s Roughness' %self.name
    set_value(self, input, value)

def get_wears_strength(self):
    input = '%s Strength' %self.name
    return get_value(self, input)

def set_wears_strength(self, value):
    input = '%s Strength' %self.name
    set_value(self, input, value)

def get_wears_seed(self):
    input = '%s Seed' %self.name
    return get_value(self, input)

def set_wears_seed(self, value):
    input = '%s Seed' %self.name
    set_value(self, input, value)
