import bpy

from bpy.types import PropertyGroup
from bpy.props import PointerProperty, CollectionProperty

from .mecafig import *
from .geometry import *
from .armature import *
from .shading import *


class MecaFigObject(PropertyGroup):

    armature: PointerProperty(
        type=MecaFigArmature
    )

    geometry: PointerProperty(
        type=MecaFigGeometry
    )

classes = (
    MecaFigGeometry,
    MecaFigArmatureParts,
    MecaFigArmature,
    MecaFigObject,
    MecaFigShadingBaseSettings,
    MecaFigShadingBase,
    MecaFigShadingMapsSettings,
    MecaFigShadingMaps,
    MecaFigShadingWearsSettings,
    MecaFigShadingWears,
    MecaFigShading,
    MecaFigSceneShadingPanels,
    MecaFigSceneShading,
    MecaFigScene,
)

def register_properties():
    for classe in classes:
        bpy.utils.register_class(classe)

    bpy.types.Object.mecafig = PointerProperty(type=MecaFigObject)
    #bpy.types.Armature.mecafig = CollectionProperty(type=MecaFigArmature)
    bpy.types.Material.mecafig = PointerProperty(type=MecaFigShading)
    bpy.types.Scene.mecafig = PointerProperty(type=MecaFigScene)

def unregister_properties():
    for classe in reversed(classes):
        bpy.utils.unregister_class(classe)

    del bpy.types.Mesh.mecafig
    del bpy.types.Armature.mecafig
    del bpy.types.Material.mecafig
    del bpy.types.Scene.mecafig
