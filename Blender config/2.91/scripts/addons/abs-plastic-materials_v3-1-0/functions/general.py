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

# Module imports
from .common import *


def import_im_textures(im_names=["ABS Fingerprints and Dust.jpg", "ABS Scratches.jpg"], replace_existing=False):
    im_path = os.path.join(get_addon_directory(), "lib")
    for im_name in im_names:
        im = bpy.data.images.get(im_name)
        preexisting_im = im is not None
        # if image texture already exists
        if preexisting_im:
            if replace_existing:
                # remove existing image texture
                bpy.data.images.remove(im)
            else:
                # skip this image texture
                continue
        bpy.ops.image.open(filepath=os.path.join(im_path, im_name))
        im = bpy.data.images.get(im_name)
        if preexisting_im:
            im.update()
