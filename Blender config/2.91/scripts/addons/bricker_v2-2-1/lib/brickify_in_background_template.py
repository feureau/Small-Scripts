# NOTE: Requires 'frame' and 'action' as variables
import sys
# redefine common functions
def b280():
    return bpy.app.version >= (2,80,0)
def link_object(o, scene=None):
    scene = scene or bpy.context.scene
    if b280():
        scene.collection.objects.link(o)
    else:
        scene.objects.link(o)
# set active scene and cmlist index
bpy.data.scenes.remove(bpy.context.scene)
scn = bpy.context.scene
assert scn.name == "Bricker Model Settings Container"
cm = scn.cmlist[0]
cm.id = cmlist_id
# link objects to scene
for obj in bpy.data.objects:
    if obj.name.startswith("Bricker_"):
        link_object(obj)
bpy.context.view_layer.depsgraph.update()
# run backgrund brickify
bpy.ops.bricker.brickify_in_background(frame=frame if frame is not None else -1, action=action)
# handle results
frame_str = "_f_%(frame)s" % locals() if cm.use_animation else ""
n = cm.source_obj.name
bpy_collections = bpy.data.groups if bpy.app.version < (2,80,0) else bpy.data.collections
target_coll = bpy_collections.get("Bricker_%(n)s_bricks%(frame_str)s" % locals())
parent_obj = bpy.data.objects.get("Bricker_%(n)s_parent%(frame_str)s" % locals())

### SET 'data_blocks' EQUAL TO LIST OF OBJECT DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [
    target_coll,
    parent_obj,
]

### PYTHON DATA TO BE SEND BACK TO THE BLENDER HOST ###

python_data = {
    "bricksdict": bpy.props.bfm_cache_bytes_hex,
    "brick_sizes_used": cm.brick_sizes_used,
    "brick_types_used": cm.brick_types_used,
    "rgba_vals": cm.rgba_vals,
    "active_key": tuple(cm.active_key),
}
