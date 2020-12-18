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
# NONE!

# Blender imports
import bpy

# Module imports
from .common import *
from ..lib.caches import *


def clear_cache(cm, brick_mesh=True, light_matrix=True, deep_matrix=True, rgba_vals=True, images=True, dupes=True):
    """clear caches for cmlist item"""
    # clear light brick mesh cache
    if brick_mesh:
        bricker_mesh_cache[cm.id] = None
    # clear light matrix cache
    if light_matrix:
        bricker_bfm_cache[cm.id] = None
    # clear deep matrix cache
    if deep_matrix:
        cm.bfm_cache = ""
    # clear rgba vals cache
    if rgba_vals:
        bricker_rgba_vals_cache[cm.id] = None
    # clear image cache
    if images:
        clear_pixel_cache()
    # remove caches of source model from data
    if dupes:
        if cm.model_created:
            delete(bpy.data.objects.get("Bricker_%(n)s__dup__"), remove_meshes=True)
        elif cm.animated:
            for cf in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame):
                delete(bpy.data.objects.get("Bricker_%(n)s_f_%(cf)s"), remove_meshes=True)


def clear_caches(brick_mesh=True, light_matrix=True, deep_matrix=True, images=True, dupes=True):
    """clear all caches in cmlist"""
    scn = bpy.context.scene
    for cm in scn.cmlist:
        clear_cache(cm, brick_mesh=brick_mesh, light_matrix=light_matrix, deep_matrix=deep_matrix, images=images, dupes=dupes)
