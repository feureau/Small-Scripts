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

def add_keymaps(km):
    km.keymap_items.new("bricksculpt.run_tool", "D", "PRESS", shift=True, alt=True).properties.mode = "DRAW"
    km.keymap_items.new("bricksculpt.run_tool", "M", "PRESS", shift=True, alt=True).properties.mode = "MERGE_SPLIT"
    km.keymap_items.new("bricksculpt.run_tool", "P", "PRESS", shift=True, alt=True).properties.mode = "PAINT"
