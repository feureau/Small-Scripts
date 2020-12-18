import bpy

from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    PointerProperty,
    CollectionProperty
)

from ..props_functions.shading import *


class MecaFigShadingBaseSettings(PropertyGroup):

    color_id: StringProperty(
        default='24',
        update=update_color_id,
    )

    enable_custom_base: BoolProperty(
        name='Enable Custom Base',
        description='Enable/Disable Custom Base',
        default=False,
        update=update_enable_custom_base,
    )

    color: FloatVectorProperty(
        name='Color',
        description='Color',
        subtype='COLOR',
        size=4,
        default=[1.0, 1.0, 1.0, 1.0],
        min=0,
        max=1,
        soft_min=0,
        soft_max=1,
        get=get_color,
        set=set_color,
    )

    subsurface: FloatProperty(
        name='Subsurface',
        description='Subsurface',
        default=.1,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_subsurface,
        set=set_subsurface,
    )

    subsurface_color: FloatVectorProperty(
        name='Subsurface Color',
        description='Subsurface color',
        subtype='COLOR',
        size=4,
        default=[1.0, 1.0, 1.0, 1.0],
        min=0,
        max=1,
        soft_min=0,
        soft_max=1,
        get=get_subsurface_color,
        set=set_subsurface_color,
    )

    metallic: FloatProperty(
        name='Metallic',
        description='Metallic',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_metallic,
        set=set_metallic,
    )

    specular: FloatProperty(
        name='Specular',
        description='Specular',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_specular,
        set=set_specular,
    )

    specular_tint: FloatProperty(
        name='Specular Tint',
        description='Specular tint',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_specular_tint,
        set=set_specular_tint,
    )

    roughness: FloatProperty(
        name='Roughness',
        description='Roughness',
        default=.1,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_roughness,
        set=set_roughness,
    )

    transmission: FloatProperty(
        name='Transmission',
        description='Transmission',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        update=update_transmission,
        get=get_transmission,
        set=set_transmission,
    )

    emission: FloatProperty(
        name='Emission',
        description='Emission',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_emission,
        set=set_emission,
    )

    emission_color: FloatVectorProperty(
        name='Emission Color',
        description='Emission Color',
        subtype='COLOR',
        size=4,
        default=[0, 0, 0, 1],
        min=0,
        max=1,
        soft_min=0,
        soft_max=1,
        get=get_emission_color,
        set=set_emission_color,
    )

    flatness_scale: FloatProperty(
        name='Flatness Scale',
        description='Flatness scale',
        default=1,
        min=0,
        max=10,
        step=10,
        precision=3,
        get=get_flatness_scale,
        set=set_flatness_scale,
    )

    flatness_strength: FloatProperty(
        name='Flatness Strength',
        description='Flatness strength',
        default=.2,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_flatness_strength,
        set=set_flatness_strength,
    )

    granulosity_scale: FloatProperty(
        name='Granulosity Scale',
        description='Granulosity scale',
        default=250,
        min=0,
        max=1000,
        step=10,
        precision=3,
        get=get_granulosity_scale,
        set=set_granulosity_scale,
    )

    granulosity_strength: FloatProperty(
        name='Granulosity Strength',
        description='Granulosity strength',
        default=.2,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_granulosity_strength,
        set=set_granulosity_strength,
    )

    glitter_amount: FloatProperty(
        name='Glitter Amount',
        description='Glitter amount',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_glitter_amount,
        set=set_glitter_amount,
    )

    glitter_scale: FloatProperty(
        name='Glitter Scale',
        description='Glitter scale',
        default=100,
        min=0,
        max=1000,
        step=10,
        precision=3,
        get=get_glitter_scale,
        set=set_glitter_scale,
    )

    paint_intensity: FloatProperty(
        name='Paint Intensity',
        description='Paint Intensity',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_intensity,
        set=set_paint_intensity,
    )

    paint_color: FloatVectorProperty(
        name='Paint Color',
        description='Paint Color',
        subtype='COLOR',
        size=4,
        default=[1.0, 1.0, 1.0, 1.0],
        min=0,
        max=1,
        soft_min=0,
        soft_max=1,
        get=get_paint_color,
        set=set_paint_color,
    )

    paint_metallic: FloatProperty(
        name='Paint Metallic',
        description='Paint Metallic',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_metallic,
        set=set_paint_metallic,
    )

    paint_specular: FloatProperty(
        name='Paint Specular',
        description='Paint Specular',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_specular,
        set=set_paint_specular,
    )

    paint_specular_tint: FloatProperty(
        name='Paint Specular Tint',
        description='Paint Specular tint',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_specular_tint,
        set=set_paint_specular_tint,
    )

    paint_roughness: FloatProperty(
        name='Paint Roughness',
        description='Paint Roughness',
        default=.1,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_roughness,
        set=set_paint_roughness,
    )

    paint_scale: FloatProperty(
        name='Paint Scale',
        description='Paint scale',
        default=250,
        min=0,
        max=1000,
        step=10,
        precision=3,
        get=get_paint_scale,
        set=set_paint_scale,
    )

    paint_strength: FloatProperty(
        name='Paint Strength',
        description='Paint strength',
        default=.2,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_paint_strength,
        set=set_paint_strength,
    )


