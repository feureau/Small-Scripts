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

# Module imports
from .property_groups import *
from .preferences import *
from .report_error import *
# from ..ui import *
from ..classes import *


classes = [
    # operators
    BRICKSCULPT_OT_run_tool,
    BRICKSCULPT_OT_confirm_cancel,
    BRICKSCULPT_OT_choose_paintbrush_material,
    # lib
    BrickSculptProperties,
    BRICKSCULPT_AP_preferences,
    SCENE_OT_report_error,
    SCENE_OT_close_report_error,
]
