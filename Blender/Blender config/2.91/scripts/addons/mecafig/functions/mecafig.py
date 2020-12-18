import os
import bpy
import zipfile
import re
import xml.etree.ElementTree as ET
import base64

from .shading import *
from ..utils import *

def get_mecafig(context):
    ob = context.active_object
    childs = []
    mecafig = []

    if ob is not None:
        if ob.type == 'ARMATURE':
            if not ob.mecafig.name == '':
                return ob
                #mecafig.append(ob)
        elif ob.type == 'MESH':
            if ob.mecafig.geometry.name in MECAFIG:
                if ob.parent:
                    if ob.parent.type == 'ARMATURE':
                        if not ob.parent.mecafig.name == '':
                            return ob.parent
                            #mecafig.append(ob.parent)
        else:
            return None
    else:
        return None

#    for child in mecafig.children:
#        if child.type == 'MESH':
#            if child.mecafig.name in MECAFIG:
#                childs.append(child)
#
#    mecafig.append(childs)
#
#    return mecafig

def set_scene_properties(context):
    scene = context.scene
    scene_data = scene.mecafig.shading.panels
    for elem in SHADING:
        if not elem in scene_data.keys():
            new_elem = scene_data.add()
            new_elem.name = elem

            if elem == 'Base':
                scene_data[elem].show_panel = True

    return {'FINISHED'}

def set_armature_properties(object):
    if object.type == 'ARMATURE':
        data = object.mecafig.armature
        parts_data = data.parts
        for part in MECAFIG:
            if not part in parts_data.keys():
                new_part = parts_data.add()
                new_part.name = part

    return {'FINISHED'}

def select_mecafig(context, name):
    ob = context.active_object
    mecafig = None
    pose_flag = False

    if ob:
        if ob.mode == 'POSE':
            pose_flag = True
            bpy.ops.object.posemode_toggle()
        elif ob.mode == 'EDIT':
            bpy.ops.object.editmode_toggle()

    bpy.ops.object.select_all(action='DESELECT')

    for object in bpy.data.objects:
        if object.type == 'ARMATURE':
            if object.mecafig.name == name:
                object.select_set(True)
                context.view_layer.objects.active = object
                mecafig = object
                if pose_flag:
                    bpy.ops.object.posemode_toggle()

    # Focus on selected MecaFig
    for area in context.screen.areas:
        if area.type == 'VIEW_3D' and area.spaces[0].region_3d.view_perspective != 'CAMERA':
            ctx = context.copy()
            ctx['area'] = area
            ctx['region'] = area.regions[-1]
            bpy.ops.view3d.view_selected(ctx)

    return mecafig

def set_mecafig_name(context, name):
    ob = get_mecafig(context)
    ob_name = ob.mecafig.name
    # Get MecaFigs name in the Scene
    mf_names = []
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if not obj.mecafig.name == '':
                mf_name = obj.mecafig.name
                if mf_name not in mf_names:
                    mf_names.append(mf_name)
    # Check name
    if not name == '':
        if name == ob_name:
            new_name = ob_name
        elif name in mf_names:
            i = 2
            new_name = '%s_%s' %(name, i)
            while new_name in mf_names:
                i += 1
                new_name = '%s_%s' %(name, i)
        else:
            new_name = name
    else:
        new_name = ob_name
    # Rename
    ob.name = new_name
    ob.data.name = '%s_Rig' % new_name
    ob.mecafig.name = new_name
    for child in ob.children:
        for part in MECAFIG:
            if child.mecafig.geometry.name == part:
                ch_name = '%s_%s' %(new_name, part)
                child.name = ch_name
                child.mecafig.name = new_name
                if child.active_material:
                    mat = child.active_material
                    mat.name = ch_name
                    mat.mecafig.name = new_name
    if ob.users_collection:
        col = ob.users_collection[0]
        col.name = new_name

    return new_name

