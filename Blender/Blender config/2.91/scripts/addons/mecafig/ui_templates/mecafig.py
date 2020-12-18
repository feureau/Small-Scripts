import bpy

from ..operators.mecafig import get_mecafig
from ..icons.__init__ import get_icon

def ui_template_mecafig(context, layout):
    scene = context.scene
    ob = context.active_object
    data = scene.mecafig
    mf = get_mecafig(context)

    objects = []
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if not obj.mecafig.name == '':
                objects.append(obj)

    col = layout.column(align=True)
    
    # Info Box
    #if objects == []:
    #    box = col.box()
    #    bcol = box.column(align=True)
    #    bcol.label(text='Welcome on \'MecaFig\' !')
    #    bcol.label(text='First Try ? Let\'s start by adding a new Fig:')

    # ### MecaFig Field ###
    row = col.row(align=True)
    # Select (if available MecaFig)
    if not objects == []:
        row.prop(data, 'select', icon_only=True, icon_value=get_icon('MINIFIG_ON'))
    # Rename, Add & Delete (if selected MecaFig)
    if mf is not None:
        row.prop(data, 'name', text='')
        row.operator('mecafig.add_mecafig', text='', icon='ADD')
        row.operator('mecafig.add_mecafig_from_file', text='', icon='IMPORT')
        row.operator('mecafig.delete_mecafig', text='', icon='X')
    # Add (if No MecaFig)
    else:
        row.operator('mecafig.add_mecafig', icon='ADD')
        row.operator('mecafig.add_mecafig_from_file', icon='IMPORT')
