import bpy

from .mecafig import *
from .armature import *
from .shading import *
from .palette import *


classes = (
    MECAFIG_OT_AddMecaFig,
    MECAFIG_OT_AddMecaFigFromFile,
    MECAFIG_OT_DeleteMecaFig,
    MECAFIG_OT_ClearBones,
    MECAFIG_OT_ClearAllBones,
    MECAFIG_OT_FKMode,
    MECAFIG_OT_IKMode,
    MECAFIG_OT_RigidMode,
    MECAFIG_OT_SoftMode,
    MECAFIG_OT_RigidModeAll,
    MECAFIG_OT_SoftModeAll,
    MECAFIG_OT_CopySettingsTo,
    MECAFIG_OT_ShadingReset,
    MECAFIG_OT_SelectImage,
    MECAFIG_OT_OpenImage,
    MECAFIG_OT_UnlinkImage,
    MECABRICKS_OT_ColorPalette,
)

def register_operators():
    for classe in classes:
        bpy.utils.register_class(classe)

def unregister_operators():
    for classe in reversed(classes):
        bpy.utils.unregister_class(classe)
