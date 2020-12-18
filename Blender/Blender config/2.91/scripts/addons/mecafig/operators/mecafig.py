import bpy

from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..properties.mecafig import *


class MECAFIG_OT_AddMecaFig(Operator):
    '''Add a new MecaFig'''
    bl_idname = 'mecafig.add_mecafig'
    bl_label = 'Add New'

    def execute(self, context):
        add_mecafig(context)

        return {'FINISHED'}


class MECAFIG_OT_AddMecaFigFromFile(Operator, ImportHelper):
    '''Add MecaFig from file(s)'''
    bl_idname = 'mecafig.add_mecafig_from_file'
    bl_label = 'Add From File'

    filename_ext = '.zip;.zmbx'

    filter_glob: StringProperty(
        default = '*.zip;*.zmbx',
        options = {'HIDDEN'},
        maxlen = 255,
    )
    # Allow multiple files selection
    files: CollectionProperty(
        name = 'Filepath List',
        type = bpy.types.OperatorFileListElement,
    )
    # Return file directory
    directory: StringProperty(
        subtype = 'DIR_PATH',
    )

    def execute(self, context):
        files = list(self.files)
        directory = self.directory

        for i, filepath in enumerate(files):
            filepath = directory + filepath.name

            add_mecafig_from_file(self, context, filepath, i)

        return {'FINISHED'}


class MECAFIG_OT_DeleteMecaFig(Operator):
    '''Delete MecaFig'''
    bl_idname = 'mecafig.delete_mecafig'
    bl_label = ''

    def execute(self, context):
        delete_mecafig(context)

        return {'FINISHED'}
