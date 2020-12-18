from ..operators.shading import *
from ..icons.__init__ import *

def ui_template_shading_header(layout, data):
    row = layout.row()
    # Show panel
    text = data.name.upper()
    icon = 'REMOVE' if data.show_panel else 'ADD'
    row.prop(data, 'show_panel', text=text, icon=icon , toggle=True, emboss=False)
    # Reset to default values
    row.operator('mecafig.shading_reset', text='', icon='LOOP_BACK', emboss=False).layer = data.name

def ui_template_shading_base(context, layout):
    ob = context.active_object
    mat = ob.active_material
    data = mat.mecafig.base
    scene_data = context.scene.mecafig.shading.panels['Base']
    slider = False

    # Header
    ui_template_shading_header(layout, scene_data)

    # Body
    if scene_data.show_panel:
        col = layout.column()

        # Enable Dual Base
        base_id = '1'
        if ob.mecafig.geometry.name in ['Leg.L', 'Leg.R', 'Arm.L', 'Arm.R']:
            text = ('Dual Base %s' %('Enabled' if data.enable_dual_base else 'Disabled'))
            col.prop(data, 'enable_dual_base', text=text, toggle=True)
            # Base ID
            if data.enable_dual_base:
                col.row().prop(data, 'select_base', expand=True)
                base_id = data.select_base

        id_data = data.base_id[base_id]

        # Mecabricks Color Palette
        color_id = id_data.color_id
        text = get_id_text(color_id)
        icon = get_icon('ID_%s' % color_id)

        mcp = layout.box()
        row = mcp.row(align=True)
        row.alignment = 'LEFT'
        row.operator('mecabricks.color_palette', text=text, icon_value=icon, emboss=False)
        if color_id in ['50', '294']:
            col = layout.column(align=True)
            col.prop(id_data, 'emission')
            #col.prop(data.custom, 'emission_color', text='', slider=slider)

        # Custom Base
        layout.prop(id_data, 'enable_custom_base', text=('Custom Base %s' %('Enabled' if id_data.enable_custom_base else 'Disabled')), toggle=True)
        if id_data.enable_custom_base:
            mcp.enabled = False

            for prop in SHADING['Base']:
                id = ((' #%s' % base_id) if data.enable_dual_base else '')
                text = 'Base%s %s' %(id, prop.title().replace('_', ' '))
                text = (text if 'color' not in prop else '')
                if prop in ['color', 'metallic', 'transmission', 'paint_intensity', 'paint_color', 'paint_metallic']:
                    row = layout.row()
                    row.prop(id_data, prop, text=text, slider=slider)
                elif prop in ['subsurface', 'specular', 'emission', 'flatness_scale', 'granulosity_scale', 'glitter_amount', 'paint_specular', 'paint_scale']:
                    col = layout.column(align=True)
                    col.prop(id_data, prop, text=text, slider=slider)
                elif prop in ['granulosity_strength', 'glitter_scale']:
                    col.prop(id_data, prop, text=text, slider=slider)
                    layout.separator()
                else:
                    col.prop(id_data, prop, text=text, slider=slider)

        layout.prop(data, 'use_normal_map')
        layout.separator()

def ui_template_shading_map_field(layout, data, node):
    map = node.name

    row = layout.row(align=True)
    # Browse images
    row.operator('mecafig.shading_select_image', text='', icon='IMAGE_DATA').map = map
    if node.image is not None: # If image
        # Image name
        row.prop(node.image, 'name', text='')
        # Use Fake User
        row.prop(node.image, 'use_fake_user', text='')
        # Open image
        row.operator('mecafig.shading_open_image',text='', icon='FILEBROWSER').map = map
        # Unlink image
        row.operator('mecafig.shading_unlink_image', text='', icon='X').map = map
    else:
        # Open image
        row.operator('mecafig.shading_open_image', text='Open Image', icon='FILEBROWSER').map = map

