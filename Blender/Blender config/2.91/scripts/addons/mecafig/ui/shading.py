import bpy

from bpy.types import Panel

from .mecafig import *
from ..ui_templates.shading import *


class MECAFIG_PT_Shading(MECAFIG_PT_MecaFigPanel, Panel):
    '''Shading Panel'''
    bl_label = 'Shading'
    bl_context = ''
    bl_parent_id = 'MECAFIG_PT_MecaFig'

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        if ob is not None:
            mat = ob.active_material
            if mat and not mat.mecafig.name == '':
                return True

    def draw_header(self, context):
        layout = self.layout
        #layout.label(icon='MATERIAL')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        scene_data = scene.mecafig.shading

        ui_template_shading(context, layout, scene_data)
