import bpy

for mat in bpy.data.materials:
     if mat.name.startswith("mb"):
         for node in mat.node_tree.nodes:
             if node.label == "Scale":
                 node.outputs[0].default_value = 0.1