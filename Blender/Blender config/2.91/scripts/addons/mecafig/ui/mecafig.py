import bpy

from bpy.types import Panel

from .utils import *
from ..ui_templates.mecafig import *


class MECAFIG_PT_MecaFig(MECAFIG_PT_MecaFigPanel, Panel):
    '''Main Panel'''
    bl_label = 'MecaFig'
    bl_context = ''

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon_value=get_icon('MINIFIG_ON'))

    def draw(self, context):
        layout = self.layout

        ui_template_mecafig(context, layout)