def add_mecafig(context):
    blend_dir = ADDON_DIR + '/files/mecafig.blend'
    ob = context.active_object

    # Set 3D View Mode to 'OBJECT'
    if ob:
        if ob.mode == 'POSE':
            bpy.ops.object.posemode_toggle()
        elif ob.mode == 'EDIT':
            bpy.ops.object.editmode_toggle()

    # Get MecaFigs name in the Scene
    mf_names = []
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if not obj.mecafig.name == '':
                mf_name = obj.mecafig.name
                if mf_name not in mf_names:
                    mf_names.append(mf_name)
    # Get new MecaFig name
    i = 1
    name = 'MecaFig_%s' % i
    while name in mf_names:
        i += 1
        name = 'MecaFig_%s' % i

    # Import MecaFig
    file = COLLECTION
    bpy.ops.wm.append(directory=blend_dir + '/Collection/', filename=file)

    # Set active object
    objects = context.selected_objects
    parent = None
    childs = []
    trash = []

    bpy.ops.object.select_all(action='DESELECT')

    for object in objects:
        if object.type == 'ARMATURE':
            object.select_set(True)
            context.view_layer.objects.active = object
            parent = object

            for child in object.children:
                if child.mecafig.geometry.name in MECAFIG:
                    childs.append(child)

    for child in childs:
        for part in MECAFIG:
            if child.mecafig.geometry.name == part:

                # Mesh
                if not child.data.name in MECAFIG[part]['meshes']:
                    ch_data = child.data
                    ch_data_name = ch_data.name.split('.')[0]
                    for mesh in MECAFIG[part]['meshes']:
                        if ch_data_name == mesh:
                            if mesh in bpy.data.meshes.keys():
                                child.data = bpy.data.meshes[mesh]
                                if not ch_data in trash:
                                    trash.append(ch_data)

                # Material
                if not MATERIAL in bpy.data.materials.keys():
                    # Import material
                    dir = blend_dir + '/Material/'
                    bpy.ops.wm.append(directory=dir, filename=MATERIAL)

                bpy.data.materials[MATERIAL].use_fake_user = True

                child.active_material = bpy.data.materials[MATERIAL].copy()
                mat = child.active_material
                nodes = mat.node_tree.nodes

                # UV Maps
                uv_maps = MECAFIG[part]['uv_maps']
                if not uv_maps == []:
                    nodes['UV Maps'].uv_map = uv_maps[-1]

                # Base Map
                if part in ['Leg.L', 'Leg.R', 'Arm.L', 'Arm.R']:
                    if part.startswith('Leg'):
                        b_part = 'leg'
                    elif part.startswith('Arm'):
                        b_part = 'arm'
                    b_dir = ADDON_DIR + '/files/textures'
                    b_map = get_image(('%s_base.png' % b_part), b_dir)
                    nodes['UV Base'].uv_map = 'Base'
                    set_image(mat, 'Base', b_map, 'Non-Color', False)

                # Normal Map
                n_dir = ADDON_DIR + '/files/textures'
                n_map = '%s_normal.png' % child.data.name.split('.')[0]
                n_map = get_image(n_map, n_dir)
                set_image(mat, 'Normal', n_map, 'Non-Color', True)

                # Set Material Scale
                scale = MECAFIG[part]['uv_scale']
                nodes[NODE].inputs['UV Scale'].default_value = scale

                #set_shading_properties(child, part)

    for mesh in trash:
        bpy.data.meshes.remove(mesh)
    # Scale MecaFig by default to 10
    parent.mecafig.armature.scale = 10
    # Name MecaFig
    context.scene.mecafig.name = name
    # Set scene properties
    set_scene_properties(context)

    return select_mecafig(context, name)

def delete_mecafig(context):
    ob = context.active_object
    arm_list = []
    mesh_list = []
    lat_list = []
    mat_list = []

    if not ob.type == 'ARMATURE':
        ob = ob.parent

    if not ob.mecafig.name == '':
        arm_list.append(ob.data)
        col = ob.users_collection[0]
        for child in ob.children:
            if child.type == 'MESH':
                if child.data not in mesh_list:
                    mesh_list.append(child.data)
            elif child.type == 'LATTICE':
                lat_list.append(child.data)
            if child.active_material:
                mat_list.append(child.active_material)
            bpy.data.objects.remove(child)
        bpy.data.objects.remove(ob)
        bpy.data.collections.remove(col)

    bpy.data.armatures.remove(arm_list[0])

    for mesh in mesh_list:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    for lat in lat_list:
        if lat.users == 0:
            bpy.data.lattices.remove(lat)

    for mat in mat_list:
        bpy.data.materials.remove(mat)

    bpy.ops.object.select_all(action='DESELECT')

    return{'FINISHED'}

