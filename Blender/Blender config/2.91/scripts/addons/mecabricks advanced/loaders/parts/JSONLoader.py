import bpy
import mathutils

class JSONLoader:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, collection = None, bevel = False):
        self.collection = collection
        self.bevel = bevel

    # --------------------------------------------------------------------------
    # Parse JSON geometry data
    # --------------------------------------------------------------------------
    def load(self, name, data, to_quads = False):
        # Get geometry data
        vertices = self.get_vertices(data['vertices'])
        face_data = self.get_face_data(data)

         # Create mesh
        mesh = self.make_mesh(name, vertices, face_data)

        # Convert to quads
        if to_quads:
            self.convert_to_quads(mesh)

        # Add bevels
        if self.bevel != False:
            self.add_bevel(mesh)

        # Rename uv layers
        for index, layer in enumerate(mesh.uv_layers):
            layer.name = 'uvmap' + str(index)

        return mesh

    # --------------------------------------------------------------------------
    # Vertices
    # --------------------------------------------------------------------------
    def get_vertices(self, data, chunk_size = 3):
        result = []
        chunk = []

        for i in range(len(data)):
            if i > 0 and i % chunk_size == 0:
                result.append(chunk)
                chunk = []

            chunk.append(data[i])

        result.append(chunk)

        return result

    # --------------------------------------------------------------------------
    # Face data
    # --------------------------------------------------------------------------
    def get_face_data(self, data):
        result = {
            'faces': [],
            'materials': [],
            'vertexUVs': [],
            'vertexNormals': [],

            'hasVertexNormals': False,
            'hasVertexUVs': False,
            'hasVertexColors': False,
            'hasFaceColors': False,
            'hasMaterials': False
        }

        # Extract raw data from json array
        faces = data.get('faces', [])
        normals = data.get('normals', [])
        colors = data.get('colors', [])

        offset = 0
        zLength = len(faces)

        nUvLayers = 0

        if 'uvs' in data:
            for layer in data['uvs']:
                if len(layer) > 0:
                    nUvLayers += 1
                    result['vertexUVs'].append([])

        # For each face
        while (offset < zLength):
            type = faces[offset]
            offset += 1

            isQuad = self.is_bit_set(type, 0)
            hasMaterial = self.is_bit_set(type, 1)
            hasFaceUv = self.is_bit_set(type, 2)
            hasFaceVertexUv = self.is_bit_set(type, 3)
            hasFaceNormal = self.is_bit_set(type, 4)
            hasFaceVertexNormal = self.is_bit_set(type, 5)
            hasFaceColor = self.is_bit_set(type, 6)
            hasFaceVertexColor = self.is_bit_set(type, 7)

            result['hasVertexUVs'] = result['hasVertexUVs'] or hasFaceVertexUv
            result['hasVertexNormals'] = result['hasVertexNormals'] or hasFaceVertexNormal
            result['hasVertexColors'] = result['hasVertexColors'] or hasFaceVertexColor
            result['hasFaceColors'] = result['hasFaceColors'] or hasFaceColor
            result['hasMaterials'] = result['hasMaterials'] or hasMaterial

            # vertices
            if isQuad:
                a = faces[offset]
                offset += 1

                b = faces[offset]
                offset += 1

                c = faces[offset]
                offset += 1

                d = faces[offset]
                offset += 1

                face = [a, b, c, d]

                nVertices = 4

            else:
                a = faces[offset]
                offset += 1

                b = faces[offset]
                offset += 1

                c = faces[offset]
                offset += 1

                face = [a, b, c]

                nVertices = 3

            result['faces'].append(face)

            # material
            if hasMaterial:
                materialIndex = faces[offset]
                offset += 1

            else:
                materialIndex = -1

            result['materials'].append(materialIndex)

            # uvs
            for i in range(nUvLayers):
                if hasFaceUv:
                    offset += 1

                if hasFaceVertexUv:
                    uvLayer = data['uvs'][i]

                    vertexUvs = []

                    for j in range(nVertices):
                        uvIndex = faces[offset]
                        offset += 1

                        u = uvLayer[uvIndex * 2]
                        v = uvLayer[uvIndex * 2 + 1]

                        vertexUvs.append([u, v])

                result['vertexUVs'][i].append(vertexUvs)

            if hasFaceNormal:
                offset += 1

            if hasFaceVertexNormal:
                vertexNormals = []

                for j in range(nVertices):
                    normalIndex = faces[offset]
                    offset += 1

                    x = data['normals'][normalIndex * 3]
                    y = data['normals'][normalIndex * 3 + 1]
                    z = data['normals'][normalIndex * 3 + 2]

                    vertexNormals.append([x, y, z])

                result['vertexNormals'].append(vertexNormals)

            if hasFaceColor:
                offset += 1

            if hasFaceVertexColor:
                for j in range(nVertices):
                    offset += 1

        return result

    # --------------------------------------------------------------------------
    # Check if bit is set
    # --------------------------------------------------------------------------
    def is_bit_set(self, value, position):
        return (value & (1 << position)) != 0

    # --------------------------------------------------------------------------
    # Create new mesh data
    # --------------------------------------------------------------------------
    def make_mesh(self, name, vertices, face_data):
        faces = face_data['faces']
        vertexUVs = face_data['vertexUVs']
        faceMaterials = face_data['materials']

        edges = []

        # Create a new mesh
        me = bpy.data.meshes.new(name)
        me.from_pydata(vertices, edges, faces)

        # Handle uvs
        if face_data['hasVertexUVs']:
            for li, layer in enumerate(vertexUVs):
                me.uv_layers.new()

                index = 0
                for fi in range(len(faces)):
                    if layer[fi]:
                        for vec in layer[fi]:
                            me.uv_layers[li].data[index].uv = mathutils.Vector((vec[0], vec[1]))

                            index += 1

        # Apply smooth shading
        #values = [True] * len(me.polygons)
        #me.polygons.foreach_set('use_smooth', values)

        # Load custom normals
        if face_data['hasVertexNormals']:
            normals = []
            for vertexNormals in face_data['vertexNormals']:
                for normal in vertexNormals:
                    normals.append(normal)

            me.normals_split_custom_set(normals)

        # Use auto smooth
        me.use_auto_smooth = True

        # Handle materials
        if face_data['hasMaterials']:
            for i, p in enumerate(me.polygons):
                p.material_index = faceMaterials[i]

        return me

    # --------------------------------------------------------------------------
    # Convert tris to quads
    # --------------------------------------------------------------------------
    def convert_to_quads(self, mesh):
        # Create object using mesh
        ob = bpy.data.objects.new('tempObject', mesh)
        ob.data = mesh

        # Add object to collection
        self.collection.objects.link(ob)

        # Select object and make it active
        ob.select_set(state=True)
        bpy.context.view_layer.objects.active = ob

        # Process mesh in Edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)

        # Select mesh
        bpy.ops.mesh.select_all(action = 'SELECT')

        # Convert tris to quads
        bpy.ops.mesh.tris_convert_to_quads(shape_threshold = 1.0472)

        # Exit edit model
        bpy.ops.object.mode_set(mode='OBJECT')

        # Remove part object
        bpy.data.objects.remove(ob)

    # --------------------------------------------------------------------------
    # Bevel mesh
    # --------------------------------------------------------------------------
    def add_bevel(self, mesh):
        # Create object using mesh
        ob = bpy.data.objects.new('tempObject', mesh)
        ob.data = mesh

        # Add object to collection
        self.collection.objects.link(ob)

        # Select object and make it active
        ob.select_set(state=True)
        bpy.context.view_layer.objects.active = ob

        # Process mesh in Edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)

        # Select mesh
        bpy.ops.mesh.select_all(action = 'SELECT')

        # Select boundary edges
        bpy.ops.mesh.region_to_loop()

        # Remove doubles
        bpy.ops.mesh.remove_doubles()

        # Mark bevel edges
        bpy.ops.transform.edge_bevelweight(value=1)

        # Exit edit model
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add Bevel modifier
        bpy.ops.object.modifier_add(type='BEVEL')
        bpy.context.active_object.modifiers["Bevel"].width = self.bevel['width']
        bpy.context.active_object.modifiers["Bevel"].segments = self.bevel['segments']
        bpy.context.active_object.modifiers["Bevel"].use_clamp_overlap = True
        bpy.context.active_object.modifiers["Bevel"].loop_slide = True
        bpy.context.active_object.modifiers["Bevel"].harden_normals = True
        bpy.context.active_object.modifiers["Bevel"].limit_method = 'WEIGHT'

        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = 3.141593

        # Apply modifier
        bpy.ops.object.convert(target='MESH')

        # Remove part object
        bpy.data.objects.remove(ob)
