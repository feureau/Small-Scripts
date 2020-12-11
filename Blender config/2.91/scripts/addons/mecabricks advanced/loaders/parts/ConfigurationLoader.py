import bpy
import mathutils
import math
import os
import json
import urllib.parse

from .MaterialBuilder import MaterialBuilder
from .JSONLoader import JSONLoader

class ConfigurationLoader:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, collection, library, logos, local_list):
        self.collection = collection
        self.library = library
        self.logos = logos
        self.local_list = local_list

    # --------------------------------------------------------------------------
    # Load data and create mesh and base material
    # --------------------------------------------------------------------------
    def load(self, version, name, data):
        # Update configuration bump textures if local part
        if name in self.local_list:
            for bump in data['bumps']:
                if bump['file'] in self.local_list[name]['bumps']:
                    bump['filepath'] = self.local_list[name]['bumps'][bump['file']]

        # Build base material
        material_builder = MaterialBuilder(self.library['textures'])
        material = material_builder.build(version, data)

        # Check if mesh shall be loaded locally
        mesh = None
        if name in self.local_list:
            mesh = self.load_local_mesh(name)

        # Import standard mesh if needed
        if mesh is None:
            # Get shell
            shell = self.library['shells'][version][data['geometry']['file']]

            # Merge logos, studs, pins and tubes
            mesh = self.add_details(shell, data['geometry']['extras'])

        return {'data': data, 'mesh': mesh, 'material': material}

        return 1

    # --------------------------------------------------------------------------
    # Add detail geometry
    # --------------------------------------------------------------------------
    def add_details(self, shell, data):
        # Collection used by temporary operations
        temp = self.collection

        # Create a temporation shell object
        object = bpy.data.objects.new('shell', shell)
        object.data = shell

        # Count uv layers
        countUvLayers = len(shell.uv_layers)

        # Add object to temp collection
        temp.objects.link(object)

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Select part object and make it active
        object.select_set(state = True)
        bpy.context.view_layer.objects.active = object

        # Add main type of detail elements
        element_types = ['knobs', 'pins', 'tubes']

        # Add logos is requested
        if self.logos:
            element_types.append('logos')

        for element_type in element_types:
            # Process each element of the type
            for element in data[element_type]:
                # Duplicate base detail element mesh
                if element['type'] not in self.library['details'][element_type]:
                    continue

                detail = self.library['details'][element_type][element['type']].copy()

                # Update uv layers
                if countUvLayers > 1:
                    for i in range(1, countUvLayers):
                        detail.uv_layers.new(name = 'uvmap' + str(i))

                # Create detail object
                detail_object = bpy.data.objects.new('detail', detail)
                detail_object.data = detail

                # Apply transform
                mat_loc = mathutils.Matrix.Translation(element['transform']['position'])

                # Quaternion order in Blender is w, x, y, z
                # Order exported from Mecabricks is x, y, z, w
                qMB = element['transform']['quaternion']
                qBL = [qMB[3], qMB[0], qMB[1], qMB[2]]

                quaternion = mathutils.Quaternion(qBL)
                mat_rot = quaternion.to_matrix().to_4x4()

                detail_object.matrix_world = mat_loc @ mat_rot

                # Add object to collection
                temp.objects.link(detail_object)

                # Select detail object
                # To ensure custom split normals are kept, the active
                # object shall include custom split normals
                detail_object.select_set(state = True)
                bpy.context.view_layer.objects.active =detail_object

        # Merge logos with part
        bpy.ops.object.join()

        # Apply transform to object
        bpy.ops.object.transform_apply(location = True)

        # Mesh
        mesh = bpy.context.object.data

        # Remove active object
        bpy.data.objects.remove(bpy.context.object)

        # Rename
        mesh.name = shell.name

        return mesh

    # --------------------------------------------------------------------------
    # Load local mesh
    # --------------------------------------------------------------------------
    def load_local_mesh(self, name):
        # Get local mesh
        blendpath = self.local_list[name]['path']

        # Check that file exists
        if os.path.isfile(blendpath) == False:
            return None

        # List of meshes before importing
        before = [f.name for f in bpy.data.meshes]

        # Import mesh
        mesh_dir = os.path.join(blendpath, 'Mesh')
        bpy.ops.wm.append(directory=mesh_dir, files=[{'name': name}])

        # List of meshes after importing
        after = [f.name for f in bpy.data.meshes]

        # Retrieve the mesh imported
        meshes = list(set(after) - set(before))
        mesh = bpy.data.meshes[meshes[0]] if len(meshes) > 0 else None

        return mesh
