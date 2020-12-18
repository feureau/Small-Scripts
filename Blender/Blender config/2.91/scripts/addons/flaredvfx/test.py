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

def copy_prop(context):
    
    scene = context.scene
    idx = scene.lensflareitems_index
    
    items = scene.lensflareitems
    active = items[idx]
    act_props = active.light.lensflareprop
    for item in items:
        print("ok")
        props = item.light.lensflareprop
        keys = props.keys()
        for key in keys:
            if item != active and item.select and props.flared_type==act_props.flared_type:
                props[key] = act_props[key]
                
context = bpy.context
copy_prop(context)