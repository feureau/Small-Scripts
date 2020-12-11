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
import time

# Module imports
from .common import *
from .general import *


def store_smoke_data(from_obj, to_obj):
    # get evaluated obj
    if b280():
        depsgraph = bpy.context.view_layer.depsgraph
        from_obj_eval = from_obj.evaluated_get(depsgraph)
    else:
        from_obj_eval = from_obj
    # store point cache for frame
    domain_settings = next((mod.domain_settings for mod in from_obj_eval.modifiers if is_smoke_domain(mod)), None)
    adapt = domain_settings.use_adaptive_domain
    obj_details_adapt = bounds(from_obj) if adapt else None
    smoke_data = {
        "density_grid": tuple(float(v) for v in foreach_get(domain_settings.density_grid)),
        "flame_grid": tuple(float(v) for v in foreach_get(domain_settings.flame_grid)),
        "color_grid": tuple(float(v) for v in foreach_get(domain_settings.color_grid)),
        "domain_resolution": tuple(domain_settings.domain_resolution),
        "use_adaptive_domain": adapt,
        "adapt_min": tuple(obj_details_adapt.min) if adapt else None,
        "adapt_max": tuple(obj_details_adapt.max) if adapt else None,
        "resolution_max": domain_settings.resolution_max,
    }
    if bpy.app.version[:2] < (2, 82):
        smoke_data["use_high_resolution"] = domain_settings.use_high_resolution
        smoke_data["amplify"] = domain_settings.amplify
    to_obj.smoke_data = compress_str(json.dumps(smoke_data))


# code adapted from https://github.com/bwrsandman/blender-addons/blob/master/render_povray/render.py
def get_smoke_info(source):
    if not source.smoke_data:
        return [None] * 8

    smoke_data = json.loads(decompress_str(source.smoke_data))

    # get resolution
    domain_res = get_adjusted_res(smoke_data, smoke_data["domain_resolution"])
    adapt = smoke_data["use_adaptive_domain"]
    adapt_min = Vector(smoke_data["adapt_min"]) if adapt else None
    adapt_max = Vector(smoke_data["adapt_max"]) if adapt else None
    max_res_i = smoke_data["resolution_max"]
    max_res = Vector(domain_res) * (max_res_i / max(domain_res))
    max_res = get_adjusted_res(smoke_data, max_res)
    # get channel data
    density_grid = smoke_data["density_grid"]
    flame_grid = smoke_data["flame_grid"]
    color_grid = smoke_data["color_grid"]
    # density_grid = np.array(smoke_data["density_grid"]).reshape(domain_res[::-1])
    # flame_grid = np.array(smoke_data["flame_grid"]).reshape(domain_res[::-1])
    # color_grid = np.array(smoke_data["color_grid"]).reshape(domain_res[::-1] + [4])

    return density_grid, flame_grid, color_grid, domain_res, max_res, adapt, adapt_min, adapt_max


def get_adjusted_res(smoke_data, smoke_res):
    if bpy.app.version[:2] < (2, 82) and smoke_data["use_high_resolution"]:
        smoke_res = [int((smoke_data["amplify"] + 1) * i) for i in smoke_res]
    return smoke_res
