'''
Copyright (C) 2020 Nicolas Jarraud
mecabricks@gmail.com

Created by Nicolas Jarraud

    License of the software is non-exclusive, non-transferrable
    and is granted only to the original buyer. Buyers do not own
    any Product and are only licensed to use it in accordance
    with terms and conditions of the applicable license. The Seller
    retains copyright in the software purchased or downloaded by any Buyer.

    The Buyer may not resell, redistribute, or repackage the Product
    without explicit permission from the Seller.

    Any Product, returned to Mecabricks and (or) the Seller in accordance
    with applicable law for whatever reason must be destroyed by the Buyer
    immediately. The license to use any Product is revoked at the time
    Product is returned. Product obtained by means of theft or fraudulent
    activity of any kind is not granted a license.
'''

bl_info = {
    "name": "Mecabricks Advanced",
    "description": "Import Mecabricks 3D Models",
    "author": "Nicolas Jarraud",
    "version": (2, 1, 7),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "warning": "",
    "wiki_url": "www.mecabricks.com",
    "category": "Import-Export"
}

import bpy
import os
import math

from .loaders.LocalPartListLoader import LocalPartListLoader
from .loaders.SceneLoader import SceneLoader
from .loaders.utils import find_node

# ------------------------------------------------------------------------------
# Import Mecabricks scene
# ------------------------------------------------------------------------------
def import_mecabricks(self, context, filepath, settings):
    # Check Blender version
    if bpy.app.version < (2, 80, 0):
        self.report({'ERROR'}, 'This add-on requires Blender 2.80 or greater.')
        return {'FINISHED'}

    # Ensure that viewport is in object mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    # Create new collection
    collection_name = os.path.splitext(os.path.basename(filepath))[0]
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)

    # Load list of local parts
    local_list = {}
    if settings['local']:
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        local_list = LocalPartListLoader().load(addon_prefs.local_dir)

    # Addon directory path
    addon_path = os.path.dirname(os.path.realpath(__file__))

    # Bevels
    bevel = False
    if settings['bevels']:
        bevel = {'width': settings['bevelWidth'], 'segments': settings['bevelSegments']}

    # Load scene
    loader = SceneLoader(addon_path, settings['logos'], bevel, local_list)
    scene = loader.load(filepath, collection)

    # Customize materials
    panel_settings = bpy.context.scene.mb_settings
    for material in scene['materials']:
        nodes = material.node_tree.nodes
        node = find_node(nodes, 'Customize')

        node.inputs['Scratches'].default_value = panel_settings.material_scratches / 100
        node.inputs['Dents'].default_value = panel_settings.material_dents / 100
        node.inputs['Fingerprints'].default_value = panel_settings.material_fingerprints / 100
        node.inputs['Dirt'].default_value = panel_settings.material_dirt / 100
        node.inputs['Color Variation'].default_value = panel_settings.material_color_shift / 100
        node.inputs['Deformation'].default_value = panel_settings.material_deformation / 100

    # Customization visibility
    update_customization_state(panel_settings.material_mute)

    # Focus viewports
    focus_viewports(scene['parts'])

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    # Select empty
    scene['empty'].select_set(state=True)
    bpy.context.view_layer.objects.active = scene['empty']

    return {'FINISHED'};

# ------------------------------------------------------------------------------
# Scratches
# ------------------------------------------------------------------------------
def update_scratches(self, context):
    customize_materials('Scratches', self.material_scratches)

# ------------------------------------------------------------------------------
# Dents
# ------------------------------------------------------------------------------
def update_dents(self, context):
    customize_materials('Dents', self.material_dents)

# ------------------------------------------------------------------------------
# Fingerprints
# ------------------------------------------------------------------------------
def update_fingerprints(self, context):
    customize_materials('Fingerprints', self.material_fingerprints)

# ------------------------------------------------------------------------------
# Dirt
# ------------------------------------------------------------------------------
def update_dirt(self, context):
    customize_materials('Dirt', self.material_dirt)

# ------------------------------------------------------------------------------
# Color Shift
# ------------------------------------------------------------------------------
def update_color_shift(self, context):
    customize_materials('Color Variation', self.material_color_shift)

# ------------------------------------------------------------------------------
# Deformation
# ------------------------------------------------------------------------------
def update_deformation(self, context):
    customize_materials('Deformation', self.material_deformation)

# ------------------------------------------------------------------------------
# Customize material
# ------------------------------------------------------------------------------
def customize_materials(param, value):
    materials = bpy.data.materials

    for material in materials:
        # Parse name
        name_split = material.name.split(':')

        # Only process mecabricks materials
        if name_split[0] != 'mb' or material.name == 'mb:nodes':
            continue

        # Material node
        nodes = material.node_tree.nodes
        node = find_node(nodes, 'Customize')

        # Update input
        node.inputs[param].default_value = value / 100