class MecaFigShadingBase(PropertyGroup):

    name: StringProperty(
        default='Base'
    )

    enable_dual_base: BoolProperty(
        name='Enable Dual Base',
        description='Enable/Disable Dual Base for dual-moulded parts',
        default=False,
        get=get_dual_base,
        set=set_dual_base
    )

    select_base: EnumProperty(
        name='Select Base',
        description='Select the Base to set',
        items=[
            ('1', 'BASE #1', 'Select Base #1'),
            ('2', 'BASE #2', 'Select Base #2')
        ]
    )

    base_id: CollectionProperty(
        type=MecaFigShadingBaseSettings
    )

    use_normal_map: BoolProperty(
        name='Use Normal Map',
        description='Use Normal Map for adding extra details to the part',
        default=True,
        get=get_use_normal_map,
        set=set_use_normal_map
    )


class MecaFigShadingMapsSettings(PropertyGroup):

    use: BoolProperty(
        name='Enable/Disable Map',
        description='Enable/Disable use of the Map',
        default=True,
    )

    metallic: FloatProperty(
        name='Metallic',
        description='Metallic',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_maps_metallic,
        set=set_maps_metallic,
    )

    specular: FloatProperty(
        name='Specular',
        description='Specular',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_maps_specular,
        set=set_maps_specular,
    )

    roughness: FloatProperty(
        name='Roughness',
        description='Roughness',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_maps_roughness,
        set=set_maps_roughness,
    )

    strength: FloatProperty(
        name='Strength',
        description='Strength',
        default=.8,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_maps_strength,
        set=set_maps_strength,
    )


class MecaFigShadingMaps(PropertyGroup):

    name: StringProperty(
        default='Maps'
    )

    enable: BoolProperty(
        name='Enable Maps',
        description='Enable/Disable Maps',
        default=False,
        get=get_enable_maps,
        set=set_enable_maps,
    )

    workflow: EnumProperty(
        name='Workflow',
        description='Select the workflow for the Maps',
        items=[
            ('DEC_MET', 'Decoration & Metalness', 'Decoration & Metalness', 0),
            ('COL_DAT', 'Color & Data', 'Color & Data', 1)
        ],
        get=get_workflow,
        set=set_workflow
    )

    uv_map: EnumProperty(
        name='UV Map',
        description='UV Map',
        items=enum_items_maps_uv_map,
        update=update_maps_uv_map,
    )

    maps: CollectionProperty(
        type=MecaFigShadingMapsSettings
    )


class MecaFigShadingWearsSettings(PropertyGroup):

    intensity: FloatProperty(
        name='Intensity',
        description='Intensity',
        default=.5,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_intensity,
        set=set_wears_intensity,
    )

    amount: FloatProperty(
        name='Amount',
        description='Amount',
        default=.5,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_amount,
        set=set_wears_amount,
    )

    color: FloatVectorProperty(
        name='',
        description='Color',
        subtype='COLOR',
        size=4,
        default=[1.0, 1.0, 1.0, 1.0],
        min=0,
        max=1,
        soft_min=0,
        soft_max=1,
        get=get_wears_color,
        set=set_wears_color,
    )

    color_opacity: FloatProperty(
        name='Color Opacity',
        description='Color opacity',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_color_opacity,
        set=set_wears_color_opacity,
    )

    specular: FloatProperty(
        name='Specular',
        description='Sspecular',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_specular,
        set=set_wears_specular,
    )

    roughness: FloatProperty(
        name='Roughness',
        description='Roughness',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_roughness,
        set=set_wears_roughness,
    )

    strength: FloatProperty(
        name='Strength',
        description='Strength',
        default=0,
        min=0,
        max=1,
        step=.1,
        precision=3,
        get=get_wears_strength,
        set=set_wears_strength,
    )

    seed: IntProperty(
        name='Seed',
        description='Seed',
        default=0,
        min=0,
        max=1000,
        get=get_wears_seed,
        set=set_wears_seed,
    )


class MecaFigShadingWears(PropertyGroup):

    name: StringProperty(
        default='Wears'
    )

    enable: BoolProperty(
        name='Enable Wears',
        description='Enable/Disable Wears',
        default=False,
        get=get_enable_wears,
        set=set_enable_wears,
    )

    wears: CollectionProperty(
        type=MecaFigShadingWearsSettings
    )


class MecaFigShading(PropertyGroup):

    base: PointerProperty(
        type=MecaFigShadingBase
    )

    maps: PointerProperty(
        type=MecaFigShadingMaps
    )

    wears: PointerProperty(
        type=MecaFigShadingWears
    )


class MecaFigSceneShadingPanels(PropertyGroup):

    show_panel: BoolProperty(
        name='',
        description='Show/Hide panel',
        default=False,
    )


class MecaFigSceneShading(PropertyGroup):

    apply_settings_for: EnumProperty(
        name='Apply Settings For',
        description='Apply settings for Active, Selected or All objects',
        items=[
            ('ACTIVE', 'Active', 'Apply settings for Active object'),
            ('SELECTED', 'Selected', 'Apply settings for Selected objects'),
            ('ALL', 'All', 'Apply settings for All objects'),
        ],
    )

    panels: CollectionProperty(
        type=MecaFigSceneShadingPanels
    )
