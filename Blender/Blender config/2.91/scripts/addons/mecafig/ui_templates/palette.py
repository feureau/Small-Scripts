import bpy
import math

def ui_template_palette(context, layout, columns, items, data, prop):

    #columns = math.floor(context.region.width / 32)
    for i in range(0, math.ceil(len(items) / columns)):
        row = layout.row()
        var = (len(items) - (i * columns))
        end_range = columns if var >= columns else var % columns
        for j in range(0, end_range):
            row.prop_enum(data, prop, items[(i * columns) + j])

    return{'FINISHED'}
