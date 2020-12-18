import bpy
import time
from .util import *

def run_update( operator, context, event):
    """Function called from VIEW3D_OT_RunOST to update onion skinning."""
    scene = operator.scene
    depsgraph = context.evaluated_depsgraph_get()
    try:
        ost = scene.ost
    except:
        scene = context.scene
        ost = scene.ost
    if ost.use_sets:
        active_set = ost.sets_collection.active
        if not active_set:
            # No set created.
            return
        obs_collection = active_set.obs_collection
        final_mats = active_set.final_mats
        final_obs = active_set.final_obs
        final_frames = active_set.final_frames
        final_collection_name = active_set.final_collection_name
        settings = active_set
    else:
        obs_collection = ost.obs_collection
        final_mats = ost.final_mats
        final_obs = ost.final_obs
        final_frames = ost.final_frames
        final_collection_name = ost.final_collection_name
        settings = ost
    start_time = time.time()
    
    # Update.
    sel_obs = [ [bpy.data.objects[ ob.name], ob.inst] for ob in obs_collection.obs]
    
    # Sort object names, frame numbers, materials.
    ob_names = [ item.ob for item in final_obs]
    ob_names.sort()
    obs = [ bpy.data.objects[ ob_name] for ob_name in ob_names]
    frames = [ f.frame for f in final_frames]
    frames.sort()
    mat_names = [ item.mat for item in final_mats]
    mat_names.sort()
    final_mats = [ bpy.data.materials[ mat_name] for mat_name in mat_names]
    current_frame = scene.frame_current
    
    # Scene collection to operate on.
    scene_collection = bpy.data.collections[ final_collection_name]
    
    frame_idx = 0
    for i in range ( frames.__len__()):
        scene.frame_set( frames[ i])
        # Remove object and mesh from scene.
        scene_collection.objects.unlink( obs[ i])
        mesh = obs[ i].data
        bpy.data.objects.remove( obs[ i], do_unlink = True)
        bpy.data.meshes.remove( mesh, do_unlink = True)
        # Regenerate object and mesh, relink to scene.
        verts_count = 0
        verts = []   # List of (x,y,z) tuples.
        edges = [] # List of 2-element tuples
        faces = [] # List of 3- or 4-element tuples
        smooth = []
        frame_mesh = bpy.data.meshes.new( "%04d_ost_mesh" % frames[ i])
        frame_mesh.materials.clear()
        frame_mesh.materials.append( final_mats[ i])
        
        for item in sel_obs:
            ob = item[0]
            inst_name = item[1]
            # Convert each object to mesh.
            ob_convert = ob.evaluated_get(depsgraph)
            me = ob_convert.to_mesh()
            me_transform( me, ob, inst_name)
            
            # Add the vertices, edges and polygons to the lists.
            verts.extend( [ vert.co[:] for vert in me.vertices])
            edges.extend( [ tuple( map( lambda x: x + verts_count, 
                            edge.vertices[:])) for edge in me.edges])
            faces.extend( [ tuple( map( lambda x: x + verts_count, 
                            poly.vertices[:])) for poly in me.polygons])
            smooth.extend( [ poly.use_smooth for poly in me.polygons])
            verts_count += me.vertices.__len__()
            #bpy.data.meshes.remove( me, do_unlink = True)
            ob_convert.to_mesh_clear()
            del me
        
        # Push the mesh data to the final mesh.
        frame_mesh.from_pydata( verts, edges, faces)
        frame_mesh.validate()
        frame_mesh.polygons.foreach_set( "use_smooth", smooth)
        if bpy.app.version[1] >= 81:
            frame_mesh.update(calc_edges=True, calc_edges_loose=True)
        elif bpy.app.version[1] == 80:
            frame_mesh.update(calc_edges=True, calc_edges_loose=True, calc_loop_triangles=True)
        
        # Create the object.
        if ost.use_sets:
            frame_ob = bpy.data.objects.new( "%04d_ost_%s_ob" % ( frames[ i], active_set.name), frame_mesh)
        else:
            frame_ob = bpy.data.objects.new( "%04d_ost_ob" % frames[ i], frame_mesh)
        # Link the object to the scene.
        scene_collection.objects.link( frame_ob)
        
        # Set object settings. Turn on object transparency.
        frame_ob.show_transparent = True if settings.show_transp else False
        frame_ob.show_in_front = settings.xray
        frame_ob.hide_select, frame_ob.hide_render = True, True
        
        # Store location for frame number for drawing frames.
        final_frames[ frame_idx].co = calc_frame_loc( verts, scene)
        frame_idx += 1
        
    scene.frame_set( current_frame)
    operator.transformed = False
    elapsed = time.time() - start_time
    
    
