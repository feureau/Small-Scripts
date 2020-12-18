import bpy

from bpy.types import PropertyGroup
from bpy.props import BoolProperty, IntProperty, PointerProperty, EnumProperty

from ..props_functions.geometry import *


class MecaFigGeometry(PropertyGroup):

    show_part: BoolProperty(
        name='Part Visibility',
        description='Show/Hide part',
        default=True,
        get=get_show_part,
        set=set_show_part
    )

    show_panel: BoolProperty(
        description='Show/Hide panel',
        default=False,
    )

    mesh: EnumProperty(
        name='Part Mesh',
        description='',
        items=enum_items_mesh,
        update=update_mesh
    )

    enable_subsurf_viewport: BoolProperty(
        name='Subsurf Viewport',
        description='Enable/Disable Subdivision Surface in 3D Viewport',
        default=False,
        get=get_enable_subsurf_viewport,
        set=set_enable_subsurf_viewport
    )

    enable_subsurf_render: BoolProperty(
        name='Subsurf Render',
        description='Enable/Disable Subdivision Surface for Render',
        default=False,
        get=get_enable_subsurf_render,
        set=set_enable_subsurf_render
    )

    subsurf_levels_viewport: IntProperty(
        name='Viewport',
        description='Level of Subdivision in 3D Viewport',
        default=2,
        min=0,
        max=6,
        get=get_subsurf_levels_viewport,
        set=set_subsurf_levels_viewport
    )

    subsurf_levels_render: IntProperty(
        name='Render',
        description='Level of Subdivision for Render',
        default=2,
        min=0,
        max=6,
        get=get_subsurf_levels_render,
        set=set_subsurf_levels_render
    )
