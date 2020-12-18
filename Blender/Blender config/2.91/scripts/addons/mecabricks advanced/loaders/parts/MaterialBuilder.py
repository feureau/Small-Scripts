import bpy
import os

from .nodes.TextureNode import TextureNode
from .nodes.RoughnessLayer import RoughnessLayer
from .materials import materials

class MaterialBuilder:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, textures = {}):
        self.textures = textures
        self.eevee_params = ['Color', 'Subsurface', 'Metallic', 'Roughness', 'Transmission', 'Normal', 'Height']

    # --------------------------------------------------------------------------
    # build material
    # --------------------------------------------------------------------------
    def build(self, version, data):
        # Create new material
        material = bpy.data.materials.new(data['name'])
        material.use_nodes = True

        # Nodes and links
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Delete the content of the material
        nodes.clear()

        # Scale value node
        scale = nodes.new('ShaderNodeValue')
        scale.location = (-1000, 0)
        scale.outputs[0].default_value = 1
        scale.label = 'Scale'

        # Assemble normals coming from all available sources
        normal = self.assemble_normals(material, data['normals'], data['bumps'], data['roughness'])
        normal.location = (-800, 0)
        normal.label = 'Normal'

        links.new(scale.outputs[0], normal.inputs[1])

        # Set bevel value
        # Default is 0.35mm but for part version 2, if no bevel texture is
        # specified, it means that value shall be 0
        bevel_size = 0.35

        if version == 2:
            has_bevel = False
            for item in data['normals']:
                if 'bevel' not in item or item['bevel'] is True:
                    has_bevel = True
                    break

            bevel_size = bevel_size if has_bevel else 0

        normal.inputs[0].default_value = bevel_size

        # Add customization group
        customize = material.node_tree.nodes.new('ShaderNodeGroup')
        customize.node_tree = bpy.data.node_groups['mb_customization']
        customize.location = (-600, 0)
        customize.label = 'Customize'

        links.new(scale.outputs[0], customize.inputs['Scale'])
        links.new(normal.outputs['Normal'], customize.inputs['Normal'])
        links.new(normal.outputs['Height'], customize.inputs['Height'])

        # Create shader mixing node
        mixing = self.mix_shaders(material, materials=data['materials'])
        mixing.location = (200, 0)
        mixing.label = 'Mix Shader'

        # Create eevee shader node
        eevee = nodes.new('ShaderNodeGroup')
        eevee.node_tree = bpy.data.node_groups['mb_eevee_shader'].copy()
        eevee.location = (400, 0)
        eevee.label = 'Eevee Shader'

        links.new(scale.outputs['Value'], eevee.inputs['Scale'])

        for param in self.eevee_params:
            links.new(mixing.outputs[param], eevee.inputs[param])

        # Add normal map to eevee shader
        if len(data['normals']) >= 1:
            # Add normal group
            eevee_normal_group = self.make_normal(eevee, data['normals'], False)
            eevee_normal_group.location = (0, -300)

            eevee.node_tree.links.new(eevee_normal_group.outputs[0], eevee.node_tree.nodes['Mix Normals'].inputs[1])
            eevee.node_tree.links.new(eevee.node_tree.nodes['Mix Normals'].outputs['Normal'], eevee.node_tree.nodes['Principled BSDF'].inputs['Normal']);

        # Create material outputs
        output_cycles = nodes.new('ShaderNodeOutputMaterial')
        output_cycles.location = (600, 0)
        output_cycles.label = 'Material Output Cycles'
        output_cycles.target = 'CYCLES'

        output_eevee = nodes.new('ShaderNodeOutputMaterial')
        output_eevee.location = (600, 150)
        output_eevee.label = 'Material Output Eevee'
        output_eevee.target = 'EEVEE'

        links.new(mixing.outputs['Shader'], output_cycles.inputs['Surface'])
        links.new(eevee.outputs['Shader'], output_eevee.inputs['Surface'])

        return material

    # --------------------------------------------------------------------------
    # Create node to mix shaders
    # --------------------------------------------------------------------------
    def mix_shaders(self, parent, **kwargs):
        # Type of inputs
        if 'materials' in kwargs:
            type = 'materials'
            materials = kwargs['materials']

        elif 'slots' in kwargs:
            type = 'slots'
            slots = kwargs['slots']

        # Create a new tree
        tree = bpy.data.node_groups.new('mb_mix_shader', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree

        # Create inputs
        group_inputs = tree.nodes.new('NodeGroupInput')

        # Add mixing nodes
        count = (len(materials) + 1) if type == 'materials' else slots
        mix_nodes = []
        mix_eevee_nodes = []
        for i in range(count):
            mix_node = tree.nodes.new('ShaderNodeMixShader')
            mix_node.location = ((i + 1) * 200, 0)

            mix_eevee_node = tree.nodes.new('ShaderNodeGroup')
            mix_eevee_node.node_tree = bpy.data.node_groups['mb_eevee_mix']
            mix_eevee_node.location = ((i + 1) * 200, -150)

            # Create a new group input for the first node
            if i == 0:
                # Cycles
                tree.inputs.new('NodeSocketShader', 'Shader1')

                # Eevee
                for param in self.eevee_params:
                    input_type = 'NodeSocketVector' if param == 'Normal' else 'NodeSocketColor'
                    tree.inputs.new(input_type, param + '1')
                    if param == 'Normal':
                        group.inputs[param + '1'].hide_value = True

            input = group_inputs.outputs['Shader1'] if i == 0 else mix_nodes[-1].outputs['Shader']
            tree.links.new(input, mix_node.inputs[1])

            for param in self.eevee_params:
                input = group_inputs.outputs[param + '1'] if i == 0 else mix_eevee_nodes[-1].outputs[param]
                tree.links.new(input, mix_eevee_node.inputs[param + '1'])

            if i > 0 and type == 'slots':
                tree.inputs.new('NodeSocketColor', 'Mask' + str(i + 1))
                tree.links.new(group_inputs.outputs['Mask' + str(i + 1)], mix_nodes[i - 1].inputs['Fac'])
                tree.links.new(group_inputs.outputs['Mask' + str(i + 1)], mix_eevee_nodes[i - 1].inputs['Mask'])

            socket_suffix = ' Dec.' if i == (count - 1) else str(i + 2)

            # Cycles
            tree.inputs.new('NodeSocketShader', 'Shader' + socket_suffix)
            tree.links.new(group_inputs.outputs['Shader' + socket_suffix], mix_node.inputs[2])

            # Eevee
            for param in self.eevee_params:
                input_type = 'NodeSocketVector' if param == 'Normal' else 'NodeSocketColor'
                tree.inputs.new(input_type, param + socket_suffix)
                if param == 'Normal':
                    group.inputs[param + socket_suffix].hide_value = True

                tree.links.new(group_inputs.outputs[param + socket_suffix], mix_eevee_node.inputs[param + '2'])

            # Add masks
            if i > 0 and type == 'materials':
                material = materials[i - 1]

                # Texture
                texture = TextureNode(group)
                texture.set_location((-700, -250 - (i - 1) * 300))

                texture.set_uv('uvmap' + str(material['uv']))
                texture.set_image(self.get_texture(material['file'], type='mask'))

                # Channel
                channel = group.node_tree.nodes.new('ShaderNodeGroup')

                channel.node_tree = bpy.data.node_groups['mb_channel']
                channel.location = (-200, -220 - (i - 1) * 300)

                map = {'r': 1, 'g': 2, 'b': 3}
                channel.inputs[map[material['channel']]].default_value = 1

                # Links
                tree.links.new(texture.texture.outputs[0], channel.inputs[0])
                tree.links.new(channel.outputs[0], mix_nodes[-1].inputs[0])
                tree.links.new(channel.outputs[0], mix_eevee_nodes[-1].inputs[0])

            mix_nodes.append(mix_node)
            mix_eevee_nodes.append(mix_eevee_node)

        # Create outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location[0] = (len(mix_nodes) + 1) * 200

        # Cycles
        tree.outputs.new('NodeSocketShader', 'Shader')
        tree.links.new(mix_nodes[-1].outputs[0], group_outputs.inputs[0])

        # Eevee
        for param in self.eevee_params:
            input_type = 'NodeSocketVector' if param == 'Normal' else 'NodeSocketColor'
            tree.outputs.new(input_type, param)
            tree.links.new(mix_eevee_nodes[-1].outputs[param], group_outputs.inputs[param])

        # Add black color input for decoration mask
        group.inputs.new('NodeSocketColor','Shader Dec. Mask')
        tree.links.new(group_inputs.outputs[-2], mix_nodes[-1].inputs[0])
        tree.links.new(group_inputs.outputs[-2], mix_eevee_nodes[-1].inputs[0])

        return group

    # --------------------------------------------------------------------------
    # Create normal group
    # --------------------------------------------------------------------------
    def assemble_normals(self, parent, normal, bump, roughness):
        # Create a new tree
        tree = bpy.data.node_groups.new('mb_config_normals', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree

        # Add inputs
        group_inputs = tree.nodes.new('NodeGroupInput')
        group_inputs.label = 'Group Input'

        tree.inputs.new('NodeSocketFloat', 'Bevel')
        tree.inputs.new('NodeSocketFloat', 'Scale')

        # Add normal group
        normal_group = self.make_normal(group, normal, True)
        normal_group.location = (200, 0)

        # Add roughness group
        roughness_group = self.make_roughness(group, roughness)
        roughness_group.location = (200, -150)

        # Add bump group if needed
        has_bump = False
        if len(bump) > 0:
            has_bump = True
            bump_group = self.make_bump(group, bump)
            bump_group.location = (200, -300)

        # Bevel link
        tree.links.new(group_inputs.outputs[0], normal_group.inputs[0])

        # Scale Links
        tree.links.new(group_inputs.outputs[1], normal_group.inputs[1])
        tree.links.new(group_inputs.outputs[1], roughness_group.inputs[0])
        if has_bump:
            tree.links.new(group_inputs.outputs[1], bump_group.inputs[0])

        # Mix normal and roughness
        mix1 = tree.nodes.new('ShaderNodeGroup')
        mix1.node_tree = bpy.data.node_groups['mb_mix_normals']
        mix1.label = 'Mix Normals #1'
        mix1.location = (400, 0)

        tree.links.new(normal_group.outputs[0], mix1.inputs[0])
        tree.links.new(roughness_group.outputs[0], mix1.inputs[1])

        # Mix with bump group if needed
        if has_bump:
            mix2 = tree.nodes.new('ShaderNodeGroup')
            mix2.node_tree = bpy.data.node_groups['mb_mix_normals']
            mix2.label = 'Mix Normals #2'
            mix2.location = (600, 0)

            tree.links.new(mix1.outputs[0], mix2.inputs[0])
            tree.links.new(bump_group.outputs[0], mix2.inputs[1])

            # Height
            mix_height = tree.nodes.new('ShaderNodeGroup')
            mix_height.node_tree = bpy.data.node_groups['mb_mix_heights']
            mix_height.label = 'Mix Heights #1'
            mix_height.location = (600, -150)

            tree.links.new(roughness_group.outputs['Height'], mix_height.inputs['Height1'])
            tree.links.new(bump_group.outputs['Height'], mix_height.inputs['Height2'])

        # Add outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.label = 'Group Output'
        tree.outputs.new('NodeSocketVector', 'Normal')
        tree.outputs.new('NodeSocketColor', 'Height')
        group_outputs.location[0] = 800

        if has_bump:
            tree.links.new(mix2.outputs[0], group_outputs.inputs[0])
            tree.links.new(mix_height.outputs['Height'], group_outputs.inputs['Height'])

        else:
            tree.links.new(mix1.outputs[0], group_outputs.inputs[0])
            tree.links.new(roughness_group.outputs['Height'], group_outputs.inputs['Height'])

        return group

    # --------------------------------------------------------------------------
    # Create normal group
    # --------------------------------------------------------------------------
    def make_normal(self, parent, normal, bevel_node):
        # Create a new tree
        tree = bpy.data.node_groups.new('mb_config_normal', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree
        group.label = 'Normal'

        # Include bevel node
        last_node = None
        if bevel_node is True:
            # Add group inputs
            group_inputs = tree.nodes.new('NodeGroupInput')
            tree.inputs.new('NodeSocketFloat', 'Bevel')
            tree.inputs.new('NodeSocketFloat', 'Scale')

            # Add multiplier node
            multiplier = tree.nodes.new('ShaderNodeMath')
            multiplier.operation = 'MULTIPLY'
            multiplier.location = (200, 200)

            # Add bevel node
            bevel = tree.nodes.new('ShaderNodeBevel')
            bevel.location = (400, 200)

            group.node_tree.links.new(multiplier.outputs[0], bevel.inputs[0])

            tree.links.new(group_inputs.outputs[0], multiplier.inputs[0])
            tree.links.new(group_inputs.outputs[1], multiplier.inputs[1])

            # Last node
            last_node = bevel

        # Add textures
        count = 0
        for item in normal:
            if bevel_node is True and ('bevel' not in item or item['bevel'] is True):
                continue
            else:
                count += 1

                # Normal texture group
                texture = tree.nodes.new('ShaderNodeGroup')
                texture.node_tree = bpy.data.node_groups['mb_normal_texture'].copy()
                texture.label = 'Normal #' + str(count)
                texture.location = (200, -200 * (count - 1))

                # Update uv layer and load image
                texture_tree = texture.node_tree

                uv = self.find_node(texture_tree.nodes, 'UV')
                uv.uv_map = 'uvmap' + str(item['uv'])

                image = self.find_node(texture_tree.nodes, 'Image')
                image.image = self.get_texture(item['file'], type='normal')
                if item['repeat'] is True:
                    image.extension = 'REPEAT'

                # Add mixing group if needed
                if last_node is not None:
                    mix = tree.nodes.new('ShaderNodeGroup')
                    mix.node_tree = bpy.data.node_groups['mb_mix_normals']
                    mix.label = 'Mix Normals #' + str(count)
                    mix.location[0] = 400 + count * 200

                    tree.links.new(last_node.outputs[0], mix.inputs[0])
                    tree.links.new(texture.outputs[0], mix.inputs[1])

                    last_node = mix

                else:
                    last_node = texture

        # Create group outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location[0] = 600 + count * 200
        tree.outputs.new('NodeSocketVector', 'Normal')

        tree.links.new(last_node.outputs[0], group_outputs.inputs[0])

        return group

    # --------------------------------------------------------------------------
    # Create roughness group
    # --------------------------------------------------------------------------
    def make_roughness(self, parent, layers):
        # Create a new tree
        tree = bpy.data.node_groups.new('mb_config_roughness', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree
        group.label = 'Roughness'

        # All parts shall include at least one roughness layer
        # Default values are used if no layers are specified in the configuration
        # or if the first group includes a mask
        groups = []
        if len(layers) == 0 or 'mask' in layers[0]:
            layers.insert(0, {
                'scale': 1, 'strength': 0.025
            })

        for index, data in enumerate(layers):
            if index == 0:
                roughness_layer = RoughnessLayer(
                    group,
                    strength = data['strength'],
                    scale = data['scale']
                )

            else:
                roughness_layer = RoughnessLayer(
                    group,
                    strength = data['strength'],
                    scale = data['scale'],
                    index = index,
                    mask = self.get_texture(data['mask']['file'], type='mask'),
                    channel = data['mask']['channel'],
                    uv = 'uvmap' + str(data['mask']['uv'])
                )

                group.node_tree.links.new(groups[-1].get_output('Normal'), roughness_layer.get_input('Normal'))
                group.node_tree.links.new(groups[-1].get_output('Height'), roughness_layer.get_input('Height'))

            # Save group
            groups.append(roughness_layer)

        # Add group inputs
        group_inputs = tree.nodes.new('NodeGroupInput')
        tree.inputs.new('NodeSocketFloat', 'Scale')

        for layer in groups:
            tree.links.new(group_inputs.outputs['Scale'], layer.get_input('MeshScale'))

        # Create group outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location[0] = (len(layers) + 1) * 200

        tree.outputs.new('NodeSocketVector', 'Normal')
        tree.links.new(groups[-1].get_output('Normal'), group_outputs.inputs['Normal'])

        tree.outputs.new('NodeSocketColor', 'Height')
        tree.links.new(groups[-1].get_output('Height'), group_outputs.inputs['Height'])

        return group

    # --------------------------------------------------------------------------
    # Create bump group
    # --------------------------------------------------------------------------
    def make_bump(self, parent, layers):
        # Create a new tree
        tree = bpy.data.node_groups.new('mb_config_normal', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree
        group.label = 'Bump'

        # Add group inputs
        group_inputs = tree.nodes.new('NodeGroupInput')
        tree.inputs.new('NodeSocketFloat', 'Scale')

        bumps = []
        textures = []
        heights = []
        for i, data in enumerate(layers):
            # Texture
            texture = TextureNode(group)
            texture.set_location((-300, -200 - i * 300))

            # Part version 1 can also have bump map
            version = 2
            if 'version' in data:
                version = data['version']

            # Import image
            if 'filepath' in data:
                image = bpy.data.images.load(data['filepath'], check_existing=False)
                image.pack()

            else:
                image = self.get_texture(data['file'], type='bump', version=version)

            texture.set_uv('uvmap'  + str(data['uv']))
            texture.set_image(image)

            # Bump
            bump = tree.nodes.new('ShaderNodeBump')
            bump.location = (200 + 600 * i, 0)
            bump.inputs[0].default_value = data['strength']

            # Links
            tree.links.new(texture.texture.outputs[0], bump.inputs[2])
            tree.links.new(group_inputs.outputs[0], bump.inputs[1])

            if i > 0:
                tree.links.new(bumps[-1].outputs[0], bump.inputs[3])

            # Height
            math_mul = tree.nodes.new('ShaderNodeMath')
            math_mul.location = (200 + 600 * i, -250 - i * 300)
            math_mul.operation = 'MULTIPLY'
            math_mul.inputs[0].default_value = data['strength']

            tree.links.new(group_inputs.outputs['Scale'], math_mul.inputs[1])

            mix_mul = tree.nodes.new('ShaderNodeMixRGB')
            mix_mul.location = (400 + 600 * i, -250 - i * 300)
            mix_mul.blend_type = 'MULTIPLY'
            mix_mul.inputs[0].default_value = 1

            tree.links.new(math_mul.outputs['Value'], mix_mul.inputs['Color2'])
            tree.links.new(texture.texture.outputs['Color'], mix_mul.inputs['Color1'])

            if i > 0:
                mix_height = tree.nodes.new('ShaderNodeGroup')
                mix_height.node_tree = bpy.data.node_groups['mb_mix_heights']
                mix_height.label = 'Mix Heights #1'
                mix_height.location = (600 + 600 * i, -250 - (i - 1) * 300)

                tree.links.new(heights[-1].outputs['Color'], mix_height.inputs['Height1'])
                tree.links.new(mix_mul.outputs['Color'], mix_height.inputs['Height2'])

                heights.append(mix_height)

            else:
                heights.append(mix_mul)

            textures.append(texture)
            bumps.append(bump)

        # Create group outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location[0] = 200 + len(layers) * 600

        tree.outputs.new('NodeSocketVector', 'Normal')
        tree.links.new(bumps[-1].outputs[0], group_outputs.inputs['Normal'])

        tree.outputs.new('NodeSocketColor', 'Height')
        out_name = 'Height' if 'Height' in heights[-1].outputs else 'Color'
        tree.links.new(heights[-1].outputs[out_name], group_outputs.inputs['Height'])

        for index, texture in enumerate(textures):
            socket_name = 'Height #' + str(index)
            tree.outputs.new('NodeSocketColor', socket_name)
            tree.links.new(texture.texture.outputs[0], group_outputs.inputs[socket_name])

        return group

    # --------------------------------------------------------------------------
    # Add base materials and decoration
    # --------------------------------------------------------------------------
    def upgrade(self, material, data, version = 2):
        # Replace Mix Shader node is there are more than one defaut material
        if version == 1 and 'default' in data['decoration'] and len(data['decoration']['default']) > 1:
            mix_shader = self.replace_mix_shader(material, data['decoration']['default'])

        # Add base materials
        bases = []
        for index, base in enumerate(data['base']):
            base = int(base)

            # Check that material reference exists
            if base not in materials:
                print('Material reference ' + str(base) + ' cannot be found')
                base = 0

            # Update viewport material
            if index == 0:
                alpha = materials[base]['opacity'] if 'opacity' in materials[base] else 1
                material.diffuse_color = materials[base]['sRGB'] + [alpha]

            # Update material screen space refraction
            if ('opacity' in materials[base] and materials[base]['opacity'] < 1) or materials[base]['type'] in ['transparent', 'glitter', 'opal'] :
                material.use_screen_refraction = True

            node = self.add_base(materials[base], index, material)
            bases.append(node)

        # Parts version 1 require special processing
        if version == 1:
            # Add bump map to part revision 1
            if 'bump' in data['decoration']:
                self.add_legacy_bump(data['decoration']['bump'], material)

        # Add decoration
        # Decoration value shall include the color or decoration key
        if data['decoration'] is not None and ('color' in data['decoration'] or 'decoration' in data['decoration']):
            self.add_decoration(data['decoration'], material, bases)

    # --------------------------------------------------------------------------
    # Add base material
    # --------------------------------------------------------------------------
    def add_base(self, data, index, material):
        # Find customize node
        customize = self.find_node(material.node_tree.nodes, 'Customize')

        # Create new colour node
        color = material.node_tree.nodes.new('ShaderNodeGroup')
        color.node_tree = bpy.data.node_groups['mb_color']
        color.location = (-200, -400 * index)

        material.node_tree.links.new(customize.outputs['Color Variation'], color.inputs['Variation'])

        # Create new node
        node = material.node_tree.nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['mb_base_' + data['type']]
        node.location[1] = -400 * index

        # Plug to mix shader group
        mix_shader = self.find_node(material.node_tree.nodes, 'Mix Shader')
        material.node_tree.links.new(node.outputs[0], mix_shader.inputs['Shader' + str(index + 1)])

        for param in self.eevee_params:
            if param in node.outputs:
                material.node_tree.links.new(node.outputs[param], mix_shader.inputs[param + str(index + 1)])

        # Plug roughness, normal and height
        material.node_tree.links.new(customize.outputs['Roughness'], node.inputs['Roughness'])
        material.node_tree.links.new(customize.outputs['Normal'], node.inputs['Normal'])
        material.node_tree.links.new(customize.outputs['Height'], node.inputs['Height'])

        # Plug scale if needed
        if 'Scale' in node.inputs:
            scale = self.find_node(material.node_tree.nodes, 'Scale')
            material.node_tree.links.new(scale.outputs[0], node.inputs['Scale'])

        # Set colour
        color.inputs['Color'].default_value = data['sRGB'] + [1]
        material.node_tree.links.new(color.outputs['Color'], node.inputs['Color'])
        material.node_tree.links.new(color.outputs['Color Raw'], node.inputs['Color Raw'])

        # Opacity
        if 'Opacity' in node.inputs:
            node.inputs['Opacity'].default_value = data['opacity']

        # Diffuse factor for transparent, glitter and opal
        if 'Diffuse Fac' in node.inputs:
            node.inputs['Diffuse Fac'].default_value = data['diffuse']

        # Speckle colour
        if 'Speckle Color' in node.inputs:
            node.inputs['Speckle Color'].default_value = data['speckle'] + [1]

        node.label = 'Base Material #' + str(index + 1)

        return node

    # --------------------------------------------------------------------------
    # Add decoration
    # --------------------------------------------------------------------------
    def add_decoration(self, data, material, bases):
        # Mix Shader group
        mix_shader = self.find_node(material.node_tree.nodes, 'Mix Shader')

        # Create a new tree
        tree = bpy.data.node_groups.new('mb_decoration', 'ShaderNodeTree')

        # Create a new group
        group = material.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree
        group.label = 'Decoration'
        group.location = (-400, 0)

        # Create inputs
        group_inputs = tree.nodes.new('NodeGroupInput')

        # Create outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location = (400, 0)

        # Decoration node
        decoration = group.node_tree.nodes.new('ShaderNodeGroup')
        decoration.node_tree = bpy.data.node_groups['mb_base_decoration']
        decoration.location = (200, 0)

        # Links
        group.inputs.new('NodeSocketFloat', 'Roughness')
        group.inputs.new('NodeSocketVector', 'Normal')
        group.inputs.new('NodeSocketColor', 'Height')
        group.inputs.new('NodeSocketFloat', 'Scale')

        tree.links.new(group_inputs.outputs['Roughness'], decoration.inputs['Roughness'])
        tree.links.new(group_inputs.outputs['Normal'], decoration.inputs['Normal'])
        tree.links.new(group_inputs.outputs['Height'], decoration.inputs['Height'])
        tree.links.new(group_inputs.outputs['Scale'], decoration.inputs['Scale'])

        group.outputs.new('NodeSocketShader', 'Shader')
        group.outputs.new('NodeSocketVector', 'Normal')
        group.outputs.new('NodeSocketColor', 'Height')

        group.node_tree.links.new(decoration.outputs['Shader'], group_outputs.inputs['Shader'])
        group.node_tree.links.new(decoration.outputs['Normal'], group_outputs.inputs['Normal'])
        group.node_tree.links.new(decoration.outputs['Height'], group_outputs.inputs['Height'])

        # Color texture
        color = None
        if 'color' in data and data['color'] is not None:
            color = TextureNode(group)
            color.set_location((-300, -200))
            color.set_uv('uvmap' + str(data['uv']))
            color.set_image(self.get_texture(data['color']['realname'], type='color', scope=data['color']['scope']))

            group.node_tree.links.new(color.texture.outputs[0], decoration.inputs['Color'])
            group.node_tree.links.new(color.texture.outputs[1], decoration.inputs['Alpha'])

            group.outputs.new('NodeSocketFloat', 'Alpha')
            group.node_tree.links.new(color.texture.outputs[1], group_outputs.inputs[-2])

        # Data texture
        if 'data' in data and data['data'] is not None:
            data_texture = TextureNode(group)
            data_texture.set_location((-300, -500))
            data_texture.set_uv('uvmap' + str(data['uv']))
            data_texture.set_image(self.get_texture(data['data']['realname'], type='data', scope=data['data']['scope']))

            group.node_tree.links.new(data_texture.texture.outputs[0], decoration.inputs['Data'])

        # Decoration texture for old element
        decoration_texture = None
        if 'decoration' in data:
            decoration_texture = TextureNode(group)
            decoration_texture.set_location((-500, -200))
            decoration_texture.set_uv('uvmap0')
            decoration_texture.set_image(self.get_texture(data['decoration']['realname'], type='decoration', version=1))

            masks = self.make_legacy_masks(group, data['default'])
            masks.location = (0, -200)

            group.node_tree.links.new(decoration_texture.texture.outputs[0], masks.inputs[0])
            group.node_tree.links.new(decoration_texture.texture.outputs[0], decoration.inputs['Color'])

            group.node_tree.links.new(masks.outputs[0], decoration.inputs['Alpha'])

            group.outputs.new('NodeSocketFloat', 'Alpha')
            group.node_tree.links.new(masks.outputs[0], group_outputs.inputs[-2])

            for index, output in enumerate(masks.outputs):
                if index == 0:
                    continue

                socket_name = 'Mask' + str(index)
                group.outputs.new('NodeSocketColor', socket_name)
                group.node_tree.links.new(output, group_outputs.inputs[socket_name])

                # Plug to mix shader
                if index > 1:
                    material.node_tree.links.new(group.outputs[socket_name], mix_shader.inputs[socket_name])

            # Converter for data texture
            if 'metalness' in data or 'bump' in data:
                data_node = group.node_tree.nodes.new('ShaderNodeGroup')
                data_node.node_tree = bpy.data.node_groups['mb_legacy_data']
                data_node.location = (0, -500)

                group.node_tree.links.new(data_node.outputs[0], decoration.inputs['Data'])

                # Metal texture
                if 'metalness' in data:
                    metal_texture = TextureNode(group)
                    metal_texture.set_location((-500, -500))
                    metal_texture.set_uv('uvmap0')
                    metal_texture.set_image(self.get_texture(data['metalness']['realname'], type='metalness', version=1))

                    group.node_tree.links.new(metal_texture.texture.outputs[0], data_node.inputs['Metal'])

                # Bump texture to extract sticker shape
                if 'bump' in data:
                    group.inputs.new('NodeSocketFloat', 'Bump')
                    group.node_tree.links.new(group_inputs.outputs[-2], data_node.inputs['Bump'])

                    # Get normal node
                    normal = self.find_node(material.node_tree.nodes, 'Normal')

                    # Plug normal to decoration
                    material.node_tree.links.new(normal.outputs['Height #0'], group.inputs['Bump'])

        # Sticker shape
        group.outputs.new('NodeSocketColor', 'Sticker')
        group.node_tree.links.new(decoration.outputs['Sticker'], group_outputs.inputs['Sticker'])

        group.outputs.new('NodeSocketColor', 'Color')
        group.outputs.new('NodeSocketColor', 'Metallic')
        group.outputs.new('NodeSocketColor', 'Roughness')

        group.node_tree.links.new(decoration.outputs['Color'], group_outputs.inputs['Color'])
        group.node_tree.links.new(decoration.outputs['Metallic'], group_outputs.inputs['Metallic'])
        group.node_tree.links.new(decoration.outputs['Roughness'], group_outputs.inputs['Roughness'])

        # Material links
        customize = self.find_node(material.node_tree.nodes, 'Customize')
        material.node_tree.links.new(customize.outputs['Roughness'], group.inputs['Roughness'])
        material.node_tree.links.new(customize.outputs['Normal'], group.inputs['Normal'])
        material.node_tree.links.new(customize.outputs['Height'], group.inputs['Height'])

        scale = self.find_node(material.node_tree.nodes, 'Scale')
        material.node_tree.links.new(scale.outputs[0], group.inputs['Scale'])

        material.node_tree.links.new(group.outputs['Shader'], mix_shader.inputs['Shader Dec.'])
        material.node_tree.links.new(group.outputs['Color'], mix_shader.inputs['Color Dec.'])
        material.node_tree.links.new(group.outputs['Metallic'], mix_shader.inputs['Metallic Dec.'])
        material.node_tree.links.new(group.outputs['Roughness'], mix_shader.inputs['Roughness Dec.'])
        material.node_tree.links.new(group.outputs['Normal'], mix_shader.inputs['Normal Dec.'])
        material.node_tree.links.new(group.outputs['Height'], mix_shader.inputs['Height Dec.'])

        # Plug normal to base materials
        for base in bases:
            material.node_tree.links.new(group.outputs['Normal'], base.inputs['Normal'])
            material.node_tree.links.new(group.outputs['Height'], base.inputs['Height'])

        if 'Alpha' in group.outputs:
            material.node_tree.links.new(group.outputs['Alpha'], mix_shader.inputs['Shader Dec. Mask'])

    # --------------------------------------------------------------------------
    # Add bump map for part version 1
    # --------------------------------------------------------------------------
    def add_legacy_bump(self, bump, material):
        # Get normal node
        normal = self.find_node(material.node_tree.nodes, 'Normal')

        nodes = normal.node_tree.nodes
        links = normal.node_tree.links

        # Add bump node
        bump_layers = [{
            'file': bump['realname'],
            'version': 1,
            'uv': 0,
            'strength': 1
        }]
        bump_group = self.make_bump(normal, bump_layers)
        bump_group.location = (200, -300)

        # Add mix normals node
        mix2 = nodes.new('ShaderNodeGroup')
        mix2.node_tree = bpy.data.node_groups['mb_mix_normals']
        mix2.label = 'Mix Normals #2'
        mix2.location = (600, 0)

        # Add mix heights node
        mix_heights = nodes.new('ShaderNodeGroup')
        mix_heights.node_tree = bpy.data.node_groups['mb_mix_heights']
        mix_heights.label = 'Mix Heights #1'
        mix_heights.location = (600, -150)

        # Get useful existing nodes
        input = self.find_node(nodes, 'Group Input')
        output = self.find_node(nodes, 'Group Output')
        mix1 = self.find_node(nodes, 'Mix Normals #1')
        roughness = self.find_node(nodes, 'Roughness')

        # Links
        links.new(input.outputs[0], bump_group.inputs[0])
        links.new(mix1.outputs[0], mix2.inputs[0])
        links.new(bump_group.outputs[0], mix2.inputs[1])
        links.new(bump_group.outputs[-1], output.inputs[-1])
        links.new(mix2.outputs[0], output.inputs[0])

        links.new(roughness.outputs['Height'], mix_heights.inputs[0])
        links.new(bump_group.outputs['Height'], mix_heights.inputs[1])
        links.new(mix_heights.outputs['Height'], output.inputs['Height'])

    # --------------------------------------------------------------------------
    # Create legacy masks from decoration texture
    # --------------------------------------------------------------------------
    def make_legacy_masks(self, parent, default):
        # Create a new tree
        tree = bpy.data.node_groups.new('mb_legacy_masks', 'ShaderNodeTree')

        # Create a new group
        group = parent.node_tree.nodes.new('ShaderNodeGroup')
        group.node_tree = tree
        group.label = 'Legacy Masks'

        # Add inputs
        group_inputs = tree.nodes.new('NodeGroupInput')
        group.inputs.new('NodeSocketColor', 'Image')

        # Add outputs
        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.location[0] = 800

        # Add color masks
        masks = []
        mixers = []
        for index, reference in enumerate(default):
            reference = int(reference)

            mask = group.node_tree.nodes.new('ShaderNodeGroup')
            mask.node_tree = bpy.data.node_groups['mb_legacy_color_mask']
            mask.location = (200, -200 * index)

            # Attach decoration texture to Image input
            group.node_tree.links.new(group_inputs.outputs[0], mask.inputs['Image'])

            # Set reference color
            if reference not in materials:
                print('Material reference ' + str(reference) + ' cannot be found')
                reference = 0

            rgb = materials[reference]
            mask.inputs['Reference'].default_value = rgb['sRGB'] + [1]

            masks.append(mask)

            # Mix with previous masks
            if index > 0:
                mix = group.node_tree.nodes.new('ShaderNodeMixRGB')
                mix.location = (200 * (index + 1), 0)

                mix.use_clamp = True
                mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1
                # Change to multiply

                # Input 1
                if len(mixers) == 0:
                    group.node_tree.links.new(masks[-2].outputs['Mask'], mix.inputs['Color1'])
                else:
                    group.node_tree.links.new(mixers[-1].outputs['Mask'], mix.inputs['Color1'])

                # Input 2
                group.node_tree.links.new(masks[-1].outputs['Mask'], mix.inputs['Color2'])

                mixers.append(mix)

        # Plug alpha mask to output
        group.outputs.new('NodeSocketColor', 'Alpha')
        if len(mixers) > 0:
            group.node_tree.links.new(mixers[-1].outputs['Color'], group_outputs.inputs[-2])
        else:
            group.node_tree.links.new(masks[-1].outputs['Mask'], group_outputs.inputs[-2])

        # Mask links
        for index, mask in enumerate(masks):
            socket_name = 'Mask' + str(index + 1)
            group.outputs.new('NodeSocketColor', socket_name)
            group.node_tree.links.new(mask.outputs['Mask Inverted'], group_outputs.inputs[-2])

        return group

    # --------------------------------------------------------------------------
    # Replace mix shader node by special version for legacy part
    # --------------------------------------------------------------------------
    def replace_mix_shader(self, material, default):
        # Remove mix shader group
        mix_shader = self.find_node(material.node_tree.nodes, 'Mix Shader')
        material.node_tree.nodes.remove(mix_shader)

        # Create new mix shader group
        mix_shader = self.mix_shaders(material, slots=len(default))
        mix_shader.location = (200, 0)
        mix_shader.label = 'Mix Shader'

        # Plug mix shader to output
        material_output = self.find_node(material.node_tree.nodes, 'Material Output Cycles')
        material.node_tree.links.new(mix_shader.outputs['Shader'], material_output.inputs['Surface'])

        eevee_shader = self.find_node(material.node_tree.nodes, 'Eevee Shader')
        for param in self.eevee_params:
            material.node_tree.links.new(mix_shader.outputs[param], eevee_shader.inputs[param])

    # --------------------------------------------------------------------------
    # Find node with specified label
    # --------------------------------------------------------------------------
    def find_node(self, nodes, label):
        for node in nodes:
            if node.label == label:
                return node

        return None

    # --------------------------------------------------------------------------
    # Get texture
    # --------------------------------------------------------------------------
    def get_texture(self, filename, **kwargs):
        version = kwargs['version'] if 'version' in kwargs else 2
        scope = kwargs['scope'] if 'scope' in kwargs else 'official'
        type = kwargs['type']

        # Get library that may contain the texture
        library = self.textures[version]
        if version == 2:
            library = library[scope]
        library = library[type]

        return library[filename]
