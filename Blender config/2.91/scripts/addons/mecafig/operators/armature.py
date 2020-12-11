from bpy.types import Operator
from bpy.props import StringProperty

from ..properties.armature import *


class MECAFIG_OT_ClearBones(Operator):
    '''Clear bones position'''
    bl_idname = 'mecafig.clear_bones'
    bl_label = 'Clear Bones'

    part: StringProperty(
        default=''
    )

    def execute(self, context):
        ob = self.part
        clear_bones(context, ob)

        return{'FINISHED'}


class MECAFIG_OT_ClearAllBones(Operator):
    '''Clear all bones position'''
    bl_idname = 'mecafig.clear_all_bones'
    bl_label = 'Clear All Bones'

    def execute(self, context):
        clear_all_bones(context)

        return{'FINISHED'}


class MECAFIG_OT_FKMode(Operator):
    '''FK Mode'''
    bl_idname = 'mecafig.fk_mode'
    bl_label = 'FK'

    part: StringProperty(
        default=''
    )

    def execute(self, context):
        fk_mode(context, self.part)

        return{'FINISHED'}


class MECAFIG_OT_IKMode(Operator):
    '''IK Mode'''
    bl_idname = 'mecafig.ik_mode'
    bl_label = 'IK'

    part: StringProperty(
        default=''
    )

    def execute(self, context):
        ik_mode(context, self.part)

        return{'FINISHED'}


class MECAFIG_OT_RigidMode(Operator):
    '''Rigid Mode'''
    bl_idname = 'mecafig.rigid_mode'
    bl_label = 'Rigid'

    part: StringProperty(
        default=''
    )

    def execute(self, context):
        ob = self.part
        rigid_mode(context, ob)

        return{'FINISHED'}


class MECAFIG_OT_SoftMode(Operator):
    '''Soft Mode'''
    bl_idname = 'mecafig.soft_mode'
    bl_label = 'Soft'

    part: StringProperty(
        default=''
    )

    def execute(self, context):
        ob = self.part
        soft_mode(context, ob)

        return{'FINISHED'}


class MECAFIG_OT_RigidModeAll(Operator):
    '''Rigid Mode All'''
    bl_idname = 'mecafig.rigid_mode_all'
    bl_label = 'All Rigid'

    def execute(self, context):
        rigid_mode_all(context)

        return{'FINISHED'}


class MECAFIG_OT_SoftModeAll(Operator):
    '''Soft Mode All'''
    bl_idname = 'mecafig.soft_mode_all'
    bl_label = 'All Soft'

    def execute(self, context):
        soft_mode_all(context)

        return{'FINISHED'}