# ------------------------------------------------------------------------------
# Mute/Unmute customization
# ------------------------------------------------------------------------------
def toggle_customization(self, context):
    update_customization_state(self.material_mute)

# ------------------------------------------------------------------------------
# Mute/Unmute customization sub function
# ------------------------------------------------------------------------------
def update_customization_state(mute):
    # Check if customize node exists
    if 'mb_customization' not in bpy.data.node_groups:
        return

    # Data
    group = bpy.data.node_groups['mb_customization']
    nodes = group.nodes
    links = group.links

    # Mute
    if mute:
        links.remove(nodes['Group Output'].inputs['Color Variation'].links[0])
        links.remove(nodes['Group Output'].inputs['Roughness'].links[0])
        links.new(nodes['Group Input'].outputs['Normal'], nodes['Group Output'].inputs['Normal'])

    # Unmute
    else:
        links.new(nodes['Group Input'].outputs['Color Variation'], nodes['Group Output'].inputs['Color Variation'])
        links.new(nodes['mb_custom_roughness'].outputs['Roughness'], nodes['Group Output'].inputs['Roughness'])
        links.new(nodes['mb_custom_normal'].outputs['Normal'], nodes['Group Output'].inputs['Normal'])

# ------------------------------------------------------------------------------
# Focus viewport cameras on added elements
# ------------------------------------------------------------------------------
def focus_viewports(objects):
    # Select added objects
    for object in objects:
        object.select_set(state=True)

    # Focus viewport on scene for all 3D views
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D' and area.spaces[0].region_3d.view_perspective != 'CAMERA':
            ctx = bpy.context.copy()
            ctx['area'] = area
            ctx['region'] = area.regions[-1]
            bpy.ops.view3d.view_selected(ctx)

# ------------------------------------------------------------------------------
# Import panel
# ------------------------------------------------------------------------------
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty
from bpy.types import Operator

class IMPORT_OT_zmbx(Operator, ImportHelper):
    bl_idname = 'import_mecabricks.zmbx'
    bl_description = 'Import from Mecabricks file format (.zmbx)'
    bl_label = "Import ZMBX"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_options = {'UNDO'}

    filepath: StringProperty(
        name="input file",
        subtype='FILE_PATH'
    )

    filename_ext = ".zmbx"

    filter_glob: StringProperty(
        default = "*.zmbx",
        options = {'HIDDEN'},
    )

    # Logos
    setting_logos: BoolProperty(
            name="Logo on studs",
            description="Display brand logo on top of studs",
            default=True,
            )

    # Local parts
    setting_local: BoolProperty(
            name="Local Parts",
            description="Use parts stored locally when available",
            default=False,
            )

    # Bevels
    setting_bevels: BoolProperty(
            name="Bevels",
            description="Add geometry bevels",
            default=False,
            )

    # Bevel Width
    setting_bevelWidth: FloatProperty(
        name='Width',
        description='Bevel value clamped to avoid overlap',
        min=0,
        max=1,
        default=0.2)

    # Bevel Segments
    setting_bevelSegments: IntProperty(
        name='Segments',
        description='Number of segments for bevels',
        min=1,
        max=16,
        default=3)

    def draw(self, context):
        layout = self.layout

        # Geometry
        box = layout.box()
        box.label(text='Geometry Options: ', icon="OUTLINER_DATA_MESH" )

        # Logos
        row = box.row()
        row.prop(self.properties, 'setting_logos')

        # Local parts
        row = box.row()
        row.prop(self.properties, 'setting_local')

        # Read addon preferences to check if a directory path is available
        addonPref = bpy.context.preferences.addons[__name__].preferences
        if addonPref.local_dir == '':
            # Disable and unckeched option if a path is not available
            row.enabled = False
            self.setting_local = False
        else:
            # Enable option if a path is available
            row.enabled = True

        # Bevel
        row = box.row()
        row.prop(self.properties, 'setting_bevels')

        if self.setting_bevels:
            row = box.row()
            row.prop(self.properties, 'setting_bevelWidth')

            row = box.row()
            row.prop(self.properties, 'setting_bevelSegments')

    def execute(self, context):
        settings = {
            'logos': self.setting_logos,
            'local': self.setting_local,
            'bevels': self.setting_bevels,
            'bevelWidth': self.setting_bevelWidth,
            'bevelSegments': self.setting_bevelSegments
        }

        return import_mecabricks(self, context, self.filepath, settings)