def run_onion_skinning( operator, context):
    """Function called from VIEW3D_OT_RunOST to run onion skinning."""
    scene = operator.scene
    depsgraph = context.evaluated_depsgraph_get()
    ost = scene.ost
    direction = ost.direction
    fwd_range = ost.fwd_range # Range of frames forward.
    bwd_range = ost.bwd_range # Range of frames backward.
    include_current = ost.include_current
    current_only = ost.current_only
    if not ost.keyed_only:
        step = ost.step # Frame step property. Minimum of 1.
    else:
        step = 1
    orig_frame = ost.orig_frame = scene.frame_current # Store current frame as "original" reference frame.
    
    if ost.use_sets:
        active_set = ost.sets_collection.active
        if not active_set:
            # No set created.
            return {'CANCELLED'}
        obs_collection = active_set.obs_collection
        final_mats = active_set.final_mats
        final_obs = active_set.final_obs
        if not operator.remove and len( final_obs) > 0 and not ost.current_only:
            # Already onion skinned, and not running only for current frame.
            return {'CANCELLED'}
        final_meshes = active_set.final_meshes
        final_frames = active_set.final_frames
        final_collection_name = active_set.final_collection_name
        settings = active_set
    else:
        obs_collection = ost.obs_collection
        final_mats = ost.final_mats
        final_obs = ost.final_obs
        if not operator.remove and len( final_obs) > 0 and not ost.current_only:
            # Already onion skinned, and not running only for current frame.
            return {'CANCELLED'}
        final_meshes = ost.final_meshes
        final_frames = ost.final_frames
        final_collection_name = ost.final_collection_name
        settings = ost
        
    if len( obs_collection.obs) == 0:
        # Nothing to onion skin, do nothing.
        if ost.use_sets:
            operator.report( {'INFO'}, "No objects in the character set's objects list.")
        else:
            operator.report( {'INFO'}, "No objects in the objects list.")
        return {'CANCELLED'}
    
    # Objects ready to onion skin, moving on.
    transp_factor = settings.transp_factor
    sel_obs = [ [bpy.data.objects[ ob.name], ob.inst] for ob in obs_collection.obs]
    
    # Remove onion skinning.
    if operator.remove:
        if final_collection_name == "":
            return {'CANCELLED'}
        
        try:
            scene_collection = bpy.data.collections[ final_collection_name]
        except KeyError:
            # Manually deleted by user. Try using the master scene collection, 
            # in case objects still exist in scene.
            scene_collection = scene.collection
            if ost.use_sets:
                active_set.final_collection_name = ""
            else:
                ost.final_collection_name = ""
                
        # Clear objects.
        if not current_only:
            if final_obs.__len__() > 0:
                for item in final_obs:
                    try:
                        scene_collection.objects.unlink( bpy.data.objects[ item.ob])
                    except KeyError:
                        pass
                    if item.ob in [ ob.name for ob in bpy.data.objects]:
                        bpy.data.objects.remove( bpy.data.objects[ item.ob], do_unlink = True)
                final_obs.clear()
            else:
                for ob in scene.objects:
                    if ost.use_sets:
                        if "ost_%s_ob" % active_set.name in ob.name:
                            scene_collection.objects.unlink( ob)
                    else:
                        if "ost_ob" in ob.name:
                            scene_collection.objects.unlink( ob)
                for ob in bpy.data.objects:
                    if ost.use_sets:
                        if "ost_%s_ob" % active_set.name in ob.name:
                            bpy.data.objects.remove( ob, do_unlink = True)
                    else:
                        if "ost_ob" in ob.name:
                            bpy.data.objects.remove( ob, do_unlink = True)
                            
            # Clear meshes.
            if final_meshes.__len__() > 0:
                for item in final_meshes:
                    if item.mesh in [ mesh.name for mesh in bpy.data.meshes]:
                        bpy.data.meshes.remove( bpy.data.meshes[ item.mesh], do_unlink = True)
                final_meshes.clear()
            else:
                for me in bpy.data.meshes:
                    if ost.use_sets:
                        if "ost_%s_mesh" % active_set.name in me.name:
                            bpy.data.meshes.remove( me, do_unlink = True)
                    else:
                        if "ost_mesh" in me.name:
                            bpy.data.meshes.remove( me, do_unlink = True)

            # Clear materials.
            if final_mats.__len__() > 0:    
                for item in final_mats:
                    if item.mat in [ mat.name for mat in bpy.data.materials]:
                        bpy.data.materials.remove( bpy.data.materials[ item.mat], do_unlink = True)
                final_mats.clear()
            else:
                for mat in bpy.data.materials:
                    if ost.use_sets:
                        if "ost_%s_mat" % active_set.name in mat.name:
                            bpy.data.materials.remove( mat, do_unlink = True)
                    else:
                        if "ost_mat" in mat.name:
                            bpy.data.materials.remove( mat, do_unlink = True)
                            
            if final_frames.__len__() > 0:
                final_frames.clear()
            if settings.final_collection_name:
                try:
                    scene.collection.children.unlink( bpy.data.collections[ settings.final_collection_name])
                except KeyError:
                    pass
                bpy.data.collections.remove( bpy.data.collections[ settings.final_collection_name], do_unlink = True)
                settings.final_collection_name = ""
            else:
                try:
                    scene.collection.children.unlink( bpy.data.collections[ settings.final_collection_name])
                except KeyError:
                    pass
                try:
                    bpy.data.collections.remove( bpy.data.collections[ settings.final_collection_name], do_unlink = True)
                except KeyError:
                    pass
                settings.final_collection_name = ""
        else:
            # TODO: Check if the current frame is the last one being removed
            # for the active set. If so, remove the scene collection too.
            # Clear for the current frame only.
            if final_obs.__len__() > 0:
                ob_found = False
                current_frame = scene.frame_current
                for item in final_obs:
                    frame = int( item.ob[:4])
                    if frame == current_frame:
                        ob_found = True
                        break
                if ob_found:
                    ob_name = item.ob
                    ob = bpy.data.objects[ob_name]
                    mesh, mesh_name = ob.data, ob.data.name 
                    mat, mat_name = mesh.materials[0], mesh.materials[0].name
                    try:
                        scene_collection.objects.unlink( ob)
                    except KeyError:
                        pass
                    bpy.data.objects.remove( ob, do_unlink = True)
                    bpy.data.meshes.remove( mesh, do_unlink = True)
                    bpy.data.materials.remove( mat, do_unlink = True)
                    for i in range( final_obs.__len__()):
                        if final_obs[ i].ob == ob_name:
                            final_obs.remove( i)
                            break
                    for i in range( final_meshes.__len__()):
                        if final_meshes[ i].mesh == mesh_name:
                            final_meshes.remove( i)
                            break
                    for i in range( final_mats.__len__()):
                        if final_mats[ i].mat == mat_name:
                            final_mats.remove( i)          
                            break
                    for i in range( final_frames.__len__()):
                        if final_frames[ i].frame == current_frame:
                            final_frames.remove( i)
                            break
                    # Check if that was the last onion skinning object in the collection.
                    if final_obs.__len__() == 0:
                        try:
                            scene.collection.children.unlink( bpy.data.collections[ settings.final_collection_name])
                        except KeyError:
                            pass
                        try:
                            bpy.data.collections.remove( bpy.data.collections[ settings.final_collection_name], do_unlink = True)
                        except KeyError:
                            pass
                        settings.final_collection_name = ""
            
        # Reset to defaults.
        operator.remove = False
        return {'FINISHED'}
    
    # Run onion skinning.
    else:
        if ost.keyed_only and ost.keyed_object == '':
            operator.report( {'INFO'}, "No objects with keyframes selected.")
            return { 'CANCELLED'}
            
        if final_collection_name == "":
            # New scene collection for onion skinning.
            if ost.use_sets:
                scene_collection = bpy.data.collections.new( "OST_%s" % active_set.name)
            else:
                scene_collection = bpy.data.collections.new( "OST")
                
            settings.final_collection_name = scene_collection.name
            scene.collection.children.link( scene_collection)
            scene_collection.hide_select = True
            scene_collection.hide_render = True

        elif settings.final_collection_name:
            scene_collection = bpy.data.collections[ settings.final_collection_name]
        
        if not current_only:
            # Calculate forward frame range for iterating. current_frame + 1 
            # to include current frame in meshes.
            if ost.range_mode == 'relative':
                range_start = ( orig_frame - bwd_range) if \
                              ( direction == 'both' or \
                                direction == 'backward') else orig_frame
                range_end = ( fwd_range + 1 + orig_frame) if \
                            ( direction == 'both' or \
                              direction == 'forward') else ( orig_frame + 1)
                ost.range_start = range_start
                ost.range_end = range_end
            elif ost.range_mode == 'absolute':
                range_start = ost.start_range
                range_end = ost.end_range + 1
                ost.range_start = range_start
                ost.range_end = range_end
            
            # If we're generating onion skinning on keyframes only.
            if ost.keyed_only:
                keyed_ob = bpy.data.objects[ ost.keyed_object]
                keyframes = set()
                fcurves = keyed_ob.animation_data.action.fcurves # There could be MANY on an armature.
                for fcu in fcurves:
                    for kp in fcu.keyframe_points:
                        keyframes.add( int( kp.co[0]))
                range_start = min(keyframes)
                range_end = max(keyframes) + 1
                
            # Iterate through timeline.
            # For each frame, create a new material and iterate 
            # through selected objects.
            frame_idx = 0
            for f in range( range_start, range_end, step):
                if not include_current and f == orig_frame:
                    continue
                if ost.keyed_only and f not in keyframes:
                    continue
                verts_count = 0
                verts = []   # List of (x,y,z) tuples.
                edges = [] # List of 2-element tuples
                faces = [] # List of 3- or 4-element tuples
                smooth = []
                
                # Set the timeline cursor and store the frame for reference.
                scene.frame_set( f)
                final_frames.add().frame = f
                
                # Create material. Use new default EVEE material without nodes.
                if ost.use_sets:
                    frame_mat = bpy.data.materials.new( "%04d_ost_%s_mat" % (f, active_set.name))
                else:
                    frame_mat = bpy.data.materials.new( "%04d_ost_mat" % f)
                final_mats.add().mat = frame_mat.name
                # Set material settings. If before start frame, blue. If after, red.
                # Set material's transparency relative to start frame.  
                frame_mat.blend_method = 'HASHED'
                frame_mat.show_transparent_back = False
                frame_mat.roughness = 0.75
                if f < orig_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    alpha = (( f - range_start + 1) / ( orig_frame - range_start + 1)) * transp_factor
                elif f > orig_frame:
                    # Reduce range, but %-% rather than to 0-1.
                    alpha = (( range_end + 1 - f) / ( range_end + 1 - orig_frame)) * transp_factor
                else:
                    alpha = 0
                if f < orig_frame:
                    frame_mat.diffuse_color = get_color( settings.bwd_color, alpha)
                else:
                    frame_mat.diffuse_color = get_color( settings.fwd_color, alpha)
                
                # Create nodes.
                frame_mat.use_nodes = True
                node_tree = frame_mat.node_tree
                os_create_nodes( node_tree)
                
                # Create the mesh.  
                if ost.use_sets:         
                    frame_mesh = bpy.data.meshes.new( "%04d_ost_%s_mesh" % (f, active_set.name))
                else:
                    frame_mesh = bpy.data.meshes.new( "%04d_ost_mesh" % f)
                final_meshes.add().mesh = frame_mesh.name
                frame_mesh.materials.clear()
                frame_mesh.materials.append( frame_mat)
                
                for item in sel_obs:
                    ob = item[0]
                    inst_name = item[1]
                    # Convert each object to mesh.
                    try:
                        # Assuming no naming conflicts with linked group empties named similarly to meshes.
                        ob_convert = ob.evaluated_get(depsgraph)
                        me = ob_convert.to_mesh()
                    except RuntimeError: 
                        # Naming conflict, searching bpy.data.objects returned an empty
                        # Search objects
                        for obj in bpy.data.objects:
                            if obj.name == ob.name and obj.data:
                                if obj.data.bl_rna.name == 'Mesh':
                                    # That's our object.
                                    ob = obj
                                    ob_convert = obj.evaluated_get( depsgraph)
                                    me = ob_convert.to_mesh()
                                    break
                               
                    me_transform( me, ob, inst_name)
                    # Add the vertices, edges and polygons to the lists.
                    verts.extend( [ vert.co[:] for vert in me.vertices])
                    edges.extend( [ tuple( map( lambda x: x + verts_count, 
                                    edge.vertices[:])) for edge in me.edges])
                    faces.extend( [ tuple( map( lambda x: x + verts_count, 
                                    poly.vertices[:])) for poly in me.polygons])
                    smooth.extend( [ poly.use_smooth for poly in me.polygons])
                    verts_count += me.vertices.__len__()
                    #bpy.data.meshes.remove( me, do_unlink = True)
                    ob_convert.to_mesh_clear()
                    del me
                
                # Push the mesh data to the final mesh.
                frame_mesh.from_pydata( verts, edges, faces)
                frame_mesh.validate()
                frame_mesh.polygons.foreach_set( "use_smooth", smooth)
                if bpy.app.version[1] >= 81:
                    frame_mesh.update(calc_edges=True, calc_edges_loose=True)
                elif bpy.app.version[1] == 80:
                    frame_mesh.update(calc_edges=True, calc_edges_loose=True, calc_loop_triangles=True)
                
                # Create the object.
                if ost.use_sets:
                    frame_ob = bpy.data.objects.new( "%04d_ost_%s_ob" % ( f, active_set.name), frame_mesh)
                else:
                    frame_ob = bpy.data.objects.new( "%04d_ost_ob" % f, frame_mesh)
                final_obs.add().ob = frame_ob.name
                
                # Link the object to the scene.
                scene_collection.objects.link( frame_ob)
                
                # Set object settings. Turn on object transparency.
                frame_ob.show_transparent = True if settings.show_transp else False
                frame_ob.show_in_front = settings.xray
                frame_ob.hide_select, frame_ob.hide_render = True, True
                
                # Store location for frame number for drawing frames.
                final_frames[ frame_idx].co = calc_frame_loc( verts, scene)
                frame_idx += 1
        else:
            # Current frame only.
            # TODO: Some duplicated code. Refactor for tidiness.
            final_frame = final_frames.add()
            final_frame.frame = orig_frame
            if ost.use_sets:
                mesh_name = "%04d_ost_%s_mesh" % ( orig_frame, active_set.name)
            else:
                mesh_name = "%04d_ost_mesh" % orig_frame
            if mesh_name not in [ mesh.name for mesh in bpy.data.meshes]:
                verts_count = 0
                verts = [] # List of (x,y,z) tuples.
                edges = [] # List of 2-element tuples
                faces = [] # List of 3- or 4-element tuples
                smooth = []
                
                if ost.use_sets:
                    frame_mat_name = "%04d_ost_%s_mat" % ( orig_frame, active_set.name)
                else:
                    frame_mat_name = "%04d_ost_mat" % orig_frame
                if frame_mat_name not in [ item.mat for item in final_mats] and \
                   frame_mat_name not in [ mat.name for mat in bpy.data.materials]:
                    frame_mat = bpy.data.materials.new( frame_mat_name)
                    final_mats.add().mat = frame_mat_name
                else:
                    frame_mat = bpy.data.materials[ frame_mat_name]
                    
                # Set material settings.
                frame_mat.show_transparent_back = False
                frame_mat.blend_method = 'HASHED'
                frame_mat.diffuse_color = get_color( settings.fwd_color, 0)
                frame_mat.roughness = 0.75
                
                # Create nodes.
                frame_mat.use_nodes = True
                node_tree = frame_mat.node_tree
                os_create_nodes( node_tree)
                
                for item in sel_obs:
                    ob = item[0]
                    inst_name = item[1]
                    ob_convert = ob.evaluated_get(depsgraph)
                    me = ob_convert.to_mesh()
                    me_transform( me, ob, inst_name)
                    # Add the vertices, edges and polygons to the lists.
                    verts.extend( [ vert.co[:] for vert in me.vertices])
                    edges.extend( [ tuple( map( lambda x: x + verts_count, 
                                    edge.vertices[:])) for edge in me.edges])
                    faces.extend( [ tuple( map( lambda x: x + verts_count, 
                                    poly.vertices[:])) for poly in me.polygons])
                    smooth.extend( [ poly.use_smooth for poly in me.polygons])
                    verts_count += me.vertices.__len__()
                    #bpy.data.meshes.remove( me, do_unlink = True)
                    ob_convert.to_mesh_clear()
                    del me
                
                # Store location for frame number for drawing frames.
                final_frame.co = calc_frame_loc( verts, scene)
                
                # Create the mesh.
                frame_mesh = bpy.data.meshes.new( mesh_name)
                final_meshes.add().mesh = frame_mesh.name
                frame_mesh.materials.clear()
                frame_mesh.materials.append( frame_mat)
                
                # Push the mesh data to the final mesh.
                frame_mesh.from_pydata( verts, edges, faces)
                frame_mesh.validate()
                frame_mesh.polygons.foreach_set( "use_smooth", smooth)
                if bpy.app.version[1] >= 81:
                    frame_mesh.update(calc_edges=True, calc_edges_loose=True)
                elif bpy.app.version[1] == 80:
                    frame_mesh.update(calc_edges=True, calc_edges_loose=True, calc_loop_triangles=True)
                
                # Create the object.
                if ost.use_sets:
                    frame_ob = bpy.data.objects.new( "%04d_ost_%s_ob" % (orig_frame, active_set.name), frame_mesh)
                else:
                    frame_ob = bpy.data.objects.new( "%04d_ost_ob" % 
                                                  orig_frame, frame_mesh)
                final_obs.add().ob = frame_ob.name
                # Link the object to the scene.
                scene_collection.objects.link( frame_ob)
                
                # Set object settings. Turn on object transparency.
                frame_ob.show_transparent = True if settings.show_transp else False
                frame_ob.show_in_front = settings.xray
                frame_ob.hide_select, frame_ob.hide_render = True, True
                
        # After iterating, reset the playhead and turn on backface culling.
        scene.frame_set( orig_frame)
        for area in bpy.data.window_managers[0].windows[0].screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].shading.show_backface_culling = True
        return {'FINISHED'}
