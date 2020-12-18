import bpy
import bpy_extras
import mathutils
import math

# ------------------------------------------------------------------------------
# Make a matrix4 from an array
# ------------------------------------------------------------------------------
def make_matrix(l):
    m = []
    count = 0
    for i in range(0,4,1):
        n = []
        for j in range(0,4,1):
            n.append(float(l[count]))
            count += 1
        m.append(n)

    return mathutils.Matrix(m)

# ------------------------------------------------------------------------------
# Find node with specified label
# ------------------------------------------------------------------------------
def find_node(nodes, label):
    for node in nodes:
        if node.label == label:
            return node

    return None

# ------------------------------------------------------------------------------
# Convert hex value to rgba
# ------------------------------------------------------------------------------
def hex_to_rgba(value):
    gamma = 2.2
    lv = len(value)
    fin = list(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    r = pow(fin[0] / 255, gamma)
    g = pow(fin[1] / 255, gamma)
    b = pow(fin[2] / 255, gamma)
    fin.clear()
    fin.append(r)
    fin.append(g)
    fin.append(b)
    fin.append(1.0)

    return tuple(fin)
