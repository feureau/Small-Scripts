import bpy

from ..functions.shading import *
from ..icons.__init__ import *
from ..utils import *

def enum_items_mecabricks_colors(self, context):
    enum_items = []
    for id in mecabricks_colors:
        identifier = id
        name = ''
        description = get_id_text(id)
        icon = get_icon('ID_%s' % id)
        number = int(id)

        enum_items.append((identifier, name, description, icon, number))

    return enum_items

def enum_items_mecabricks_color_types(self, context):
    ts = type_settings
    enum_items = []

    for id in ts:
        enum_items.append((id, id.title(), ''))

    return enum_items

def get_colors(self):
    data = bpy.context.active_object.active_material.mecafig.base
    base_id = data.select_base
    return int(data.base_id[base_id].color_id)

def set_colors(self, value):
    objects = apply_settings_for(bpy.context)
    base_id = bpy.context.active_object.active_material.mecafig.base.select_base
    for ob in objects:
        data = ob.active_material.mecafig.base
        data.base_id[base_id].color_id = str(value)
