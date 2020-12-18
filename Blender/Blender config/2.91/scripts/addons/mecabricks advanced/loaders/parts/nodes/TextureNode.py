import mathutils

class TextureNode:
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, parent):
        self.parent = parent
        self.texture_offset = mathutils.Vector((200, 40))

        # Add UV Map and Image Texture nodes
        nodes = parent.node_tree.nodes
        links = parent.node_tree.links

        self.uv = nodes.new('ShaderNodeUVMap')
        self.uv.location = (0, 0)

        self.texture = nodes.new('ShaderNodeTexImage')
        self.texture.location = self.texture_offset

        links.new(self.uv.outputs[0], self.texture.inputs[0])

    # --------------------------------------------------------------------------
    # Move node group to the specified location
    # --------------------------------------------------------------------------
    def set_location(self, location):
        self.uv.location = location
        self.texture.location = mathutils.Vector(location) + self.texture_offset

    # --------------------------------------------------------------------------
    # Set uv map
    # --------------------------------------------------------------------------
    def set_uv(self, name):
        self.uv.uv_map = name

    # --------------------------------------------------------------------------
    # Set image texture
    # --------------------------------------------------------------------------
    def set_image(self, image, extension = 'EXTEND'):
        self.texture.image = image
        self.texture.extension = extension
