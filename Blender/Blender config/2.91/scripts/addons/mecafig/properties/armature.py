import bpy

from bpy.types import PropertyGroup
from bpy.props import BoolProperty, EnumProperty, StringProperty, CollectionProperty, FloatProperty

from ..props_functions.armature import *


class MecaFigArmatureParts(PropertyGroup):

    show_panel: BoolProperty(
        name='',
        description='Show/Hide panel',
        default=False,
    )

    show_bones: BoolProperty(
        name='',
        description='Show/Hide bones',
        default=True,
    )

    enable_link: BoolProperty(
        name='',
        description='Link/Unlink',
        default=True,
        update=update_enable_link,
    )

    switch_rigid_soft: EnumProperty(
        name='Switch Rigid/Soft',
        description='Switch between Rigid mode and Soft mode',
        items=[
            ('RIGID', 'Rigid', 'Switch to Rigid mode'),
            ('SOFT', 'Soft', 'Switch to Soft mode'),
        ],
        update=update_switch_rigid_soft,
    )

    switch_fk_ik: EnumProperty(
        name='Switch FK/IK',
        description='Switch between FK mode and IK mode',
        items=[
            ('FK', 'FK', 'Switch to FK mode'),
            ('IK', 'IK', 'Switch to IK mode'),
        ],
        update=update_switch_fk_ik,
    )

    enable_snapping: BoolProperty(
        name='Snapping',
        description='Enable/Disable automatic snapping between FK and IK chains',
        default=True,
    )


class MecaFigArmature(PropertyGroup):

    scale: FloatProperty(
        name='Scale',
        description='Scale',
        default=1,
        min=.01,
        max=100,
        step=3,
        precision=3,
        update=update_armature_scale,
        get=get_armature_scale,
        set=set_armature_scale,
    )

    show_root_bones: BoolProperty(
        name='',
        description='Show/Hide root bones',
        default=False,
    )

    show_special_bones: BoolProperty(
        name='',
        description='Show/Hide special bones',
        default=False,
    )

    show_anchor_bones: BoolProperty(
        name='',
        description='Show/Hide anchor bones',
        default=False,
    )

    parts: CollectionProperty(
        type=MecaFigArmatureParts
    )
