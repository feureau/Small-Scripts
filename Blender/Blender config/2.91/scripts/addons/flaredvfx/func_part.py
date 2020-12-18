#####################################################

# <FLARED is an add-on for Blender that creates lens flare VFX in Eevee.>
# Copyright (C) <2019-2020>  <Beniamino Della Torre e Alfonso Annarumma>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# You can contact the creator of Flared here: blenderlensflare@gmail.com

#####################################################


import bpy
import os
import random

from . import (
    flare_a,
    flare_b,
    flare_c,
    flare_d,
    flare_e,
    flare_f,
    flare_g,
    flare_h,
    flare_i,
    particle,
    function,
)
def update_particle(self, context):
    colls = bpy.data.collections
    coll = colls[self.id]
    suffix = function.find_suffix(coll)
    obs = coll.all_objects
    lensflareprop = self
    type = lensflareprop.flared_type
    if type == 'A':
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'B':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'C':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'D':
        #print("Not implemend")
        particle.flare_d_particle(obs, context, lensflareprop, suffix)
    if type == 'E':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'G':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'H':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
    if type == 'I':
        #print("Not implemend")
        particle.flare_particle(obs, context, lensflareprop, suffix)
