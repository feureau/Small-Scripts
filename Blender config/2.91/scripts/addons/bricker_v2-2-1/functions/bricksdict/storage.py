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
import marshal

# Blender imports
import bpy

# Module imports
from .generate import *
from .modify import *
from .exposure import *
from ...lib.caches import bricker_bfm_cache, cache_exists


def get_bricksdict(cm, d_type="MODEL", cur_frame=None):
    """ retrieve bricksdict from cache if possible, else return None """
    scn = bpy.context.scene
    # if bricksdict can be pulled from cache
    if not matrix_really_is_dirty(cm) and cache_exists(cm) and not (cm.anim_is_dirty and "ANIM" in d_type):
        # try getting bricksdict from light cache, then deep cache
        bricksdict = bricker_bfm_cache.get(cm.id) or marshal.loads(bytes.fromhex(cm.bfm_cache))
        # if animated, index into that dict
        if "ANIM" in d_type and bricksdict is not None:
            adjusted_frame_current = get_anim_adjusted_frame(cur_frame, cm.last_start_frame, cm.last_stop_frame, cm.last_step_frame)
            try:
                bricksdict = bricksdict[str(adjusted_frame_current)]
            except KeyError:
                return None
        return bricksdict
    # else, return nothing
    return None


def light_to_deep_cache(bricker_bfm_cache, cm_ids=None):
    """ send bricksdict from blender cache to python cache for quick access """
    scn = bpy.context.scene
    num_pushed_ids = 0
    cm_ids = cm_ids or bricker_bfm_cache.keys()
    for cm_id in cm_ids:
        # get cmlist item referred to by object
        cm = get_item_by_id(scn.cmlist, cm_id)
        if not cm:
            continue
        # save last cache to cm.bfm_cache
        cm.bfm_cache = marshal.dumps(bricker_bfm_cache[cm_id]).hex()
        num_pushed_ids += 1
    if num_pushed_ids > 0:
        print("[Bricker] pushed {num_keys} {pluralized_dicts} from light cache to deep cache".format(num_keys=num_pushed_ids, pluralized_dicts="dict" if num_pushed_ids == 1 else "dicts"))


def deep_to_light_cache(bricker_bfm_cache, cm):
    """ send bricksdict from python cache to blender cache for saving to file """
    # make sure there is something to store to light cache
    if cm.bfm_cache == "":
        return
    try:
        bricksdict = marshal.loads(bytes.fromhex(cm.bfm_cache))
        bricker_bfm_cache[cm.id] = bricksdict
    except Exception as e:
        print("ERROR in deep_to_light_cache:", e)
    cm.bfm_cache = ""


def cache_bricks_dict(action, cm, bricksdict, cur_frame=None):
    """ store bricksdict in light python cache for future access """
    scn = bpy.context.scene
    if action in ("CREATE", "UPDATE_MODEL"):
        bricker_bfm_cache[cm.id] = bricksdict
    elif action in ("ANIMATE", "UPDATE_ANIM"):
        if (cm.id not in bricker_bfm_cache.keys() or
           type(bricker_bfm_cache[cm.id]) != dict):
            bricker_bfm_cache[cm.id] = {}
        bricker_bfm_cache[cm.id][str(cur_frame)] = bricksdict
