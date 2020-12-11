import bpy

from bpy.types import Operator, Menu
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper

from ..properties.shading import *


class MECAFIG_OT_CopySettingsTo(Operator):
    '''Copy Settings To Selected or All objects'''
    bl_idname = 'mecafig.copy_settings_to'
    bl_label = ''

    copy_to: StringProperty(
        default='',
    )

    def execute(self, context):
        copy_settings_to(self, context, self.copy_to)

        return{'FINISHED'}


class MECAFIG_OT_ShadingReset(Operator):
    '''Reset to default values'''
    bl_idname = 'mecafig.shading_reset'
    bl_label = ''

    layer: StringProperty(
        default=''
    )

    def execute(self, context):
        shading_reset(self, context, self.layer)

        return{'FINISHED'}


class MECAFIG_OT_SelectImage(Operator):
    '''Select image'''
    bl_idname = 'mecafig.shading_select_image'
    bl_label = ''
    bl_property = 'images'

    map: StringProperty(
        default=''
    )

    images: EnumProperty(
        items=enum_items_images,
    )

    def execute(self, context):
        image = bpy.data.images[self.images]

        set_map(context, self.map, image)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class MECAFIG_OT_OpenImage(Operator, ImportHelper):
    '''Open image'''
    bl_idname = 'mecafig.shading_open_image'
    bl_label = 'Open Image'

    filename_ext = '.png'

    filter_glob: StringProperty(
        default = '*.png',
        options = {'HIDDEN'},
        maxlen = 255,
    )

    map: StringProperty(
        default=''
    )

    def execute(self, context):
        filepath = self.filepath
        image = bpy.data.images.load(filepath=filepath, check_existing=True)

        set_map(context, self.map, image)

        return {'FINISHED'}


class MECAFIG_OT_UnlinkImage(Operator):
    '''Unlink image'''
    bl_idname = 'mecafig.shading_unlink_image'
    bl_label = 'Unlink Image'

    map: StringProperty(
        default=''
    )

    def execute(self, context):
        ob = context.active_object
        mat = ob.active_material
        nodes = get_nodes(mat)
        # Remove image & Disable texture map
        nodes[self.map].image = None
        nodes[NODE].inputs[self.map].default_value = 0

        return {'FINISHED'}
