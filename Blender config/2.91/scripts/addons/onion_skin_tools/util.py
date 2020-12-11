import bpy
import blf
import bgl
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d as l3d_r2d

debug = False
def Debug( *args):
    if debug:
        print( " ".join( str(arg) for arg in args))

def me_transform( me, ob, inst_name):
    """Transform created meshes to match originals"""
    # Need to make sure the transformation is intact. 
    # Object center may not be on origin, so mesh could 
    # appear out of place.
    if inst_name != "":
        me.transform( ob.matrix_world)
        me.transform( bpy.data.objects[ inst_name].matrix_world)
    else:
        me.transform( ob.matrix_world)
# -------------------------
# Property update function.
# -------------------------
def get_objects( self, context):
    """Return object names for enum property 'keyed_object'.
    Only return keyed objects."""
    objects = []
    for object in context.scene.objects:
        if object.animation_data != None:
            objects.append( ( object.name, object.name, ""))
    return objects
    
#------------------
# Color conversion.
#------------------
def get_color( color, alpha):
    """Return a color tuple with alpha channel. Just saving text."""
    return ( color[0], color[1], color[2], alpha)

#----------------
# Nodes creation.
#----------------
def os_create_nodes( node_tree):
    """Create a node network for onion skinning."""
    nodes = node_tree.nodes
    if "BSDF_PRINCIPLED" in (node.type for node in nodes.values()):
        bsdf_node = next( node for node in nodes if node.type == "BSDF_PRINCIPLED")
        nodes.remove( bsdf_node)
    output_node = next( node for node in nodes if node.type == "OUTPUT_MATERIAL")
    output_node.location = Vector((350, 350))
    diffuse_node = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse_node.location = Vector((-100, 200))
    transp_node = nodes.new( "ShaderNodeBsdfTransparent")
    transp_node.inputs[0].default_value = (1, 1, 1, 1)
    transp_node.location = Vector((-100, 500))
    mix_node = nodes.new( "ShaderNodeMixShader")
    mix_node.location = Vector((90, 350))
    node_tree.links.new( diffuse_node.outputs[0], mix_node.inputs[2])
    node_tree.links.new( transp_node.outputs[0], mix_node.inputs[1])
    node_tree.links.new( mix_node.outputs[0], output_node.inputs[0])
    
#-------------------
# Update functions.
#-------------------
def update_xray( self, context):
    """Update x-ray for onion skin objects."""
    ost = context.scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        final_obs = char_set.final_obs
        settings = char_set
    else:
        final_obs = ost.final_obs
        settings = ost
    if final_obs.__len__():
        for item in final_obs:
            ob = bpy.data.objects[ item.ob]
            ob.show_in_front = settings.xray

def update_xray_orig( self, context):
    """Update x-ray for original objects in onion
       skinning list."""
    ost = context.scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        obs = char_set.obs_collection.obs
        settings = char_set
    else:
        obs = ost.obs_collection.obs
        settings = ost
    if obs.__len__():
        for item in obs:
            ob = bpy.data.objects[ item.name]
            ob.show_in_front = settings.xray_orig

def update_wire( self, context):
    """Update wireframe for onion skin objects."""
    ost = context.scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        final_obs = char_set.final_obs
        settings = char_set
    else:   
        final_obs = ost.final_obs
        settings = ost
    if final_obs.__len__():
        for item in final_obs:
            ob = bpy.data.objects[ item.ob]
            ob.show_wire = settings.wireframe
            ob.show_all_edges = settings.wireframe
                    
