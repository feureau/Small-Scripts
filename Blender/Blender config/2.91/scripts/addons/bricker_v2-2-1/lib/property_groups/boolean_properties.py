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
from bpy.props import *

# Module imports
from ...functions.property_callbacks import *


# Create custom property group
class BooleanProperties(bpy.types.PropertyGroup):
    # BOOLEAN ITEM SETTINGS
    name = StringProperty(update=uniquify_name)
    id = IntProperty()
    idx = IntProperty()

    # NAME OF SOURCE
    type = EnumProperty(
        name="Type",
        description="",
        items=[
            ("OBJECT", "Object", "", 0),
            ("MODEL", "Model", "", 1),
        ],
        default="OBJECT",
    )
    object = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH",
        name="Object",
        description="Name of the object to boolean against",
    )
    model_name = StringProperty(
        # type=bpy.types.Object,
        # poll=lambda self, object: object.type == "MESH",
        name="Model Name",
        description="Name of the Bricker model to bool against",
    )

    # internal
    object_dup = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH",
    )
