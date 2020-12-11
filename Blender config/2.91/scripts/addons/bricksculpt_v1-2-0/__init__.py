# Copyright (C) 2018 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name"        : "BrickSculpt (Bricker Addon)",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (1, 2, 0),
    "blender"     : (2, 83, 0),
    "description" : "Brick Sculpting Tools for Bricker",
    "location"    : "View3D > UI > Bricker > Customize Model",
    "warning"     : "",
    "wiki_url"    : "https://www.blendermarket.com/products/bricksculpt/",
    "doc_url"     : "https://www.blendermarket.com/products/bricksculpt/",
    "tracker_url" : "https://blendermarket.com/products/bricksculpt/faq",
    "category"    : "Object",
}

# System imports
import importlib

# Blender imports
import bpy
from bpy.types import Scene
from bpy.props import *

# Addon imports
if "classes_to_register" in locals():
    import importlib
    common = importlib.reload(common)
    classes_to_register = importlib.reload(classes_to_register)
    keymaps = importlib.reload(keymaps)
    property_groups = importlib.reload(property_groups)
else:
    from .functions import common, app_handlers
    from .lib import classes_to_register, keymaps, property_groups

# store keymaps here to access after registration
addon_keymaps = []


def register():
    # register classes
    for cls in classes_to_register.classes:
        common.make_annotations(cls)
        bpy.utils.register_class(cls)

    bpy.props.bricksculpt_module_name = __name__
    bpy.props.bricksculpt_version = str(bl_info["version"])[1:-1].replace(", ", ".")
    bpy.props.brickscape_validated = True

    Scene.bricksculpt = PointerProperty(type=property_groups.BrickSculptProperties)

    # handle the keymaps
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon: # check this to avoid errors in background case
        km = wm.keyconfigs.addon.keymaps.new(name="Object Mode", space_type="EMPTY")
        keymaps.add_keymaps(km)
        addon_keymaps.append(km)


def unregister():
    # handle the keymaps
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

    del Scene.bricksculpt

    del bpy.props.brickscape_validated
    del bpy.props.bricksculpt_version
    del bpy.props.bricksculpt_module_name

    # unregister classes
    for cls in reversed(classes_to_register.classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
