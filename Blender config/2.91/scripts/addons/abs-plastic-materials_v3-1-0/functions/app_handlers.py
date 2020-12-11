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
from os.path import join, exists, split
import codecs

# Blender imports
import bpy
from bpy.app.handlers import persistent
from .property_callbacks import *

# Module imports
# NONE!

# updater import, import safely
# Prevents popups for users with invalid python installs e.g. missing libraries
try:
	from ..addon_updater import Updater as updater
except Exception as e:
	print("ERROR INITIALIZING UPDATER")
	print(str(e))
	class Singleton_updater_none(object):
		def __init__(self):
			self.addon = None
			self.verbose = False
			self.invalidupdater = True # used to distinguish bad install
			self.error = None
			self.error_msg = None
			self.async_checking = None
		def clear_state(self):
			self.addon = None
			self.verbose = False
			self.invalidupdater = True
			self.error = None
			self.error_msg = None
			self.async_checking = None
		def run_update(self): pass
		def check_for_update(self): pass
	updater = Singleton_updater_none()
	updater.error = "Error initializing updater module"
	updater.error_msg = str(e)


@persistent
def verify_texture_data(scn):
    mat_names = get_mat_names()  # list of materials to append from 'abs_plastic_materials.blend'
    already_imported = [mn for mn in mat_names if bpy.data.materials.get(mn) is not None]
    if len(already_imported) > 0:
        update_fd_image(scn, bpy.context)
        update_s_image(scn, bpy.context)


@persistent
def validate_abs_plastic_materials(dummy):
	validated = False
	validation_file = join(get_addon_directory(), "lib", codecs.encode("nof_cynfgvp_chepunfr_irevsvpngvba.gkg", "rot13"))
	if exists(validation_file):
		verification_str = "Thank you for supporting my work and ongoing development by purchasing ABS Plastic Materials!\n"
		with open(validation_file) as f:
			validated = verification_str == codecs.encode(f.readline(), "rot13")
	if not validated:
		res = updater.run_update(
			force=False,
			revert_tag="demo",
			# callback=post_update_callback,
			clean=False,
		)
		folderpath, foldername = split(get_addon_directory())
		bpy.props.abs_validated = False


@persistent
def handle_upconversion(scn):
    # rename outdated ABS Plastic Material names
    pink_mat = bpy.data.materials.get('ABS Plastic Pink')
    if pink_mat is not None:
        pink_mat.name = 'ABS Plastic Dark Pink'
    orange_mat = bpy.data.materials.get('ABS Plastic Trans-Reddish Orange')
    if orange_mat is not None:
        orange_mat.name = 'ABS Plastic Trans-Orange'
