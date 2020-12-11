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

# Module imports
from .property_groups import *
from .preferences import *
from .report_error import *
from ..ui import *
from ..operators import *
from ..operators.customization_tools import *
from ..operators.overrides import *
from ..functions.common import *
from ..functions.general import *


classes = [
    # bricker/operators
    populate_mat_obj.BRICKER_OT_populate_mat_obj,
    bake.BRICKER_OT_bake_model,
    bevel.BRICKER_OT_bevel,
    brickify.BRICKER_OT_brickify,
    generate_brick.BRICKER_OT_generate_brick,
    brickify_in_background.BRICKER_OT_brickify_in_background,
    brickify_in_background.BRICKER_OT_stop_brickifying_in_background,
    cache.BRICKER_OT_clear_cache,
    delete_model.BRICKER_OT_delete_model,
    debug_toggle_view_source.BRICKER_OT_debug_toggle_view_source,
    export_ldraw.BRICKER_OT_export_ldraw,
    apply_material.BRICKER_OT_apply_material,
    redraw_custom_bricks.BRICKER_OT_redraw_custom_bricks,
    refresh_model_info.BRICKER_OT_refresh_model_info,
    revert_settings.BRICKER_OT_revert_settings,
    boollist_actions.BRICKER_OT_bool_list_action,
    cmlist_actions.BRICKER_OT_cm_list_action,
    cmlist_actions.CMLIST_OT_copy_settings_to_others,
    cmlist_actions.CMLIST_OT_copy_settings,
    cmlist_actions.CMLIST_OT_paste_settings,
    cmlist_actions.CMLIST_OT_select_bricks,
    cmlist_actions.CMLIST_OT_link_animated_model,
    cmlist_actions.CMLIST_OT_link_frames,
    matlist_actions.BRICKER_OT_matlist_actions,
    test_brick_generators.BRICKER_OT_test_brick_generators,
    update_booleans.BRICKER_OT_update_booleans,
    initialize.BRICKER_OT_initialize,
    mass_generate.BRICKER_OT_mass_generate,
    # bricker/operators/customization_tools
    change_brick_material.BRICKER_OT_change_brick_material,
    change_brick_type.BRICKER_OT_change_brick_type,
    BRICKER_OT_draw_adjacent,
    BRICKER_OT_merge_bricks,
    BRICKER_OT_redraw_bricks,
    BRICKER_OT_select_bricks_by_size,
    BRICKER_OT_select_bricks_by_type,
    BRICKER_OT_split_bricks,
    BRICKER_OT_bricksculpt_null,
    # bricker/operators/overrides
    delete_object.OBJECT_OT_delete_override,
    duplicate_object.OBJECT_OT_duplicate_override,
    duplicate_object.OBJECT_OT_duplicate_move_override,
    # move_to_layer.OBJECT_OT_move_to_layer_override,
    # move_to_layer.OBJECT_OT_move_to_layer,
    # bricker/lib
    BooleanProperties,
    CreatedModelProperties,
    BRICKER_AP_preferences,
    SCENE_OT_report_error,
    SCENE_OT_close_report_error,
    # bricker/ui
    BRICKER_MT_specials,
    BRICKER_UL_collections_tuple,
    VIEW3D_PT_bricker_brick_models,
    VIEW3D_PT_bricker_animation,
    VIEW3D_PT_bricker_model_transform,
    VIEW3D_PT_bricker_model_settings,
    VIEW3D_PT_bricker_smoke_settings,
    VIEW3D_PT_bricker_brick_types,
    VIEW3D_PT_bricker_detailing,
    VIEW3D_PT_bricker_booleans,
    # VIEW3D_PT_bricker_detailing_bevel,
    VIEW3D_PT_bricker_merge_settings,
    VIEW3D_PT_bricker_merge_alignment,
    VIEW3D_PT_bricker_materials,
    VIEW3D_PT_bricker_use_uv_map,
    VIEW3D_PT_bricker_included_materials,
    VIEW3D_PT_bricker_material_properties,
    VIEW3D_PT_bricker_supports,
    VIEW3D_PT_bricker_advanced,
    VIEW3D_PT_bricker_ray_casting,
    VIEW3D_PT_bricker_customize,
    VIEW3D_PT_bricker_legacy_customization_tools,
    VIEW3D_PT_bricker_model_info,
    VIEW3D_PT_bricker_export,
    BRICKER_UL_booleans,
    BRICKER_UL_created_models,
    MATERIAL_UL_matslots,
    VIEW3D_PT_bricker_debugging_tools,
    VIEW3D_PT_bricker_matrix_details,
]
