# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

bl_info =  {'name': 'Onion Skin Tools for 2.8',
            'author': 'Joel Daniels',
            'version': ( 0, 2, 2, 4),
            'blender': ( 2, 83, 0),
            'category': 'Animation',
            'location': '3D View -> Right sidebar -> OST tab',
            'description': 'A set of tools for viewport onion skinning'}



if "bpy" not in locals():
    import bpy
    from . import util
    from . import props
    from . import operators
    from . import ui
else:
    import imp
    imp.reload( util)
    imp.reload( props)
    imp.reload( operators)
    imp.reload( ui)

from mathutils import Vector
from bpy.props import PointerProperty
from bpy.app.handlers import persistent

#-------------------------------------------------
# Handler for updating materials on frame change.
#-------------------------------------------------
@persistent
def os_mats_set( scene):
    ost = scene.ost            
    # Run the material settings calculation on the onion skinning objects.
    sets_collection = ost.sets_collection
    
    for char_set in sets_collection.sets:
        obs = [ bpy.data.objects[ item.ob] for item in char_set.final_obs]
        util.calc_mat( scene, char_set, obs)
    obs = [ bpy.data.objects[ item.ob] for item in ost.final_obs]
    util.calc_mat( scene, ost, obs)


#-------------------------------------------------
# Handler for resetting modal operator status.
#-------------------------------------------------
@persistent
def unset_auto_update( dummy):
    bpy.context.scene.ost.auto_update_on = False
            
def register():
    props.register()
    operators.register()
    ui.register()
    bpy.types.Scene.ost = PointerProperty( type = props.OSTProps)
    bpy.app.handlers.frame_change_post.append( os_mats_set)
    bpy.app.handlers.load_post.append( unset_auto_update)
    
def unregister():
    props.unregister()
    ui.unregister()
    operators.unregister()
    del bpy.types.Scene.ost
    bpy.app.handlers.frame_change_post.remove( os_mats_set)
    bpy.app.handlers.load_post.remove( unset_auto_update)
    
if __name__ == "__main__":
    register()
