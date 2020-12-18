# Copyright (C) 2020 Christopher Gearhart
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

# System imports
from colorsys import rgb_to_hsv, hsv_to_rgb

# Module imports
from .common import *
from .general import *
from .colors import *
from .matlist_utils import *
from .brick.legal_brick_sizes import *


def brick_materials_installed():
    """ checks that 'ABS Plastic Materials' addon is installed and enabled """
    return hasattr(bpy.props, "abs_plastic_materials_module_name")


def brick_materials_imported():
    """ check that all brick materials have been imported """
    scn = bpy.context.scene
    # make sure abs_plastic_materials addon is installed
    if not brick_materials_installed():
        return False
    # check if any of the colors haven't been loaded
    mats = bpy.data.materials.keys()
    for mat_name in get_abs_mat_names():
        if mat_name not in mats:
            return False
    return True


def get_abs_mat_names(all:bool=True):
    """ returns list of ABS Plastic Material names """
    if not brick_materials_installed():
        return []
    scn = bpy.context.scene
    materials = list()
    # get common names (different properties for different versions)
    materials += bpy.props.abs_mats_common if hasattr(bpy.props, "abs_mats_common") else bpy.props.abs_plastic_materials
    # get transparent/uncommon names
    if all or scn.include_transparent:
        materials += bpy.props.abs_mats_transparent
    if all or scn.include_uncommon:
        materials += bpy.props.abs_mats_uncommon
    return materials


def update_displacement_of_mat(mat, displacement=0.04):
    """ snippit from 'update_abs_displace' function found in ABS Plastic Materials source code """
    scn = bpy.context.scene
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    target_node = nodes.get("ABS Bump")
    if target_node is None:
        return
    noise = target_node.inputs.get("Noise")
    waves = target_node.inputs.get("Waves")
    scratches = target_node.inputs.get("Scratches")
    fingerprints = target_node.inputs.get("Fingerprints")
    if noise is None or waves is None or scratches is None or fingerprints is None:
        return
    noise.default_value = displacement * (20 if "Metallic" in mat.name else 1)
    waves.default_value = displacement
    scratches.default_value = displacement
    fingerprints.default_value = scn.abs_fingerprints * displacement
    # disconnect displacement node if not used
    try:
        displace_in = nodes["Material Output"].inputs["Displacement"]
        displace_out = nodes["Displacement"].outputs["Displacement"] if b280() else target_node.outputs["Color"]
    except KeyError:
        return
    if displacement == 0:
        for l in displace_in.links:
            links.remove(l)
    else:
        links.new(displace_out, displace_in)


