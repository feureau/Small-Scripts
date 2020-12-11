import bpy

from ..functions.geometry import *

def get_show_part(self):
    ob = self.id_data
    return ob.hide_viewport

def set_show_part(self, value):
    ob = self.id_data
    ob.hide_viewport = value

def enum_items_mesh(self, context):
    part = self.name
    enum_items = []

    for elem in MECAFIG[part]['meshes']:
        item = (elem, elem, '')

        enum_items.append(item)

    return enum_items

def update_mesh(self, context):
    ob = self.id_data
    mesh_name = self.mesh
    # Mesh
    if not mesh_name in bpy.data.meshes.keys():
        blend_dir = ADDON_DIR + '/files/mecafig.blend'
        m_dir = blend_dir + '/Mesh/'
        file = mesh_name

        bpy.ops.wm.append(directory=m_dir, filename=file)
        mesh = bpy.data.meshes[mesh_name]
    else:
        mesh = bpy.data.meshes[mesh_name]

    ob.data = mesh
    # Normal Map
    mat = ob.active_material
    n_map = '%s_normal.png' % mesh_name
    n_dir = ADDON_DIR + '/files/textures/'
    set_image_texture(mat, 'Normal', n_dir, n_map, 'Non-Color')

def get_enable_subsurf_viewport(self):
    ob = self.id_data
    return ob.modifiers['Subdivision'].show_viewport

def set_enable_subsurf_viewport(self, value):
    ob = self.id_data
    ob.modifiers['Subdivision'].show_viewport = value

def get_enable_subsurf_render(self):
    ob = self.id_data
    return ob.modifiers['Subdivision'].show_render

def set_enable_subsurf_render(self, value):
    ob = self.id_data
    ob.modifiers['Subdivision'].show_render = value

def get_subsurf_levels_viewport(self):
    ob = self.id_data
    return ob.modifiers['Subdivision'].levels

def set_subsurf_levels_viewport(self, value):
    ob = self.id_data
    ob.modifiers['Subdivision'].levels = value

def get_subsurf_levels_render(self):
    ob = self.id_data
    return ob.modifiers['Subdivision'].render_levels

def set_subsurf_levels_render(self, value):
    ob = self.id_data
    ob.modifiers['Subdivision'].render_levels = value