def update_color( self, context):
    """Update color for onion skin objects."""
    scene = context.scene
    ost = scene.ost
    update_nodes = False
    found_rendered = None
    if scene.render.engine in {'CYCLES', 'BLENDER_EEVEE'}:
      for window in bpy.data.window_managers[0].windows:
        for area in window.screen.areas:
          if area.type == 'VIEW_3D':
            for space in area.spaces:
                if hasattr(space, "shading") and space.shading.type in {'RENDERED', 'MATERIAL'}:
                    found_rendered = space
                    break
          if found_rendered:
            update_nodes = True
            break
            
    range_start = ( ost.orig_frame - ost.bwd_range) if \
                  ( ost.direction == 'both' or \
                  ost.direction == 'backward') \
                  else ost.orig_frame
    range_end =   ( ost.fwd_range + 1 + ost.orig_frame) if \
                  ( ost.direction == 'both' or \
                  ost.direction == 'forward') \
                  else ( ost.orig_frame + 1)
    mats = []
    current_frame = scene.frame_current
    if ost.use_sets:
        char_set = ost.sets_collection.active
        mats = [ bpy.data.materials[ item.mat] for item in char_set.final_mats]
        settings = char_set
    else:
        mats = [ bpy.data.materials[ item.mat] for item in ost.final_mats]
        settings = ost
    for frame_mat in mats:
        frame = int(frame_mat.name[:4])
        nodes = frame_mat.node_tree.nodes
        if frame < current_frame:
            frame_mat.diffuse_color = get_color( settings.bwd_color, 
                                                 frame_mat.diffuse_color[3])
            if update_nodes:
                nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( settings.bwd_color, 
                                                 frame_mat.diffuse_color[3])
        elif frame > current_frame:
            frame_mat.diffuse_color = get_color( settings.fwd_color, 
                                                 frame_mat.diffuse_color[3])
            if update_nodes:
                nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( settings.fwd_color, 
                                                 frame_mat.diffuse_color[3])
        

                                                 
