# Copyright (C) 2019 Christopher Gearhart
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
    "name"        : "ABS Plastic Materials",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (3, 1, 0),
    "blender"     : (2, 83, 0),
    "description" : "Append ABS Plastic Materials to current blender file with a simple click",
    "location"    : "PROPERTIES > Materials > ABS Plastic Materials",
    "warning"     : "",  # used for warning icon and text in addons panel
    "wiki_url"    : "https://www.blendermarket.com/products/abs-plastic-materials",
    "doc_url"     : "https://www.blendermarket.com/products/abs-plastic-materials",  # 2.83+
    "tracker_url" : "https://github.com/bblanimation/abs-plastic-materials/issues",
    "category"    : "Materials",
}

# System imports
import getpass

# Blender imports
import bpy
from bpy.props import *
from bpy.types import Scene, Material
from bpy.utils import register_class, unregister_class
props = bpy.props

# Module imports
if "classes_to_register" in locals():
    import importlib
    addon_updater_ops = importlib.reload(addon_updater_ops)
    app_handlers = importlib.reload(app_handlers)
    property_callbacks = importlib.reload(property_callbacks)
    common = importlib.reload(common)
    classes_to_register = importlib.reload(classes_to_register)
    mat_properties = importlib.reload(mat_properties)
else:
    from . import addon_updater_ops
    from .functions import app_handlers, property_callbacks, common
    from .lib import classes_to_register, mat_properties


