from ..functions.mecafig import *

def get_name(self):
    ob = bpy.context.active_object

    if ob.type == 'ARMATURE' and not ob.mecafig.name == '':
        return ob.mecafig.name
    elif ob.type == 'MESH':
        if ob.parent.type == 'ARMATURE' and not ob.parent.mecafig.name == '':
            return ob.parent.mecafig.name
    else:
        return ''

def set_name(self, value):
    set_mecafig_name(bpy.context, value)

def enum_items_select(self, context):
    items = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE']

    enum_items = []
    for elem in items:
        if not elem.mecafig.name == '':
            elem = elem.mecafig.name
            item = (elem, elem, '')
            enum_items.append(item)

    return enum_items

def update_select(self, context):
    select_mecafig(context, self.select)