def extract_zipfile(filepath):
    file = ''
    extensions = ['.dae', '.mbx']
    # ZIP
    if zipfile.is_zipfile(filepath): # If True
        # Open .zip file
        with zipfile.ZipFile(filepath, 'r') as zip:
            # Variables
            zip_files = zip.namelist()
            zip_files_count = len(zip_files)
            #
            if zip_files_count > 0:
                # Read 'zip' files
                for zip_file in zip_files:
                    for ext in extensions:
                        if zip_file.endswith(ext):
                            file = zip_file
                    # Extract
                    zip.extract(zip_file, os.path.dirname(filepath))

    return file

def extract_from_collada(self, context, filepath, collada_file):
    exp = True
    filepath = os.path.dirname(filepath) + '/' + collada_file
    objects = {}

    if exp:
        tree = ET.parse(filepath) # Parse XML file
        root = tree.getroot() # Get ROOT

        for part in MECAFIG:
            objects[part] = []
            meshes = MECAFIG[part]['meshes']
            for child in root:
                if 'library_visual_scenes' in child.tag:
                    for node in child[0]:
                        matrix = []
                        for elem in node:
                            if 'matrix' in elem.tag:
                                matrix = elem.text.split()
                            if 'instance_geometry' in elem.tag:
                                mesh_name = elem.attrib['url'].replace('#', '').split('-')[0]
                                for mesh in meshes:
                                    r = r'%s(uv|UV)?\d?' % mesh
                                    if re.fullmatch(r, mesh_name):
                                        mat = elem[0][0][0].attrib['symbol'].split('-')[0].split(':')
                                        mat_list = [[mat[0]], mat[1], mat[3]]

                                        object = [mesh_name, matrix, mat_list, 1]
                                        objects[part].append(object)

    else:
        # Import Collada file
        bpy.ops.object.select_all(action = 'DESELECT')
        bpy.ops.wm.collada_import(filepath = filepath)
        # Get objects
        objects = [ob for ob in context.selected_objects]

        for part in MECAFIG:
            for ob in objects:
                mesh_name = ob.data.name.split('.')[0]
                for mesh in MECAFIG[part]['meshes']:
                    r = r'%s(uv|UV)?\d?' % mesh
                    if re.fullmatch(r, mesh_name):
                        mat_name = ob.active_material.name.split('.')[0].split(':')
                        mat_list = [mat_name[0], mat_name[1], mat_name[3]]

                        settings[part] = [mesh_name, mat_list]

        # Remove objects
        mesh_list = []
        mat_list = []

        for ob in objects:
            if ob.data not in mesh_list:
                mesh_list.append(ob.data)
            if ob.active_material not in mat_list:
                mat_list.append(ob.active_material)
            bpy.data.objects.remove(ob)

        for mesh in mesh_list:
            bpy.data.meshes.remove(mesh)

        for mat in mat_list:
            bpy.data.materials.remove(mat)

    return objects