def create_new_material(model_name, rgba, rgba_vals, sss, sat_mat, specular, roughness, ior, transmission, displacement, use_abs_template, last_use_abs_template, include_transparency, cur_frame=None):
    """ create new material with specified rgba values """
    # get or create material with unique color
    if rgba is None:
        return ""
    scn = bpy.context.scene
    r0, g0, b0, a0 = rgba
    # min_diff = float("inf")
    # for i in range(len(rgba_vals)):
    #     diff = rgba_distance(rgba, rgba_vals[i])
    #     if diff < min_diff and diff < snap_amount:
    #         min_diff = diff
    #         r0, g0, b0, a0 = rgba_vals[i]
    #         break
    mat_name_end_string = "".join((str(round(r0, 5)), str(round(g0, 5)), str(round(b0, 5)), str(round(a0, 5))))
    mat_name_hash = str(hash_str(mat_name_end_string))[:14]
    mat_name = "Bricker_{n}{f}_{hash}".format(n=model_name, f="_f_%(cur_frame)s" % locals() if cur_frame is not None else "", hash=mat_name_hash)
    mat = bpy.data.materials.get(mat_name)
    # handle materials created using abs template
    if use_abs_template:
        if mat and mat.node_tree.nodes.get("ABS Dialectric") is None:
            bpy.data.materials.remove(mat)
            mat = None
        if mat is None:
            abs_template_mat_name = "ABS Plastic Black"
            if abs_template_mat_name not in bpy.data.materials or bpy.data.materials[abs_template_mat_name].node_tree.nodes.get("ABS Dialectric") is None:
                bpy.ops.abs.append_materials()
            mat = bpy.data.materials[abs_template_mat_name].copy()
            update_displacement_of_mat(mat, displacement)
            mat.name = mat_name
            mat.diffuse_color[:3] = rgba[:3]
            if b280():
                mat.diffuse_color[3] = rgba[3] if include_transparency else 1
            dialectric_node = mat.node_tree.nodes.get("ABS Dialectric")
            dialectric_node.inputs["Diffuse Color"].default_value = rgba
            sss_amount = round(0.15 * sss * (rgb_to_hsv(*rgba[:3])[2] ** 1.5), 2)
            if sss_amount != 0:
                dialectric_node.inputs["SSS Amount"].default_value = sss_amount
                dialectric_node.inputs["SSS Color"].default_value = rgba
        return mat_name
    # handle materials created from scratch
    mat_is_new = mat is None
    mat = mat or bpy.data.materials.new(name=mat_name)
    # set diffuse and transparency of material
    if mat_is_new:
        mat.diffuse_color[:3] = rgba[:3]
        if b280():
            mat.diffuse_color[3] = rgba[3] if include_transparency else 1
        if scn.render.engine == "BLENDER_RENDER":
            mat.diffuse_intensity = 1.0
            if a0 < 1.0:
                mat.use_transparency = True
                mat.alpha = rgba[3]
        elif scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            mat.use_nodes = True
            mat_nodes = mat.node_tree.nodes
            mat_links = mat.node_tree.links
            if scn.render.engine in ("CYCLES", "BLENDER_EEVEE"):
                if b280():
                    # get principled material node
                    principled = mat_nodes.get("Principled BSDF")
                else:
                    # a new material node tree already has a diffuse and material output node
                    output = mat_nodes["Material Output"]
                    # remove default Diffuse BSDF
                    diffuse = mat_nodes["Diffuse BSDF"]
                    mat_nodes.remove(diffuse)
                    # add Principled BSDF
                    principled = mat_nodes.new("ShaderNodeBsdfPrincipled")
                    # link Principled BSDF to output node
                    mat_links.new(principled.outputs["BSDF"], output.inputs["Surface"])
                # set values for Principled BSDF
                principled.inputs[0].default_value = rgba
                principled.inputs[1].default_value = sss
                principled.inputs[3].default_value[:3] = mathutils_mult(Vector(rgba[:3]), sat_mat).to_tuple()
                principled.inputs[5].default_value = specular
                principled.inputs[7].default_value = roughness
                principled.inputs[14].default_value = ior
                principled.inputs[15].default_value = transmission
                if include_transparency:
                    if b280():
                        principled.inputs[18].default_value = rgba[3]
                    else:
                        # a new material node tree already has a diffuse and material output node
                        output = mat_nodes["Material Output"]
                        # create transparent and mix nodes
                        transparent = mat_nodes.new("ShaderNodeBsdfTransparent")
                        mix = mat_nodes.new("ShaderNodeMixShader")
                        # link these nodes together
                        mat_links.new(principled.outputs["BSDF"], mix.inputs[1])
                        mat_links.new(transparent.outputs["BSDF"], mix.inputs[2])
                        mat_links.new(mix.outputs["Shader"], output.inputs["Surface"])
                        # set mix factor to 1 - alpha
                        mix.inputs[0].default_value = rgba[3]
            elif scn.render.engine == "octane":
                # a new material node tree already has a diffuse and material output node
                output = mat_nodes["Material Output"]
                # remove default Diffuse shader
                diffuse = mat_nodes["Octane Diffuse Mat"]
                mat_nodes.remove(diffuse)
                # add Octane Glossy shader
                oct_glossy = mat_nodes.new("ShaderNodeOctGlossyMat")
                # set values for Octane Glossy shader
                oct_glossy.inputs[0].default_value = rgba
                oct_glossy.inputs["Specular"].default_value = specular
                oct_glossy.inputs["Roughness"].default_value = roughness
                oct_glossy.inputs["Index"].default_value = ior
                oct_glossy.inputs["Opacity"].default_value = rgba[3]
                oct_glossy.inputs["Smooth"].default_value = True
                mat_links.new(oct_glossy.outputs["OutMat"], output.inputs["Surface"])
            # elif scn.render.engine == "LUXCORE":
            #     # get default Matte shader
            #     matte = mat_nodes["Matte Material"]
            #     # set values for Matte shader
            #     matte.inputs[0].default_value = rgba
            #     matte.inputs["Opacity"].default_value = rgba[3]
    else:
        if scn.render.engine == "BLENDER_RENDER":
            # make sure 'use_nodes' is disabled
            mat.use_nodes = False
            # update material color
            r1, g1, b1 = mat.diffuse_color
            a1 = mat.alpha
            r2, g2, b2, a2 = get_average(Vector(rgba), Vector((r1, g1, b1, a1)), mat.num_averaged)
            mat.diffuse_color = [r2, g2, b2]
            mat.alpha = a2
        # if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane", "LUXCORE"):
        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            # make sure 'use_nodes' is enabled
            mat.use_nodes = True
            # get first node
            first_node = get_first_bsdf_node(mat)
            # update first node's color
            if first_node:
                rgba1 = vec_round(first_node.inputs[0].default_value, 5, outer_type=list)
                if b280():
                    mat.diffuse_color[3] = rgba1[3] if include_transparency else 1
                new_rgba = get_average(Vector(rgba), Vector(rgba1), mat.num_averaged)
                first_node.inputs[0].default_value = new_rgba
                first_node.inputs[3].default_value[:3] = mathutils_mult(Vector(new_rgba[:3]), sat_mat).to_tuple()
    mat.num_averaged += 1
    return mat_name


def get_brick_rgba(obj, face_idx, point, uv_image=None, color_depth:int=0, blur_radius:int=0):
    """ returns RGBA value for brick """
    if face_idx is None:
        return None, None
    # get material based on rgba value of UV image at face index
    image = get_uv_image(obj, face_idx=face_idx, uv_image=uv_image)
    if image is not None:
        orig_mat_name = ""
        rgba = get_uv_pixel_color(obj, face_idx, point, image, color_depth=color_depth, blur_radius=blur_radius)
    else:
        # get closest material using material slot of face
        orig_mat = get_mat_at_face_idx(obj, face_idx)
        orig_mat_name = orig_mat.name if orig_mat is not None else ""
        rgba = get_material_color(orig_mat_name)
    return rgba, orig_mat_name


def get_materials_in_model(cm, cur_frame=None):
    """ cannot account for materials added with BrickSculpt paintbrush """
    scn, cm, n = get_active_context_info(cm=cm)
    if cm.color_snap in ("ABS", "RANDOM"):
        return [mat for mat in get_mat_obj(cm).data.materials]
    else:
        mat_name_start = "Bricker_{n}{f}".format(n=n, f="f_%(cur_frame)s" % locals() if cur_frame else "")
        return [mat for mat in bpy.data.materials if mat.name.startswith(mat_name_start)]
