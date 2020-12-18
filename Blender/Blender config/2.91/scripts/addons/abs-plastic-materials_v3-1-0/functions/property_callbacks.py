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

# System imports
# NONE!

# Blender imports
import bpy
from bpy.props import *
from ..lib.mat_properties import mat_properties

# Module imports
from .common import *
from .general import *


def get_mat_names(include_undefined=True):
    scn = bpy.context.scene
    materials = bpy.props.abs_mats_common.copy()
    materials += bpy.props.abs_mats_transparent
    materials += bpy.props.abs_mats_uncommon
    if include_undefined:
        materials += bpy.props.abs_mats_undefined
    return materials


def update_abs_subsurf(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        nodes = mat.node_tree.nodes
        target_node = nodes.get("ABS Dialectric")
        if target_node is None:
            continue
        sss_input = target_node.inputs.get("SSS Amount")
        if sss_input is None:
            continue
        sss_default = mat_properties[mat_name]["SSS Amount"] if "SSS Amount" in mat_properties[mat_name] else 0
        sss_input.default_value = sss_default * scn.abs_subsurf


def update_abs_roughness(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        nodes = mat.node_tree.nodes
        target_node = nodes.get("ABS Dialectric") or nodes.get("ABS Transparent")
        if target_node is None:
            continue
        input1 = target_node.inputs.get("Rough 1")
        if input1 is None:
            continue
        input1.default_value = scn.abs_roughness * (50 if "Metallic" in mat.name else (3 if mat.name == "ABS Plastic Trans-Yellowish Clear" else 1))


def update_abs_randomize(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        nodes = mat.node_tree.nodes
        target_node = nodes.get("ABS Dialectric") or nodes.get("ABS Transparent")
        if target_node is None:
            continue
        input1 = target_node.inputs.get("Random")
        if input1 is None:
            continue
        input1.default_value = scn.abs_randomize


def update_abs_fingerprints(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        nodes = mat.node_tree.nodes
        target_node1 = nodes.get("ABS Dialectric") or nodes.get("ABS Transparent")
        target_node2 = nodes.get("ABS Bump")
        if target_node1 is None or target_node2 is None:
            continue
        input1 = target_node1.inputs.get("Fingerprints")
        input2 = target_node2.inputs.get("Fingerprints")
        if input1 is None or input2 is None:
            continue
        input1.default_value = scn.abs_fingerprints / (8 if "Metallic" in mat.name else 1)
        input2.default_value = scn.abs_fingerprints * scn.abs_displace


def update_abs_displace(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        target_node = nodes.get("ABS Bump")
        if target_node is None:
            continue
        noise = target_node.inputs.get("Noise")
        waves = target_node.inputs.get("Waves")
        scratches = target_node.inputs.get("Scratches")
        fingerprints = target_node.inputs.get("Fingerprints")
        concavity = target_node.inputs.get("Concavity")
        if noise is None or waves is None or scratches is None or fingerprints is None:
            continue
        noise.default_value = scn.abs_displace * (20 if "Metallic" in mat.name else 1)
        waves.default_value = scn.abs_displace
        scratches.default_value = scn.abs_displace
        fingerprints.default_value = scn.abs_fingerprints * scn.abs_displace * 4
        concavity.default_value = scn.abs_displace
        # disconnect displacement node if not used
        try:
            displace_in = nodes["Material Output"].inputs["Displacement"]
            displace_out = nodes["Displacement"].outputs["Displacement"] if b280() else target_node.outputs["Color"]
        except KeyError:
            continue
        if scn.abs_displace == 0:
            for l in displace_in.links:
                links.remove(l)
        else:
            links.new(displace_out, displace_in)


def update_abs_uv_scale(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        n_scale = mat.node_tree.nodes.get("ABS Uniform Scale")
        if n_scale is None:
            continue
        n_scale.inputs[0].default_value = scn.abs_uv_scale


def toggle_save_datablocks(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is not None:
            mat.use_fake_user = scn.save_datablocks


def update_viewport_transparency(self, context):
    scn = context.scene
    for mat_name in bpy.props.abs_mats_transparent:
        mat = bpy.data.materials.get(mat_name)
        if mat is not None:
            mat.diffuse_color[-1] = 0.75 if scn.abs_viewport_transparency else 1

def update_texture_mapping(self, context):
    scn = context.scene
    for mat_name in get_mat_names():
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            continue
        n_tex = mat.node_tree.nodes.get("Texture Coordinate")
        if n_tex is None:
            continue
        n_scale = mat.node_tree.nodes.get("ABS_Scale")
        if n_scale is None:
            continue
        links = mat.node_tree.links
        links.new(n_tex.outputs[scn.abs_mapping], n_scale.inputs["Vector"])
    groups_to_update = ("ABS_Fingerprint", "ABS_Specular Map")
    for ng_name in groups_to_update:
        ng = bpy.data.node_groups.get(ng_name)
        if ng is None:
            continue
        n_image = ng.nodes.get("ABS Fingerprints and Dust")
        n_image.projection = "FLAT" if scn.abs_mapping == "UV" else "BOX"



def update_fd_image(scn, context):
    import_im_textures(["ABS Fingerprints and Dust.jpg"])
    im = bpy.data.images.get("ABS Fingerprints and Dust.jpg")
    scn = context.scene
    res = round(scn.abs_fpd_quality, 1)
    resized_img = get_detail_image(res, im)
    fnode = bpy.data.node_groups.get("ABS_Fingerprint")
    snode = bpy.data.node_groups.get("ABS_Specular Map")
    image_node1 = fnode.nodes.get("ABS Fingerprints and Dust")
    image_node2 = snode.nodes.get("ABS Fingerprints and Dust")
    for img_node in (image_node1, image_node2):
        if img_node is None:
            continue
        img_node.image = resized_img


def update_s_image(scn, context):
    import_im_textures(["ABS Scratches.jpg"])
    im = bpy.data.images.get("ABS Scratches.jpg")
    scn = context.scene
    res = round(scn.abs_s_quality, 1)
    resized_img = get_detail_image(res, im)
    fnode = bpy.data.node_groups.get("ABS_Scratches")
    if fnode is None:
        return
    img_node = fnode.nodes.get("ABS Scratches")
    if img_node is None:
        return
    img_node.image = resized_img


def get_detail_image(res, full_img):
    # create smaller fingerprints/dust images
    if res == 1:
        return full_img
    new_img_name = "{im_name} ({res}).jpg".format(im_name=full_img.name.replace(".jpg", ""), res=res)
    detail_img_scaled = bpy.data.images.get(new_img_name)
    if detail_img_scaled and not detail_img_scaled.has_data:
        bpy.data.images.remove(detail_img_scaled)
        detail_img_scaled = None
    if detail_img_scaled is None:
        detail_img_scaled = duplicate_image(full_img, new_img_name)
        new_size = Vector(full_img.size) * res
        detail_img_scaled.scale(new_size.x, new_size.y)
        detail_img_scaled.use_fake_user = True
    return detail_img_scaled