def extract_from_zmbx(self, context, filepath, zmbx_file):
    ob_dict = {}
    file_path = os.path.dirname(filepath)
    debug = False

    def decode_image(image_string, filepath, image_name):
        data = bytes(image_string, 'utf-8')
        name = image_name + '.png'

        with open(filepath + name, 'wb') as image:
            image.write(base64.decodebytes(data))

        return image

    # Set .zmbx file as a variable
    filepath = os.path.dirname(filepath) + '/' + zmbx_file
    with open(filepath, 'r') as f:
        scene = eval(f.read().replace('null', 'None').replace('false', 'False').replace('true', 'True'))

    # ZMBX Version [2.0.0]
    if 'metadata' in scene:
        objects = scene['parts']
        textures = scene['textures']

        for part in MECAFIG:

            if debug:
                print(part)
                i = 0

            ob_dict[part] = []
            for ob in objects:
                config = ob['configuration']
                # Check if this object is a MiniFig part
                for mesh in MECAFIG[part]['meshes']:
                    r = r'%s(uv|UV)?\d?' % mesh # Regex
                    mesh_name = config.split('.')[0]

                    if re.fullmatch(r, mesh_name):
                        version = ob['version']
                        scope = ob['scope']
                        matrix = ob['matrix']
                        material = ob['material']
                        images = textures[str(version)]

                        # ### Material ###
                        mat_list = []

                        # Base
                        base = material['base']
                        mat_list.append(base)

                        # ### Maps ###
                        maps = material['decoration']

                        # UV Map
                        if 'uv' in maps:
                            uv = maps['uv']
                            uv_map = '%s%s' %(config, ('uv%s' %('' if uv == 1 else str(uv))))
                        else:
                            uv_map = config.split('.')[0]

                        # Decoration / Color
                        if version == 1:
                            map = 'decoration'
                        else:
                            map = 'color'

                        if map in maps:
                            dec = maps[map]
                            dec_name = dec['name'].split('.')[0]
                            if version == 1:
                                dec_images = images[map]
                                dec_path = file_path + '/maps/diffuse/'
                            else:
                                dec_images = images[scope][map]
                                dec_path = file_path + '/maps/color/'
                            dec_image = dec_images[dec['name']]
                            # Check if path exists
                            if not os.path.exists(dec_path):
                                os.makedirs(dec_path)
                            # Create image
                            decode_image(dec_image, dec_path, dec_name)

                            mat_list.append(dec_name)
                        else:
                            mat_list.append('')

                        # Metalness / Data
                        if version == 1:
                            map = 'metalness'
                        else:
                            map = 'data'

                        if map in maps:
                            met = maps[map]
                            met_name = met['name'].split('.')[0] + '_data'
                            if version == 1:
                                met_images = images[map]
                                met_path = file_path + '/maps/metalness/'
                            else:
                                met_images = images[scope][map]
                                met_path = file_path + '/maps/data/'
                            met_image = met_images[met['name']]
                            # Check if path exists
                            if not os.path.exists(met_path):
                                os.makedirs(met_path)
                            # Create image
                            decode_image(met_image, met_path, met_name)

                            mat_list.append(met_name)
                        else:
                            mat_list.append('')

                        ob_list = [uv_map, matrix, mat_list, version]
                        ob_dict[part].append(ob_list)

                        if debug:
                            i += 1
                            print(i, ob_list)

        return ob_dict

    # ZMBX Version 1
    else:
        objects = scene[0]
        materials = scene[2]
        images = scene[3]
        mesh_names = scene[5]

        for part in MECAFIG:
            ob_dict[part] = []
            for ob in objects:
                mesh_id = ob[0]
                mesh_name = mesh_names[mesh_id]
                for mesh in MECAFIG[part]['meshes']:
                    r = r'%s(uv|UV)?\d?' % mesh
                    if re.fullmatch(r, mesh_name):
                        # Matrix
                        matrix = ob[1]

                        # Material
                        mat_id = ob[2][0]
                        mat = materials[mat_id]
                        mat_list = []

                        # Color ID
                        color_id = [str(mat[0])]
                        mat_list.append(color_id)

                        # Decoration Map
                        d_map_id = mat[2]
                        if d_map_id is None:
                            mat_list.append('')
                        else:
                            d_images = images[1]
                            d_map_str = d_images[d_map_id]
                            d_fp = os.path.dirname(filepath) + '/maps/diffuse/'
                            if not os.path.exists(d_fp):
                                os.makedirs(d_fp)
                            d_map_name = '%smb%s' %(mesh, ob[3])
                            decode_image(d_map_str, d_fp, d_map_name)

                            mat_list.append(d_map_name)

                        # Metalness Map
                        m_map_id = mat[4]
                        if m_map_id is None:
                            mat_list.append('')
                        else:
                            m_images = images[2]
                            m_map_str = m_images[m_map_id]
                            m_fp = os.path.dirname(filepath) + '/maps/metalness/'
                            if not os.path.exists(m_fp):
                                os.makedirs(m_fp)
                            m_map_name = '%smb%s_metal' %(mesh, ob[3])
                            decode_image(m_map_str, m_fp, m_map_name)

                            mat_list.append(m_map_name)

                        ob_dict[part].append([mesh_name, matrix, mat_list, 1])

        return ob_dict