def register():
    for cls in classes_to_register.classes:
        common.blender.make_annotations(cls)
        bpy.utils.register_class(cls)

    bpy.props.abs_plastic_materials_module_name = __name__
    bpy.props.abs_plastic_version = str(bl_info["version"])[1:-1].replace(", ", ".")
    bpy.props.abs_mat_properties = mat_properties.mat_properties
    bpy.props.abs_developer_mode = getpass.getuser().startswith("cgear") and True
    bpy.props.abs_validated = True

    bpy.props.abs_mats_common = [
        "ABS Plastic Black",
        "ABS Plastic Blue",
        "ABS Plastic Dark Azure",
        "ABS Plastic Dark Blue",
        "ABS Plastic Dark Bluish Gray",
        "ABS Plastic Dark Brown",
        "ABS Plastic Dark Green",
        "ABS Plastic Dark Red",
        "ABS Plastic Dark Tan",
        "ABS Plastic Green",
        "ABS Plastic Light Bluish Gray",
        "ABS Plastic Lime",
        "ABS Plastic Orange",
        "ABS Plastic Red",
        "ABS Plastic Reddish Brown",
        "ABS Plastic Sand Blue",
        "ABS Plastic Sand Green",
        "ABS Plastic Tan",
        "ABS Plastic White",
        "ABS Plastic Yellow",
    ]

    bpy.props.abs_mats_transparent = [
        "ABS Plastic Trans-Black",
        "ABS Plastic Trans-Bright Green",
        "ABS Plastic Trans-Clear",
        "ABS Plastic Trans-Dark Blue",
        "ABS Plastic Trans-Dark Pink",
        "ABS Plastic Trans-Green",
        "ABS Plastic Trans-Light Blue",
        "ABS Plastic Trans-Neon Green",
        "ABS Plastic Trans-Neon Orange",
        "ABS Plastic Trans-Orange",
        "ABS Plastic Trans-Purple",
        "ABS Plastic Trans-Red",
        "ABS Plastic Trans-Yellow",
    ]

    bpy.props.abs_mats_uncommon = [
        "ABS Plastic Bright Green",
        "ABS Plastic Bright Light Orange",
        "ABS Plastic Bright Light Blue",
        "ABS Plastic Bright Light Yellow",
        "ABS Plastic Bright Pink",
        "ABS Plastic Coral",
        "ABS Plastic Dark Orange",
        "ABS Plastic Dark Pink",
        "ABS Plastic Dark Purple",
        "ABS Plastic Dark Turquoise",
        "ABS Plastic Lavender",
        "ABS Plastic Light Aqua",
        "ABS Plastic Light Nougat",
        "ABS Plastic Magenta",
        "ABS Plastic Medium Azure",
        "ABS Plastic Medium Blue",
        "ABS Plastic Medium Lavender",
        "ABS Plastic Medium Nougat",
        "ABS Plastic Metallic Gold",
        "ABS Plastic Metallic Silver",
        "ABS Plastic Nougat",
        "ABS Plastic Olive Green",
        "ABS Plastic Yellowish Green",
    ]

    bpy.props.abs_mats_undefined = [
        "ABS Plastic Pearl Gold",
        "ABS Plastic Flat Silver",
        "ABS Plastic Pearl Dark Gray",
        "ABS Plastic Chrome Silver",
        "ABS Plastic Chrome Gold",
    ]

    Scene.abs_subsurf = FloatProperty(
        name="Subsurface Scattering",
        description="Amount of subsurface scattering for ABS Plastic Materials (higher values up to 1 are more accurate, but increase render times)",
        subtype="FACTOR",
        min=0, soft_max=1,
        precision=3,
        update=property_callbacks.update_abs_subsurf,
        default=1,
    )
    Scene.abs_roughness = FloatProperty(
        name="Roughness",
        description="Amount of roughness for the ABS Plastic Materials",
        subtype="FACTOR",
        min=0, max=1,
        precision=3,
        update=property_callbacks.update_abs_roughness,
        default=0.005,
    )
    Scene.abs_randomize = FloatProperty(
        name="Randomize",
        description="Amount of per-object randomness for ABS Plastic Material colors",
        subtype="FACTOR",
        min=0, soft_max=1,
        precision=3,
        update=property_callbacks.update_abs_randomize,
        default=0.025,
    )
    Scene.abs_fingerprints = FloatProperty(
        name="Fingerprints",
        description="Amount of fingerprints and dust to add to the specular map of the ABS Plastic Materials",
        subtype="FACTOR",
        min=0, max=1,
        precision=3,
        update=property_callbacks.update_abs_fingerprints,
        default=0.25,
    )
    Scene.abs_displace = FloatProperty(
        name="Displacement",
        description="Bumpiness of the ABS Plastic Materials (0.04 recommended)",
        subtype="FACTOR",
        min=0, soft_max=1,
        precision=3,
        update=property_callbacks.update_abs_displace,
        default=0.0,
    )
    Scene.abs_fpd_quality = FloatProperty(
        name="FP/Dust Quality",
        description="Quality of the fingerprints and dust textures (save memory by reducing quality)",
        subtype="FACTOR",
        min=0, max=1,
        precision=1,
        update=property_callbacks.update_fd_image,
        default=0.5,
    )
    Scene.abs_s_quality = FloatProperty(
        name="Scratch Quality",
        description="Quality of the scratch texture (save memory by reducing quality)",
        subtype="FACTOR",
        min=0, max=1,
        precision=1,
        update=property_callbacks.update_s_image,
        default=0.5,
    )
    Scene.abs_uv_scale = FloatProperty(
        name="UV Scale",
        description="Update the universal scale of the Fingerprints & Dust UV Texture",
        min=0,
        update=property_callbacks.update_abs_uv_scale,
        default=1,
    )
    Scene.save_datablocks = BoolProperty(
        name="Save Data-Blocks",
        description="Save ABS Plastic Materials even if they have no users",
        update=property_callbacks.toggle_save_datablocks,
        default=True,
    )
    Scene.abs_viewport_transparency = BoolProperty(
        name="Viewport Transparency",
        description="Display trans- materials as partially transparent in the 3D viewport",
        update=property_callbacks.update_viewport_transparency,
        default=False,
    )
    Scene.abs_mapping = EnumProperty(
        name="Texture Mapping",
        description="The method to use for mapping the fingerprints and dust textures",
        items=[
            ("UV", "UV", "Use active UV map"),
            ("Generated", "Generated", "Use generated texture coordinates"),
        ],
        update=property_callbacks.update_texture_mapping,
        default="Generated",
    )

    # Attribute for tracking version
    Material.abs_plastic_version = StringProperty(default="2.1.0")  # default is the version where this property was introduced

    # register app handlers
    bpy.app.handlers.load_pre.append(app_handlers.validate_abs_plastic_materials)
    bpy.app.handlers.load_post.append(app_handlers.handle_upconversion)
    bpy.app.handlers.load_post.append(app_handlers.verify_texture_data)

    # addon updater code and configurations
    addon_updater_ops.register(bl_info)


def unregister():

    # addon updater unregister
    addon_updater_ops.unregister()

    # unregister app handlers
    bpy.app.handlers.load_post.remove(app_handlers.verify_texture_data)
    bpy.app.handlers.load_post.remove(app_handlers.handle_upconversion)
    bpy.app.handlers.load_pre.remove(app_handlers.validate_abs_plastic_materials)

    del Material.abs_plastic_version
    del Scene.abs_viewport_transparency
    del Scene.save_datablocks
    del Scene.abs_fpd_quality
    del Scene.abs_displace
    del Scene.abs_fingerprints
    del Scene.abs_randomize
    del Scene.abs_roughness
    del Scene.abs_subsurf
    del bpy.props.abs_mats_uncommon
    del bpy.props.abs_mats_transparent
    del bpy.props.abs_mats_common
    del bpy.props.abs_mat_properties
    del bpy.props.abs_validated
    del bpy.props.abs_plastic_version
    del bpy.props.abs_plastic_materials_module_name

    for cls in reversed(classes_to_register.classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
