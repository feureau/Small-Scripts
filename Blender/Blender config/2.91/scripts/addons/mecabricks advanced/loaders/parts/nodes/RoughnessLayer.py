import bpy

from .TextureNode import TextureNode

class RoughnessLayer:
    # -----------------------------------------------------------------------------
    # Constructor
    # -----------------------------------------------------------------------------
    def __init__(self, parent, **kwargs):
        self.parent = parent

        # Roughness group
        self.roughness = self.parent.node_tree.nodes.new('ShaderNodeGroup')

        # No mask specified
        if 'mask' not in kwargs:
            self.roughness.node_tree = bpy.data.node_groups['mb_roughness']
            self.roughness.location[0] = 200

        # Mask specified
        else:
            self.roughness.node_tree = bpy.data.node_groups['mb_roughness_mask'].copy()
            self.roughness.location[0] = 200 * (kwargs['index'] + 1)

            # Select colour channel
            self.roughness.inputs[kwargs['channel'].upper()].default_value = 1

            # Texture
            self.texture = TextureNode(self.parent)
            self.texture.set_location((-100, -220 - 300 * (kwargs['index'] - 1)))

            # Link texture to roughness
            self.parent.node_tree.links.new(self.texture.texture.outputs[0], self.roughness.inputs['Mask'])

            # Select uv layer
            self.texture.set_uv(kwargs['uv'])

            # Select image
            self.texture.set_image(kwargs['mask'])

        # Set scale and strength
        self.roughness.inputs['Strength'].default_value = kwargs['strength']
        self.roughness.inputs['Scale'].default_value = kwargs['scale']

        self.roughness.label = 'Roughness Layer'

    # -----------------------------------------------------------------------------
    # Return roughness output
    # -----------------------------------------------------------------------------
    def get_output(self, name):
        return self.roughness.outputs[name]

    # -----------------------------------------------------------------------------
    # Return roughness normal input
    # -----------------------------------------------------------------------------
    def get_input(self, name):
        return self.roughness.inputs[name]
