# <pep8 compliant>

from math import degrees
import os
import re

from . import write_ascii_xps
from . import xps_types
from .timing import timing
import bpy
from mathutils import Vector


def getOutputPoseSequence(filename):
    filepath, file = os.path.split(filename)
    basename, ext = os.path.splitext(file)
    poseSuffix = re.sub('\d+$', '', basename)

    startFrame = bpy.context.scene.frame_start
    endFrame = bpy.context.scene.frame_end
    initialFrame = bpy.context.scene.frame_current

    for currFrame in range(startFrame, endFrame + 1):
        bpy.context.scene.frame_set(currFrame)
        numSuffix = '{:0>3d}'.format(currFrame)
        name = poseSuffix + numSuffix + ext

        newPoseFilename = os.path.join(filepath, name)
        getOutputFilename(newPoseFilename)

    bpy.context.scene.frame_current = initialFrame


def getOutputFilename(filename):
    blenderExportSetup()
    xpsExport(filename)
    blenderExportFinalize()


def blenderExportSetup():
    pass


def blenderExportFinalize():
    pass


def saveXpsFile(filename, xpsPoseData):
    # dirpath, file = os.path.split(filename)
    # basename, ext = os.path.splitext(file)
    write_ascii_xps.writeXpsPose(filename, xpsPoseData)


@timing
def xpsExport(filename):
    global rootDir
    global xpsData

    print("------------------------------------------------------------")
    print("---------------EXECUTING XPS PYTHON EXPORTER----------------")
    print("------------------------------------------------------------")
    print("Exporting Pose: ", filename)

    rootDir, file = os.path.split(filename)
    print('rootDir: {}'.format(rootDir))

    xpsPoseData = exportPose()

    saveXpsFile(filename, xpsPoseData)


def exportPose():
    armature = next((obj for obj in bpy.context.selected_objects
                     if obj.type == 'ARMATURE'), None)
    boneCount = len(armature.data.bones)
    print('Exporting Pose', str(boneCount), 'bones')

    return xpsPoseData(armature)


def xpsPoseData(armature):
    context = bpy.context
    currentMode = bpy.context.mode
    currentObj = bpy.context.active_object
    context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    bones = armature.pose.bones
    objectMatrix = armature.matrix_world

    xpsPoseData = {}
    for poseBone in bones:
        boneName = poseBone.name
        boneData = xpsPoseBone(poseBone, objectMatrix)
        xpsPoseData[boneName] = boneData

    bpy.ops.object.posemode_toggle()
    context.view_layer.objects.active = currentObj
    bpy.ops.object.mode_set(mode=currentMode)

    return xpsPoseData


def xpsPoseBone(poseBone, objectMatrix):
    boneName = poseBone.name
    boneRotDelta = xpsBoneRotate(poseBone)
    boneCoordDelta = xpsBoneTranslate(poseBone, objectMatrix)
    boneScale = xpsBoneScale(poseBone)
    boneData = xps_types.XpsBonePose(boneName, boneCoordDelta, boneRotDelta,
                                     boneScale)
    return boneData


def eulerToXpsBoneRot(rotEuler):
    xDeg = degrees(rotEuler.x)
    yDeg = degrees(rotEuler.y)
    zDeg = degrees(rotEuler.z)
    return Vector((xDeg, yDeg, zDeg))


def vectorTransform(vec):
    x = vec.x
    y = vec.y
    z = vec.z
    y = -y
    newVec = Vector((x, z, y))
    return newVec


def vectorTransformTranslate(vec):
    x = vec.x
    y = vec.y
    z = vec.z
    y = -y
    newVec = Vector((x, z, y))
    return newVec


def vectorTransformScale(vec):
    x = vec.x
    y = vec.y
    z = vec.z
    newVec = Vector((x, y, z))
    return newVec


def xpsBoneRotate(poseBone):
    # LOCAL PoseBone
    poseMatGlobal = poseBone.matrix_basis.to_quaternion()
    # LOCAL EditBoneRot
    editMatLocal = poseBone.bone.matrix_local.to_quaternion()

    rotQuat = editMatLocal @ poseMatGlobal @ editMatLocal.inverted()
    rotEuler = rotQuat.to_euler('YXZ')
    xpsRot = eulerToXpsBoneRot(rotEuler)
    rot = vectorTransform(xpsRot)
    return rot


def xpsBoneTranslate(poseBone, objectMatrix):
    translate = poseBone.location
    # LOCAL EditBoneRot
    editMatLocal = poseBone.bone.matrix_local.to_quaternion()
    vector = editMatLocal @ translate
    return vectorTransformTranslate(objectMatrix.to_3x3() @ vector)


def xpsBoneScale(poseBone):
    scale = poseBone.scale
    return vectorTransformScale(scale)


if __name__ == "__main__":
    writePosefilename0 = (r"G:\3DModeling\XNALara\XNALara_XPS\dataTest\Models"
                          r"\Queen's Blade\echidna pose - copy.pose")

    getOutputFilename(writePosefilename0)
