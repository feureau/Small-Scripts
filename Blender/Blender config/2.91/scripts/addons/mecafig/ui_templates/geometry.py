from ..properties.geometry import *
from ..icons.__init__ import *

def ui_template_geometry_header(layout, data):
    ob = data.name
    OB = ob.upper().replace('.', '_')

    row = layout.row()
    # Show/Hide part
    row.prop(data, 'show_part', icon_value=(get_icon('MINIFIG_%s_OFF' % OB) if data.show_part else get_icon('MINIFIG_%s_ON' % OB)), text='', toggle=True, emboss=False)
    # Show/Hide sub-panel
    row.prop(data, 'show_panel', text=ob.upper(), icon=('REMOVE' if data.show_panel else 'ADD'), toggle=True, emboss=False)
    # Subsurf
    row.prop(data, 'enable_subsurf_viewport', text='', icon=('RESTRICT_VIEW_OFF' if data.enable_subsurf_viewport else 'RESTRICT_VIEW_ON'), toggle=True, emboss=False)
    row.prop(data, 'enable_subsurf_render', text='', icon=('RESTRICT_RENDER_OFF' if data.enable_subsurf_render else 'RESTRICT_RENDER_ON'), toggle=True, emboss=False)

def ui_template_geometry_sub_panel(context, layout, part):
    data = None
    mf = get_mecafig(context)

    for ch in mf.children:
        if ch.type == 'MESH':
            if ch.mecafig.geometry.name == part:
                data = ch.mecafig.geometry

    ui_template_geometry_header(layout, data)

    if data.show_panel:
        # Mesh
        if part in ['Leg.L', 'Leg.R', 'Body', 'Head']:
            row = layout.row()
            row.label(text='Mesh:')
            row.prop(data, 'mesh', text='')
        # Subsurf
        col = layout.column(align=True)
        #col.label(text='Subsurf:')
        col.prop(data, 'subsurf_levels_viewport', text='Subsurf Viewport')
        col.prop(data, 'subsurf_levels_render', text='Subsurf Render')

        layout.separator()

def ui_template_geometry(context, layout):

    PARTS = [part for part in MECAFIG]
    for part in reversed(PARTS):
        ui_template_geometry_sub_panel(context, layout, part)