def ui_template_shading_maps(context, layout):
    ob = context.active_object
    mat = ob.active_material
    nodes = get_nodes(mat)
    data = mat.mecafig.maps
    scene_data = context.scene.mecafig.shading.panels['Maps']
    slider = False

    if len(ob.data.uv_layers.values()) > 1:
        # Header
        ui_template_shading_header(layout, scene_data)

        # Body
        if scene_data.show_panel:
            # Enable Maps
            layout.prop(data, 'enable', text='Maps %s' %('Enabled' if data.enable else 'Disabled'), toggle=True)
            cmaps = layout.column()

            if data.enable:
                # Workflow
                cmaps.label(text='Workflow:')
                cmaps.row().prop(data, 'workflow', text='', expand=False)
                # UV Map
                uvm = cmaps.column()
                uvm.label(text='UV Map:')
                uvm.prop(data, 'uv_map', text='')
                # Maps
                for map in SHADING['Maps']:
                    map_data = data.maps[map]
                    node = nodes[map]
                    col = cmaps.column()

                    # Map Field
                    if data.workflow == 'COL_DAT':
                        if map == 'Decoration':
                            text = 'Color Map:'
                        elif map == 'Metalness':
                            text = 'Data Map:'
                    else:
                        text = '%s Map:' % map
                    col.label(text=text)
                    ui_template_shading_map_field(col, data, node)

                    # Map Settings
                    if node.image is not None:
                        for prop in SHADING['Maps'][map]:
                            if data.workflow == 'COL_DAT':
                                if map == 'Decoration':
                                    text = 'Color %s' % prop.title()
                                elif map == 'Metalness':
                                    text = 'Data %s' % prop.title()
                            else:
                                text = '%s %s' % (map, prop.title())
                            if prop == 'specular':
                                col = cmaps.column(align=True)
                                col.prop(map_data, prop, text=text, slider=slider)
                            elif prop == 'roughness':
                                col.prop(map_data, prop, text=text, slider=slider)
                            elif prop == 'strength':
                                if map == 'Decoration':
                                    if data.workflow == 'COL_DAT':
                                        row = cmaps.row()
                                        row.prop(map_data, prop, text=text, slider=slider)
                                elif map == 'Metalness':
                                    row = cmaps.row()
                                    row.prop(map_data, prop, text=text, slider=slider)
                            else:
                                row = cmaps.row()
                                row.prop(map_data, prop, text=text, slider=slider)

                layout.separator()

def ui_template_shading_wear(context, layout, data, wear):
    ob = context.active_object
    mat = ob.active_material
    nodes = get_nodes(mat)
    inputs = nodes[NODE].inputs
    data = data.wears[wear]
    slider = False

    for prop in SHADING['Wears'][wear]:
        input = '%s %s' %(wear, prop.title().replace('_', ' '))
        if input in inputs.keys():
            if prop in ['intensity', 'color', 'specular']:
                col = layout.column(align=True)
                text = (input if prop != 'color' else '')
                col.prop(data, prop, text=text, slider=slider)
            elif prop in ['amount', 'color_opacity', 'roughness']:
                col.prop(data, prop, text=input, slider=slider)
            else:
                row = layout.row()
                row.prop(data, prop, text=input, slider=slider)

    layout.separator()

def ui_template_shading_wears(context, layout):
    ob = context.active_object
    mat = ob.active_material
    data = mat.mecafig.wears
    scene_data = context.scene.mecafig.shading.panels['Wears']

    # Header
    ui_template_shading_header(layout, scene_data)

    # Body
    if scene_data.show_panel:
        layout.prop(data, 'enable', text=('Wears %s' %('Enabled' if data.enable else 'Disabled')), toggle=True)
        if data.enable:
            for wear in SHADING['Wears']:
                ui_template_shading_wear(context, layout, data, wear)

def ui_template_shading(context, layout, data):

    col = layout.column()
    # Apply Settings For
    col.row().prop(data, 'apply_settings_for', expand=True)
    # Copy Settings To
    if data.apply_settings_for == 'ACTIVE':
        row = col.row(align=True)
        row.operator('mecafig.copy_settings_to', text='Copy to Selected').copy_to = 'SELECTED'
        row.operator('mecafig.copy_settings_to', text='Copy to All').copy_to = 'ALL'

    layout.separator()

    # ### BASE ###
    ui_template_shading_base(context, layout)
    # ### MAPS ###
    ui_template_shading_maps(context, layout)
    # ### WEARS ###
    ui_template_shading_wears(context, layout)
