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

# LDR code reference: https://www.ldraw.org/article/547.html

# System imports
# NONE!

# Blender imports
import bpy
from bpy.props import *

# Module imports
# NONE!


# Create custom property group
class BrickSculptProperties(bpy.types.PropertyGroup):
    cancel_session_changes = BoolProperty(
        name="Cancel Session Changes",
        description="Cancel changes made in the active BrickSculpt session",
        default=False,
    )
    running_active_session = BoolProperty(
        name="Running Active BrickSculpt Session",
        description="Session of BrickSculpt is currently running",
        default=False,
    )
    paintbrush_mat = PointerProperty(
        type=bpy.types.Material,
        name="Paintbrush Material",
        description="Material for the BrickSculpt paintbrush tool",
    )
    choosing_material = BoolProperty(
        name="Choosing material",
        description="Currently running the 'choose new material' operator",
        default=False,
    )
