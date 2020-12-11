import bpy

from ..properties.armature import *
from ..utils import *

def get_bone_chain(object):
    return MECAFIG[object]['chain']

def clear_bones(context, object):
    ob = context.active_object
    data = ob.mecafig.armature.parts[object]
    p_bones = ob.pose.bones
    d_bones = ob.data.bones
    bone_chain = get_bone_chain(object)
    # FK
    for bone in bone_chain:
        bone = 'FK_' + bone
        p_bones[bone].rotation_quaternion = (1, 0, 0, 0)
    # IK
    ik_target = 'IK_Target_' + object
    if ik_target in p_bones.keys():
        p_bones[ik_target].location = (0, 0, 0)
        p_bones[ik_target].rotation_quaternion = (1, 0, 0, 0)
        p_bones[ik_target].scale = (1, 1, 1)

    if object.startswith('Leg'):
        p_bones['IK_Roll_' + object].rotation_quaternion = (1, 0, 0, 0)

    if object == 'Body':
        for i in range(2, 4): # For 'IK_Clavicle.L' & 'IK_Clavicle.R'
            p_bones['IK_' + bone_chain[i]].rotation_quaternion = (1, 0, 0, 0)
            p_bones['SP_Body_Roll'].rotation_quaternion = (1, 0, 0, 0)

    if object.startswith('Hand'):
        bone = 'SP_' + object
        p_bones[bone].location = (0, 0, 0)

    if object == 'Head':
        p_bones['IK_Roll_Head'].rotation_quaternion = (1, 0, 0, 0)
        p_bones['SP_Head_Roll'].rotation_quaternion = (1, 0, 0, 0)

    return {'FINISHED'}

def clear_all_bones(context):
    p_bones = context.active_object.pose.bones

    p_bones['CTRL_Hip'].location = (0, 0, 0)
    p_bones['CTRL_Hip'].rotation_quaternion = (1, 0, 0, 0)

    for ob in MECAFIG:
        clear_bones(context, ob)

    for bone in p_bones:
        if bone.name.startswith('SP_'):
            bone.rotation_quaternion = (1, 0, 0, 0)

    return {'FINISHED'}

def chain_snapping(context, chain, from_, to_):
    p_bones = context.active_object.pose.bones

    for bone in chain:
        from_bone = '%s_%s' %(from_, bone)
        to_bone = '%s_%s' %(to_, bone)
        p_bones[from_bone].matrix = p_bones[to_bone].matrix
        dg = context.evaluated_depsgraph_get()
        dg.update()

    return{'FINISHED'}

def fk_mode(context, object):
    ob = context.active_object
    data = ob.mecafig.armature.parts[object]
    snapping = data.enable_snapping
    p_bones = context.active_object.pose.bones
    bone_chain = get_bone_chain(object)

    if snapping:
        chain_snapping(context, bone_chain, 'FK', 'IK')

        if object == 'Head':
            p_bones['FK_' + bone_chain[1]].rotation_quaternion[0] = p_bones['IK_Roll_Head'].rotation_quaternion[0]
            p_bones['FK_' + bone_chain[1]].rotation_quaternion[3] = p_bones['IK_Roll_Head'].rotation_quaternion[3]

    if object.startswith('Leg'):
        p_bones['IK_Roll_' + object].rotation_quaternion = (1, 0, 0, 0)

    return{'FINISHED'}

def ik_mode(context, object):
    ob = context.active_object
    data = ob.mecafig.armature.parts[object]
    snapping = data.enable_snapping
    p_bones = context.active_object.pose.bones
    bone_chain = get_bone_chain(object)

    # Bones snapping
    if snapping:
        # Disable IK constraint(s)
        for bone in bone_chain:
            bone = 'IK_' + bone
            if 'IK' in p_bones[bone].constraints.keys():
                p_bones[bone].constraints['IK'].influence = 0
        # Snap chains
        if object != 'Head':
            chain_snapping(context, bone_chain, 'IK', 'FK')
        else:
            p_bones['IK_Roll_Head'].rotation_quaternion[0] = p_bones['FK_' + bone_chain[1]].rotation_quaternion[0]
            p_bones['IK_Roll_Head'].rotation_quaternion[3] = p_bones['FK_' + bone_chain[1]].rotation_quaternion[3]
        # Snap targets
        ik_target = 'IK_Target_' + object
        fk_target = 'FK_Target_' + object
        if (ik_target and fk_target) in p_bones.keys():
            p_bones[ik_target].matrix = p_bones[fk_target].matrix
            if not object.startswith('Leg'):
                p_bones[ik_target].rotation_quaternion = (1, 0, 0, 0)

        if object.startswith('Hand'):
            for bone in ['Finger', 'Thumb']:
                ik_target = 'IK_Target_%s.%s' %(bone, object.split('.')[1])
                fk_target = 'FK_Target_%s.%s' %(bone, object.split('.')[1])
                if (ik_target and fk_target) in p_bones.keys():
                    p_bones[ik_target].matrix = p_bones[fk_target].matrix
                    p_bones[ik_target].rotation_quaternion = (1, 0, 0, 0)
        # Enable IK constraint(s)
        for bone in bone_chain:
            bone = 'IK_' + bone
            if 'IK' in p_bones[bone].constraints.keys():
                p_bones[bone].constraints['IK'].influence = 1

    return {'FINISHED'}

def rigid_mode(context, object):
    ob = context.active_object
    data = ob.mecafig.armature.parts[object]
    p_bones = context.active_object.pose.bones
    bone_chain = get_bone_chain(object)

    # FK chain
    if object != 'Body':
        for i, bone in enumerate(bone_chain):
            if i != 0:
                bone = 'FK_' + bone_chain[i]
                p_bones[bone].rotation_quaternion = (1, 0, 0, 0)
    else: # For 'Body'
        for bone in bone_chain:
            bone = 'FK_' + bone
            p_bones[bone].rotation_quaternion = (1, 0, 0, 0)

    if object.startswith('Leg'):
        p_bones['IK_Roll_' + object].rotation_quaternion = (1, 0, 0, 0)

    elif object == 'Body':
        for i in range(1, 4):
            p_bones['IK_' + bone_chain[i]].rotation_quaternion = (1, 0, 0, 0)
        p_bones['IK_Target_Body'].location = (0, 0, 0)

    elif object.startswith('Hand'):
        for i, bone in enumerate(bone_chain):
            if i != 0:
                p_bones['FK_' + bone].rotation_quaternion = (1, 0, 0, 0)

    elif object == 'Head':
        p_bones['IK_Roll_Head'].rotation_quaternion = (1, 0, 0, 0)

    return {'FINISHED'}

def rigid_mode_all(context):
    ob = context.active_object
    data = ob.mecafig.armature.parts

    for ob in MECAFIG:
        data[ob].switch_rigid_soft = 'RIGID'

    return {'FINISHED'}

def soft_mode(context, object):
    return {'FINISHED'}

def soft_mode_all(context):
    ob = context.active_object
    data = ob.mecafig.armature.parts

    for ob in MECAFIG:
        data[ob].switch_rigid_soft = 'SOFT'

    return {'FINISHED'}