# ------------------------------------------------------------------------------
# Randomize selected elements
# ------------------------------------------------------------------------------
class MB_OT_randomize(Operator):
    bl_idname = "mecabricks.randomize"
    bl_label = "Randomize Transform"
    bl_description = "Randomize location and rotation of selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    strength: IntProperty(
       name="Strength",
       default=0,
       min=0,
       max=100,
       subtype='PERCENTAGE',)

    def execute(self, context):
       objects = [ob for ob in bpy.context.selected_objects]

       # Values for randomize_transform
       loc = 0.4 * (self.strength / 100)
       rot = 2 * (self.strength / 100) * math.pi / 180

       # Clear delta for all selected objects
       for object in objects:
           object.delta_location=(0,0,0)
           object.delta_rotation_euler=(0,0,0)

       # Apply randomization to all selected object
       bpy.ops.object.randomize_transform(
           random_seed=0,
           use_delta=True,
           use_loc=True,
           loc=(loc,loc,loc),
           use_rot=True,
           rot=(rot,rot,rot)
       )

       return {'FINISHED'}

# ------------------------------------------------------------------------------
# Global Settings
# ------------------------------------------------------------------------------
class mecabricks_settings(bpy.types.PropertyGroup):
    material_scratches: IntProperty(
        name='Scratches',
        description='Update scratches strength for Mecabricks materials',
        min=0,
        max=100,
        default=10,
        subtype='PERCENTAGE',
        update=update_scratches)

    material_dents: IntProperty(
        name='Dents',
        description='Update dents strength for Mecabricks materials',
        min=0,
        max=100,
        default=25,
        subtype='PERCENTAGE',
        update=update_dents)

    material_fingerprints: IntProperty(
        name='Fingerprints',
        description='Update fingerprints strength for Mecabricks materials',
        min=0,
        max=100,
        default=25,
        subtype='PERCENTAGE',
        update=update_fingerprints)

    material_dirt: IntProperty(
        name='Dirt',
        description='Update dirt strength for Mecabricks materials',
        min=0,
        max=100,
        default=25,
        subtype='PERCENTAGE',
        update=update_dirt)

    material_color_shift: IntProperty(
        name='Color Shift',
        description='Shift base color values for Mecabricks materials',
        min=0,
        max=100,
        default=10,
        subtype='PERCENTAGE',
        update=update_color_shift)

    material_deformation: IntProperty(
        name='Deformation',
        description='Update deformation strength for Mecabricks materials',
        min=0,
        max=100,
        default=80,
        subtype='PERCENTAGE',
        update=update_deformation)

    material_mute: BoolProperty(
            name='Mute',
            description="Mute material customization",
            default=False,
            update=toggle_customization)

# ------------------------------------------------------------------------------
# Viewport Panel
# ------------------------------------------------------------------------------
class VIEW3D_PT_mecabricks_tools(bpy.types.Panel):
    bl_category = 'Mecabricks'
    bl_label = "Mecabricks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mb_settings

        box = layout.box()
        box.label(text='Materials: ', icon="MATERIAL_DATA")

        row = box.row()
        row.prop(settings,"material_scratches")
        row = box.row()
        row.prop(settings,"material_dents")
        row = box.row()
        row.prop(settings,"material_fingerprints")
        row = box.row()
        row.prop(settings,"material_dirt")
        row = box.row()
        row.prop(settings,"material_color_shift")
        row = box.row()
        row.prop(settings,"material_deformation")
        row = box.row()
        row.prop(settings,"material_mute")

        box = layout.box()
        box.label(text='Parts: ', icon="OBJECT_DATA")

        row = box.row()
        row.operator("mecabricks.randomize", text="Randomize")

# ------------------------------------------------------------------------------
# Preferences
# ------------------------------------------------------------------------------
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # Local parts directory
    local_dir: StringProperty(
        name='Part directory',
        description='Path of directory containing local parts',
        default='',
        subtype='DIR_PATH')

    # Draw preferences
    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager

        box = layout.box()
        row = box.row(align=True)
        row.prop(self, 'local_dir', expand=True)

# ------------------------------------------------------------------------------
# Register / Unregister
# ------------------------------------------------------------------------------
# Import menu
def menu_func(self, context):
    self.layout.operator(IMPORT_OT_zmbx.bl_idname, text = 'Mecabricks (.zmbx)')

def register():
    bpy.utils.register_class(IMPORT_OT_zmbx)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)

    # Randomize operator
    bpy.utils.register_class(MB_OT_randomize)

    # Register global settings
    bpy.utils.register_class(mecabricks_settings)
    bpy.types.Scene.mb_settings = bpy.props.PointerProperty(type=mecabricks_settings)

    # Register Tools
    bpy.utils.register_class(VIEW3D_PT_mecabricks_tools)

    # Register preferences
    bpy.utils.register_class(AddonPreferences)

def unregister():
    bpy.utils.unregister_class(IMPORT_OT_zmbx)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)

    bpy.utils.unregister_class(MB_OT_randomize)

    bpy.utils.unregister_class(mecabricks_settings)
    del bpy.types.Scene.mb_settings

    bpy.utils.unregister_class(VIEW3D_PT_mecabricks_tools)

    bpy.utils.unregister_class(AddonPreferences)

if __name__ == "__main__":
    register()
