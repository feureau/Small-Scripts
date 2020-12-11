bl_info = {
    'name': 'MecaFig',
    'description': 'A ready shaded and rigged LEGO® MiniFigurine for your renders and animations!',
    'author': 'Bruno Ducloy',
    'version': (2019, 1, 2),
    'blender': (2, 80, 75),
    'location': '3D View > Properties (N) > MecaFig',
    'warning': '',
    'wiki_url': '',
    'category': '3D View'
}

import bpy

from .icons.__init__ import *
from .operators.__init__ import *
from .properties.__init__ import *
from .ui.__init__ import *

def register():
    register_icons()
    register_properties()
    register_operators()
    register_ui()

def unregister():
    unregister_ui()
    unregister_operators()
    unregister_properties()
    unregister_icons()

if __name__ == '__main__':
    register()