def calc_mat( scene, settings, obs):
    """Function for calculating and setting transparency."""
    use_transp_range = settings.use_transp_range
    transp_range = settings.transp_range
    show_transp = settings.show_transp
    bwd_color = settings.bwd_color
    fwd_color = settings.fwd_color
    update_nodes = False
    found_rendered = None
    if scene.render.engine in {'CYCLES', 'BLENDER_EEVEE'}:
      for window in bpy.data.window_managers[0].windows:
        for area in window.screen.areas:
          if area.type == 'VIEW_3D':
            for space in area.spaces:
                if hasattr(space, "shading") and space.shading.type in {'RENDERED', 'MATERIAL'}:
                    found_rendered = space
                    break
          if found_rendered:
            update_nodes = True
            break
            
    if obs.__len__() > 0:
        frames = [ int( ob.name[:4]) for ob in obs]
        frames.sort()
        range_start = frames[0]
        range_end = frames[-1]    
        current_frame = scene.frame_current
        
        for frame_ob in obs:
            frame_mat = frame_ob.material_slots[0].material
            nodes = frame_mat.node_tree.nodes
            frame = int(frame_ob.name[:4])
            if not use_transp_range:    
                if frame < current_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    if show_transp:
                        alpha = (( frame - range_start + 1) / ( current_frame - range_start + 1)) * settings.transp_factor
                    else:
                        alpha = 1
                    frame_mat.diffuse_color = get_color( bwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( bwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
                    frame_ob.hide_viewport = True if ( settings.hide_before or settings.hide_all) else False   
                elif frame > current_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    if show_transp:
                        alpha = (( range_end + 1 - frame) / ( range_end + 1 - current_frame)) * settings.transp_factor
                    else: 
                        alpha = 1
                    frame_mat.diffuse_color = get_color( fwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( fwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
                    frame_ob.hide_viewport = True if ( settings.hide_after or settings.hide_all) else False    
                else: 
                    frame_ob.hide_viewport = True 
                    alpha = 0    
                    frame_mat.diffuse_color = get_color( fwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( fwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
            else:
                if frame < current_frame:
                    frame_ob.hide_viewport = True if ( settings.hide_before or settings.hide_all) else False    
                    if frame < ( current_frame - transp_range):
                        alpha = 0
                    else:
                        if show_transp:
                            alpha = (( transp_range - ( current_frame - frame) + 1) / ( transp_range + 1)) * settings.transp_factor
                        else:
                            alpha = 1
                    frame_mat.diffuse_color = get_color( bwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( bwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
                elif frame > current_frame:
                    frame_ob.hide_viewport = True if ( settings.hide_after or settings.hide_all) else False    
                    if frame > ( current_frame + transp_range):
                        alpha = 0
                    else:
                        if show_transp:
                            alpha = (( current_frame + transp_range + 1 - frame) / \
                            ( current_frame + transp_range + 1 - current_frame)) * settings.transp_factor
                        else: 
                            alpha = 1
                    frame_mat.diffuse_color = get_color( fwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( fwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
                else:
                    frame_ob.hide_viewport = True  
                    alpha = 0
                    frame_mat.diffuse_color = get_color( fwd_color, alpha)
                    if update_nodes:
                        nodes['Diffuse BSDF'].inputs['Color'].default_value = get_color( fwd_color, alpha)
                        nodes['Mix Shader'].inputs['Fac'].default_value = alpha
                        
                        
def calc_transp( scene, settings, mats):
    '''Function to calculate transparency'''
    ost = scene.ost
    # Check if updating nodes.
    update_nodes = False
    found_rendered = None
    if scene.render.engine in {'CYCLES', 'BLENDER_EEVEE'}:
      for window in bpy.data.window_managers[0].windows:
        for area in window.screen.areas:
          if area.type == 'VIEW_3D':
            for space in area.spaces:
                if hasattr(space, "shading") and space.shading.type in {'RENDERED', 'MATERIAL'}:
                    found_rendered = space
                    break
          if found_rendered:
            update_nodes = True
            break
    
    show_transp = settings.show_transp
    use_transp_range = settings.use_transp_range
    transp_range = settings.transp_range
    frames = [ int( frame_mat.name[:4]) for frame_mat in mats]
    if len( frames) == 0:
        return
    frames.sort()
    current_frame = scene.frame_current
    range_start = frames[0]
    range_end = frames[-1]    
    current_frame = scene.frame_current
    for frame_mat in mats:
        frame = int(frame_mat.name[:4])
        nodes = frame_mat.node_tree.nodes
        if not use_transp_range:
            if frame < current_frame:
                # Reduce range, but %-% rather than to 0-1.
                alpha = (( frame - range_start + 1) / \
                ( current_frame - range_start + 1)) * settings.transp_factor
                if not show_transp:
                    alpha = 1
            elif frame > current_frame:
                # Reduce range, but %-% rather than to 0-1.
                alpha = (( range_end + 1 - frame) / \
                ( range_end + 1 - current_frame)) * settings.transp_factor
                if not show_transp:
                    alpha = 1
            else: 
                # Current frame.
                alpha = 0

        else:
            # Using visilibity range.
            if frame < current_frame:
                if frame < ( current_frame - transp_range):
                    alpha = 0
                else:
                    alpha = (( transp_range - ( current_frame - frame) + 1) / ( transp_range + 1)) * settings.transp_factor
                    if not show_transp:
                        alpha = 1
                   
            elif frame > current_frame:
                if frame > ( current_frame + transp_range):
                    alpha = 0
                else:
                    alpha = (( current_frame + transp_range + 1 - frame) / \
                    ( current_frame + transp_range + 1 - current_frame)) * settings.transp_factor
                    if not show_transp:
                        alpha = 1
            else:
                # Current frame.
                alpha = 0
        frame_mat.diffuse_color = get_color( frame_mat.diffuse_color, alpha)
        if update_nodes:
            nodes['Mix Shader'].inputs['Fac'].default_value = alpha
            
def update_transp( self, context):
    """Update transparency for onion skin objects."""
    scene = context.scene
    ost = scene.ost
    if ost.use_sets:
        settings = ost.sets_collection.active
        mats = [ bpy.data.materials[ item.mat] for item in settings.final_mats]
    else:  
        settings = ost
        mats = [ bpy.data.materials[ item.mat] for item in settings.final_mats]
    calc_transp( scene, settings, mats)
        
def update_hide_before( self, context):
    """Hide or show all onion skin objects before current frame."""
    scene = context.scene
    ost = scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        obs = [ bpy.data.objects[ item.ob] for item in char_set.final_obs]
        settings = char_set
    else:
        obs = [ bpy.data.objects[ item.ob] for item in ost.final_obs]
        settings = ost
    for frame_ob in obs:
        frame = int(frame_ob.name[:4])
        if frame < scene.frame_current:
            frame_ob.hide_viewport = True if ( settings.hide_before or settings.hide_all) else False
    
def update_hide_after( self, context):
    """Hide or show all onion skin objects after current frame."""
    scene = context.scene
    ost = scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        obs = [ bpy.data.objects[ item.ob] for item in char_set.final_obs]
        settings = char_set
    else: 
        obs = [ bpy.data.objects[ item.ob] for item in ost.final_obs]
        settings = ost
    for frame_ob in obs:
        frame = int(frame_ob.name[:4])
        if frame > scene.frame_current:
            frame_ob.hide_viewport = True if ( settings.hide_after or settings.hide_all) else False

def update_hide_all( self, context):
    """Hide or show all onion skin objects."""
    scene = context.scene
    ost = scene.ost
    if ost.use_sets:
        char_set = ost.sets_collection.active
        obs = [ bpy.data.objects[ item.ob] for item in char_set.final_obs]
        settings = char_set
    else:
        obs = [ bpy.data.objects[ item.ob] for item in ost.final_obs]
        settings = ost
    for frame_ob in obs:
        frame_ob.hide_viewport = True if settings.hide_all else False

        
#-------------------
# bgl Utilities.
#-------------------
def draw_frames( self, context):
    """blf/bgl callback for drawing keyframe numbers above objects.
    Called from VIEW3D_OT_DrawFramesOST."""
    scene = context.scene
    ost = scene.ost
    # Check that onion skinning hasn't been removed while running modal.
    if ost.use_sets and ost.sets_collection.sets.__len__() == 0:
        ost.display_frames = False
    if ost.use_sets and ost.sets_collection.active.final_collection_name == "":
        ost.display_frames = False
    if not ost.use_sets and ost.final_collection_name == "":
        ost.display_frames = False
    if ost.display_frames:
        current_frame = scene.frame_current
        if ost.use_sets:
            settings = ost.sets_collection.active
        else:
            settings = ost
        use_transp_range = settings.use_transp_range
        transp_range = settings.transp_range
        # Frames to display.
        frames = [ final_frame.frame for final_frame in settings.final_frames]
        frames.sort()
        range_start = frames[0]
        range_end = frames[-1] 
        region = context.region
        rv3d = context.space_data.region_3d
        bgl.glEnable( bgl.GL_BLEND)
        blf.size(0, ost.font_size, 72)
        blf.color(0, 1.0, 1.0, 1.0, 0.75)
        for final_frame in settings.final_frames:
            mod_co = Vector( (final_frame.co[0], final_frame.co[1], final_frame.co[2] + (ost.font_height - 1)))
            co = l3d_r2d( region, rv3d, mod_co)
            blf.position( 0, co[0], co[1], 0)
            if not use_transp_range:    
                if final_frame.frame < current_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    alpha = (( final_frame.frame - range_start + 1) / \
                    ( current_frame - range_start + 1)) * settings.transp_factor   
                elif final_frame.frame > current_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    alpha = (( range_end + 1 - final_frame.frame) / ( range_end + 1 - current_frame)) * settings.transp_factor 
                else: 
                    alpha = 1  
            else:
                if final_frame.frame < current_frame:
                    if final_frame.frame < ( current_frame - transp_range):
                        alpha = 0
                    else:
                        alpha = (( transp_range - ( current_frame - final_frame.frame) + 1) / \
                        ( transp_range + 1)) * settings.transp_factor
                    
                elif final_frame.frame > current_frame: 
                    if final_frame.frame > ( current_frame + transp_range):
                        alpha = 0
                    else:
                        alpha = (( current_frame + transp_range + 1 - final_frame.frame) / \
                        ( current_frame + transp_range + 1 - current_frame)) * settings.transp_factor
                else:
                    alpha = 1
            if final_frame.frame == context.scene.frame_current:
                blf.color(0, 0.8, 0.9, 0.1, alpha)
                blf.draw( 0, str( final_frame.frame))
            else:
                blf.color(0, 1.0, 1.0, 1.0, alpha)
                blf.draw( 0, str( final_frame.frame))
    # Restore defaults.
    bgl.glDisable( bgl.GL_BLEND)
    
        
def calc_frame_loc( verts, scene):
    """
    verts = list of vertex coordinates from current object.
    Calculate average vertex vector, get the highest z coordinate.
    Return loc for drawing keyframe number. 
    """
    verts_z_dict = { verts[i][2]: i for i in range( len( verts))}
    verts_z = [v for v in verts_z_dict.keys()]
    # Look up the highest z coordinate we found
    verts_z.sort()
    hi_z = verts_z[ -1]
    z = hi_z + ( 0.5 * scene.unit_settings.scale_length)
    # Look up the x and y coordinates of the highest z.
    #x, y = verts[ verts_z_dict[ hi_z]][ :-1]
    # Average the x and y coordinates
    x = 0
    y = 0
    for vert in verts:
      x += vert[0]
      y += vert[1]
    x /= len( verts)
    y /= len( verts)
    return Vector((x, y, z))

#------------------------------------------------
# Removal Utilities. Obsolete for versions < 2.8.
#------------------------------------------------
def remove_ob( ob):
    if bpy.app.version[1] >= 78:
        bpy.data.objects.remove( ob, True)

def remove_mesh( mesh):
    if bpy.app.version[1] >= 78:
        bpy.data.meshes.remove( mesh, True)    

def remove_mat( mat):
    if bpy.app.version[1] >= 78:
        bpy.data.materials.remove( mat, True)

