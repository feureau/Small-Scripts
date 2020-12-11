import bpy

from bpy.types import Panel

from .mecafig import *
from ..ui_templates.armature import *


class MECAFIG_PT_Armature(MECAFIG_PT_MecaFigPanel, Panel):
    '''Armature Panel'''
    bl_label = 'Armature'
    bl_context = 'posemode'
    bl_parent_id = 'MECAFIG_PT_MecaFig'

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        if ob is not None:
            if ob.type == 'ARMATURE':
                if not ob.mecafig.name == '':
                    return True
                else:
                    return None
            else:
                return None

    def draw_header(self, context):
        layout = self.layout
        #layout.label(text='', icon='ARMATURE_DATA')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        ui_template_armature(context, layout)
