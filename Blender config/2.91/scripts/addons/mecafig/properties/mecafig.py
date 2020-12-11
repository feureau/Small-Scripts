import bpy

from bpy.types import PropertyGroup
from bpy.props import StringProperty, PointerProperty, EnumProperty

from .shading import *
from ..props_functions.mecafig import *


class MecaFigScene(PropertyGroup):

    name: StringProperty(
        name='',
        description='',
        default='MecaFig',
        maxlen=32,
        get=get_name,
        set=set_name
    )

    select: EnumProperty(
        name='Select MecaFig',
        description='',
        items=enum_items_select,
        update=update_select
    )

    shading: PointerProperty(
        type=MecaFigSceneShading
    )