def parse_objects(objects):
    debug = False
    figs = {}
    thd = [1, 2.6, 1]
    vecs = {
        'Leg.L': [[4, 11.2, 0]],
        'Leg.R': [[-4, 11.2, 0]],
        'Hip': [[0, 16, 0]],
        'Body': [[0, 16, 0]],
        'Arm.L': [[6.265, 24.99, 0]],
        'Arm.R': [[-6.265, 24.99, 0]],
        'Hand.L': [[8.265, 19.646,10.988], [8.255, 13.345, 5.35]],
        'Hand.R': [[-8.265, 19.646,10.988], [-8.255, 13.345, 5.35]],
        'Head': [[0, 28.8, 0]]
    }

    def compare_matrix(from_matrix, vector, to_matrix, threshold, debug):
        f_mx = from_matrix
        t_mx = to_matrix
        thd = threshold
        true = 0

        # For X, Y & Z
        for i in range(0, 3):
            j = i * 4
            # Define Min & Max
            min = max = float(f_mx[j + 3])
            for k in range(0, 3):
                min += (float(f_mx[j + k]) * vector[k])
                max += (float(f_mx[j + k]) * vector[k])
            # Compare Value with Min & Max
            min = round(min, 2) - thd[i]
            max = round(max, 2) + thd[i]
            value = round(float(t_mx[j + 3]), 2)
            if min <= value <= max or max <= value <= min:
                true += 1
            # Debug
            if debug:
                print(i, true, min, value, max)
        # Return comparison result
        if true == 3:
            return True
        else:
            return False

    for i, hip in enumerate(objects['Hip']):
        figs[i] = {}

        for part in MECAFIG:
            bool = False
            # Debug
            if debug:
                print(part)

            if part == 'Hip':
                figs[i][part] = hip
                # Debug
                if debug:
                    print(hip)
            else:
                for vec in vecs[part]:
                    if part in ['Arm.L', 'Arm.R', 'Head']:
                        if 'Body' in figs[i]:
                            f_mx = figs[i]['Body'][1]
                            v = [i - j for i, j in zip(vec, vecs['Body'][0])]
                            t = thd
                        else:
                            break
                    elif part == 'Hand.L':
                        if 'Arm.L' in figs[i]:
                            f_mx = figs[i]['Arm.L'][1]
                            v = [i - j for i, j in zip(vec, vecs['Arm.L'][0])]
                            t = [i + j for i, j in zip(thd, [2.1, 4.2, 2.7])]
                        else:
                            break
                    elif part == 'Hand.R':
                        if 'Arm.R' in figs[i]:
                            f_mx = figs[i]['Arm.R'][1]
                            v = [i - j for i, j in zip(vec, vecs['Arm.R'][0])]
                            t = [i + j for i, j in zip(thd, [2.1, 4.2, 2.7])]
                        else:
                            break
                    else:
                        f_mx = hip[1]
                        v = [i - j for i, j in zip(vec, vecs['Hip'][0])]
                        t = thd

                    for elem in objects[part]:
                        t_mx = elem[1] # elem [Matrix]
                        bool = compare_matrix(f_mx, v, t_mx, t, debug)
                        if bool:
                            figs[i][part] = elem
                            # Debug
                            if debug:
                                print(elem)

                            if part in ['Hand.L', 'Hand.R']:
                                for p in ['Hand.L', 'Hand.R']:
                                    objects[p].remove(elem)
                            else:
                                objects[part].remove(elem)
                            break
                    if bool:
                        break

    return figs

def add_mecafig_from_file(self, context, filepath, count):
    scene = context.scene
    asf = scene.mecafig.shading.apply_settings_for

    # Get / Set 'Apply Settings For'
    if not asf == 'ACTIVE':
        get_asf = asf
        scene.mecafig.shading.apply_settings_for = 'ACTIVE'
    else:
        get_asf = 'ACTIVE'

    # Extract file from ZIP
    file = extract_zipfile(filepath)
    file_name = os.path.basename(filepath).split('.')[0]
    figs = {}

    if file.endswith('.dae'):
        figs = extract_from_collada(self, context, filepath, file)
    elif file.endswith('.mbx'):
        figs = extract_from_zmbx(self, context, filepath, file)

    # Parse MiniFig(s)
    figs = parse_objects(figs)

    # For each MiniFig
    for i in figs:
        # Add MecaFig
        mecafig = add_mecafig(context)
        mecafig.location[0] += count * 40
        mecafig.location[1] += i * 40

        for part in MECAFIG:
            for ob in mecafig.children:
                ob_data = ob.mecafig
                if ob_data.geometry.name == part:
                    # Set object as active
                    bpy.ops.object.select_all(action='DESELECT')
                    ob.select_set(True)
                    context.view_layer.objects.active = ob

                    if part in figs[i]:
                        # Set Mesh
                        if part in ['Leg.L', 'Leg.R', 'Body', 'Head']:
                            ob_mesh = figs[i][part][0]
                            for mesh in MECAFIG[part]['meshes']:
                                if mesh in ob_mesh:
                                    ob_data.geometry.mesh = mesh
                        # Set Material
                        ob_mat = ob.active_material
                        ob_fig = figs[i][part]

                        set_shading(ob_mat, ob_fig, filepath)
        # Rename New MecaFig
        context.scene.mecafig.name = file_name
    # Set 'Apply Setting For'
    scene.mecafig.shading.apply_settings_for = get_asf

    return {'FINISHED'}
