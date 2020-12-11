import bpy

from bpy.types import Operator

from ..props_functions.palette import *
from ..ui_templates.palette import *


class MECABRICKS_OT_ColorPalette(Operator):
    '''Mecabricks Color Palette'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MecaFig'
    bl_idname = 'mecabricks.color_palette'
    bl_label = 'Mecabricks Color Palette'

    color_types: EnumProperty(
        name='Type',
        description='Type',
        items=enum_items_mecabricks_color_types,
    )

    colors: EnumProperty(
        name='',
        description='',
        items=enum_items_mecabricks_colors,
        get=get_colors,
        set=set_colors,
    )

    columns: IntProperty(
        default=12,
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        #col = self.columns
        return context.window_manager.invoke_popup(self, width=328)

    def execute(self, context):
        return self.colors

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene

        id = self.colors
        text = get_id_text(id)
        icon = get_icon('ID_%s' % id)

        layout.label(text=text, icon_value=icon)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Mecabricks color palette
        row = layout.row()
        row.label(text='Mecabricks© Color Palette', icon_value=get_icon('mecabricks_logo'))

        # Menu 'Types'
        row = layout.row()
        row.prop(self, 'color_types', text='')
        #row.prop(, 'columns', emboss=False)

        # Colors
        layout = self.layout
        ui_template_palette(context, layout, self.columns, type_settings[self.color_types]['color_sort'], self, 'colors')

        id = self.colors
        text = get_id_text(id)
        icon = get_icon('ID_%s' % id)

        box = layout.box()
        box.label(text=text, icon_value=icon)
