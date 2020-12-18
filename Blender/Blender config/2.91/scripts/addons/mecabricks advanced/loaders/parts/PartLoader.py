import bpy

from ..utils import make_matrix
from .MaterialBuilder import MaterialBuilder
from .JSONLoader import JSONLoader

class PartLoader:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, collection, library, bevel, local_list):
        self.collection = collection
        self.library = library
        self.bevel = bevel
        self.local_list = local_list

    # --------------------------------------------------------------------------
    # Load part
    # --------------------------------------------------------------------------
    def load(self, data):
        # Create object according to configuration type
        if data['type'] == 'custom':
            object = self.load_custom(data)
            pass
        elif data['type'] == 'solid':
            object = self.load_solid(data)

        # Update transform
        object.matrix_world = make_matrix(data['matrix'])

        # Update object pass
        object.pass_index = data['objectIndex']

        return object

    # --------------------------------------------------------------------------
    # Load solid part
    # --------------------------------------------------------------------------
    def load_solid(self, data):
        # Load configuration data
        configuration = self.library['configurations'][data['version']][data['configuration']]

        # Get mesh with material
        mesh = self.get_solid_mesh(data, configuration)

        # Create object using a copy of the configuration mesh
        object = bpy.data.objects.new('part', mesh)
        object.data = mesh

        # Add object to collection
        self.collection.objects.link(object)

        # Add subdivision modifiers for high lod
        if configuration['data']['name'] in self.local_list:
            # Select part object and make it active
            object.select_set(state=True)
            bpy.context.view_layer.objects.active = object

            # Add modifier
            bpy.ops.object.modifier_add(type='SUBSURF')
            bpy.context.active_object.modifiers['Subdivision'].levels = 1
            bpy.context.active_object.modifiers['Subdivision'].render_levels = 2

            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')

        return object

    # --------------------------------------------------------------------------
    # Get solid mesh
    # --------------------------------------------------------------------------
    def get_solid_mesh(self, data, configuration):
        # Create the entry for the part id if not available
        if data['id'] not in self.library['meshes'][data['scope']]:
            self.library['meshes'][data['scope']][data['id']] = {}

        # Material references
        mat_references = ','.join(str(x) for x in data['material']['base'])

        # Create material and mesh couple if not available
        if mat_references not in self.library['meshes'][data['scope']][data['id']]:
            # Create mesh
            mesh = configuration['mesh'].copy()

            # Create material
            material = configuration['material'].copy()
            material.name = self.get_material_name(data)

            # Upgrade material to include base and decoration
            material_builder = MaterialBuilder(self.library['textures'])
            material_builder.upgrade(material, data['material'], data['version'])

            # Append to material list
            self.library['materials'].append(material)

            # Append material to mesh
            mesh.materials.append(material)

            # Save mesh in library
            self.library['meshes'][data['scope']][data['id']][mat_references] = mesh

        return self.library['meshes'][data['scope']][data['id']][mat_references]

    # --------------------------------------------------------------------------
    # Load custom part
    # --------------------------------------------------------------------------
    def load_custom(self, data):
        # Create mesh data
        loader = JSONLoader(self.collection, self.bevel)
        mesh = loader.load(data['configuration'], data['geometry'], True)

        # Create the material entry for the part id if not available
        if data['id'] not in self.library['flex-materials']:
            self.library['flex-materials'][data['id']] = {}

        # Material references
        mat_references = ','.join(str(x) for x in data['material']['base'])

        # Create material if not available yet
        if mat_references not in self.library['flex-materials'][data['id']]:
            # Roughness
            roughness = []
            if data['material']['roughness'] is not None:
                roughness.append(data['material']['roughness'])

            # Create material
            material_builder = MaterialBuilder()
            material = material_builder.build(2, {
                'name': self.get_material_name(data),
                'bumps': [],
                'normals': [],
                'materials': [],
                'roughness': roughness
            })

            # Upgrade materials
            material_builder.upgrade(material, {
                'base': data['material']['base'],
                'decoration': None
            })

            # Save material in library
            self.library['flex-materials'][data['id']][mat_references] = material

            # Append to material list
            self.library['materials'].append(material)

        else:
            material = self.library['flex-materials'][data['id']][mat_references]

        # Append material to mesh
        mesh.materials.append(material)

        # Create object using a copy of the configuration mesh
        object = bpy.data.objects.new('part', mesh)
        object.data = mesh

        # Add object to collection
        self.collection.objects.link(object)

        return object

    # --------------------------------------------------------------------------
    # Get material name
    # --------------------------------------------------------------------------
    def get_material_name(self, data):
        name = 'mb:' + data['scope'][0] + ':' + str(data['id']) + ':'

        # Material reference
        reference = ','.join(str(x) for x in data['material']['base'])
        name += reference

        return name
