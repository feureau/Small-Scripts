import bpy

from bpy.types import Panel

from .utils import *
from ..ui_templates.help import *


class MECAFIG_PT_Help(MECAFIG_PT_MecaFigPanel, Panel):
    '''Help Panel'''
    bl_label = 'Help'
    bl_context = ''
    #bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='QUESTION')

    def draw(self, context):
        layout = self.layout

        ui_template_help(layout)
