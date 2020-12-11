import bpy
import math
import os
import json
from zipfile import ZipFile

from .parts.ConfigurationLoader import ConfigurationLoader
from .parts.PartLoader import PartLoader
from .parts.TextureLoader import TextureLoader
from .parts.JSONLoader import JSONLoader

class SceneLoader:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, dir, logos, bevel, local_list):
        self.dir = dir
        self.logos = logos
        self.bevel = bevel
        self.local_list = local_list

        # Library
        self.library = {
            'configurations': {
                1: {},
                2: {}
            },
            'textures': {
                1: {
                    'decoration': {},
                    'bump': {},
                    'metalness': {}
                },
                2: {
                    'official': {
                        'normal': {},
                        'bump': {},
                        'mask': {},
                        'color': {},
                        'data': {}
                    },
                    'custom': {
                        'color': {},
                        'data': {}
                    }
                }
            },
            'shells': {
                1: {},
                2: {}
            },
            'meshes': {
                'official': {},
                'custom': {}
            },
            'flex-materials': {},
            'materials': [],
            'details': {}
        }

    # --------------------------------------------------------------------------
    # Load parts from model file
    # --------------------------------------------------------------------------
    def load(self, filepath, collection):
        # Save collection
        self.collection = collection;

        # Load nodes
        self.load_nodes();

        # Load json data contained in the scene file
        content = self.read_file(filepath)

        # Create detail meshes
        self.library['details'] = self.load_details(content['details'])

        # Load shells
        self.load_shells(content['geometries'])

        # Load custom textures
        self.load_textures(content['textures'])

        # Load configurations
        self.load_configurations(content['configurations'])

        # Load parts
        (empty, parts) = self.load_parts(content['parts'])

        return {
            'empty': empty,
            'parts': parts,
            'materials': self.library['materials']
        }

    # --------------------------------------------------------------------------
    # Load necessary nodes
    # --------------------------------------------------------------------------
    def load_nodes(self):
        if 'mb:nodes' in bpy.data.materials:
            return

        # Import materials from blend file
        path = os.path.join(self.dir, 'nodes.blend', 'Material')
        bpy.ops.wm.append(files=[{'name': 'mb:nodes'}], directory=path)

        bpy.data.materials['mb:nodes'].use_fake_user = True

    # --------------------------------------------------------------------------
    # Get file content
    # --------------------------------------------------------------------------
    def read_file(self, filepath):
        # Open zip file and read model file
        with ZipFile(filepath, 'r') as zip:
            data = zip.read('scene.mbx')

        return json.loads(data)

    # --------------------------------------------------------------------------
    # Get file content
    # --------------------------------------------------------------------------
    def load_details(self, data):
        details = {}

        loader = JSONLoader()

        for shape in data:
            details[shape] = {}

            for index in data[shape]:
                mesh_name = 'detail.' + shape + '.' + index
                details[shape][int(index)] = loader.load(mesh_name, data[shape][index])

        return details

    # --------------------------------------------------------------------------
    # Load shells
    # --------------------------------------------------------------------------
    def load_shells(self, geometries):
        loader = JSONLoader(self.collection, self.bevel)

        for version, version_lib in geometries.items():
            version = int(version)

            for filename, data in version_lib.items():
                # Create mesh data
                name = filename.replace('.json', '')
                mesh = loader.load(name, data)

                # Save in library
                self.library['shells'][version][filename] = mesh;

    # --------------------------------------------------------------------------
    # Load textures
    # --------------------------------------------------------------------------
    def load_textures(self, textures):
        loader = TextureLoader(self.dir)

        for version, version_lib in textures.items():
            version = int(version)

            # Version 1 textures
            if version == 1:
                for type, type_lib in version_lib.items():
                    # Check if the list is empty
                    if len(type_lib) == 0:
                        continue

                    for filename, image_base64 in type_lib.items():
                        color_space = 'sRGB' if type == 'decoration' else 'Non-Color'

                        image = loader.load(filename, colorspace=color_space, base64=image_base64)
                        self.library['textures'][1][type][filename] = image

            # Version 2 textures
            if version == 2:
                for scope, scope_lib in version_lib.items():
                    for type, type_lib in scope_lib.items():
                        # Check that the list is not empty
                        if len(scope_lib) == 0:
                            continue

                        for filename, image_base64 in type_lib.items():
                            color_space = 'sRGB' if type == 'color' else 'Non-Color'
                            image = loader.load(filename, colorspace=color_space, base64=image_base64)
                            self.library['textures'][2][scope][type][filename] = image

    # --------------------------------------------------------------------------
    # Load configurations
    # --------------------------------------------------------------------------
    def load_configurations(self, configurations):
        loader = ConfigurationLoader(self.collection, self.library, self.logos, self.local_list)

        for version, library in configurations.items():
            version = int(version)

            for name, configuration in library.items():
                # Complete configuration version 1
                if version == 1:
                    configuration['bumps'] = []
                    configuration['normals'] = []
                    configuration['roughness'] = []
                    configuration['materials'] = []

                self.library['configurations'][version][name] = loader.load(version, name, configuration)

    # --------------------------------------------------------------------------
    # Load parts
    # --------------------------------------------------------------------------
    def load_parts(self, parts):
        objects = []

        # Create empty
        empty = self.make_empty();

        # Add parts to the scene in the empty object
        loader = PartLoader(self.collection, self.library, self.bevel, self.local_list)
        for part in parts:
            # Create object
            object = loader.load(part)

            # Add object to empty
            object.parent = empty

            # Add object to part list
            objects.append(object)

        # Apply empty transform
        self.apply_transform(empty);

        return (empty, objects)

    # --------------------------------------------------------------------------
    # Create empty object that will contain all the scene objects
    # --------------------------------------------------------------------------
    def make_empty(self):
        empty = bpy.data.objects.new('empty', None)
        self.collection.objects.link(empty)

        empty.location = (0, 0, 0)
        empty.rotation_euler[0] = math.radians(90)
        empty.name = 'Empty'

        return empty

    # --------------------------------------------------------------------------
    # Apply object transform
    # --------------------------------------------------------------------------
    def apply_transform(self, object):
        # Select empty object and make it active
        bpy.ops.object.select_all(action='DESELECT')

        object.select_set(state=True)
        bpy.context.view_layer.objects.active = object

        # Apply transform to empty
        bpy.ops.object.transform_apply(location=True, rotation=True)
