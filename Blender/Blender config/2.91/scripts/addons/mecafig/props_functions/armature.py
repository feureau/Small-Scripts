import bpy

from ..functions.armature import *
from ..functions.mecafig import get_mecafig
from ..functions.shading import get_nodes

def update_armature_scale(self, context):
    mf = get_mecafig(context)
    for ob in mf.children:
        if ob.mecafig.geometry.name in MECAFIG:
            if ob.active_material:
                nodes = get_nodes(ob.active_material)
                input = 'Scale'
                value = self.scale
                nodes[NODE].inputs[input].default_value = value

def get_armature_scale(self):
    ob = self.id_data
    value = ob.scale[0]
    return value

def set_armature_scale(self, value):
    ob = self.id_data
    ob.scale = (value, value, value)

def update_enable_link(self, context):
    part = self.name
    bone = context.active_object.pose.bones['RT_%s' % part]
    if self.enable_link:
        bone.constraints['Child Of'].influence = 1
        bone.location = (0, 0, 0)
        bone.rotation_quaternion = (1, 0, 0, 0)
    else:
        bone_matrix = bone.matrix
        bone.constraints['Child Of'].influence = 0
        bone.matrix = bone_matrix

def update_switch_rigid_soft(self, context):
    if self.switch_rigid_soft == 'RIGID':
        bpy.ops.mecafig.rigid_mode(part=self.name)
    elif self.switch_rigid_soft == 'SOFT':
        bpy.ops.mecafig.soft_mode(part=self.name)

def update_switch_fk_ik(self, context):
    if self.switch_fk_ik == 'FK':
        bpy.ops.mecafig.fk_mode(part=self.name)
    elif self.switch_fk_ik == 'IK':
        bpy.ops.mecafig.ik_mode(part=self.name)
