import bpy

from bpy.types import Panel

from .mecafig import *
from ..ui_templates.geometry import *

class MECAFIG_PT_Geometry(MECAFIG_PT_MecaFigPanel, Panel):
    '''Geometry Panel'''
    bl_label = 'Geometry'
    bl_context = ''
    bl_parent_id = 'MECAFIG_PT_MecaFig'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        mf = get_mecafig(context)
        if mf is not None:
            return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout

        ui_template_geometry(context, layout)
