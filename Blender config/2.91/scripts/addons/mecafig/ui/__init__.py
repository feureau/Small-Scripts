import bpy

from .mecafig import *
from .armature import *
from .geometry import *
from .shading import *
from .help import *

classes = (
    MECAFIG_PT_MecaFig,
    MECAFIG_PT_Geometry,
    MECAFIG_PT_Armature,
    MECAFIG_PT_Shading,
    MECAFIG_PT_Help,
)

def register_ui():
    for classe in classes:
        bpy.utils.register_class(classe)

def unregister_ui():
    for classe in reversed(classes):
        bpy.utils.unregister_class(classe)
