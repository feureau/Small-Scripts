bl_info = {
    "name": "MecaFace",
    "author": "Citrine's Animations",
    "version": (1, 0, 4),
    "blender": (2, 80, 0),
    "location": "Side Bar",
    "description": "Easily Add Face Rigs",
    "warning": "",
    "wiki_url": "www.mecabricks.com",
    "category": "Add Mesh",
}

import os
import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup, Panel, Scene

addon_dirc =os .path .dirname (os .path .realpath (__file__ ))

bpy.types.Scene.test_float = bpy.props.FloatVectorProperty(name = "Base",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.000986,0.000986,0.000986,1.0)) 
bpy.types.Scene.eyes_float = bpy.props.FloatVectorProperty(name = "Base",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.000986,0.000986,0.000986,1.0)) 
bpy.types.Scene.pupil_float = bpy.props.FloatVectorProperty(name = "Pupils",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.904661,0.904661,0.904661,1.0)) 

bpy.types.Scene.omouth_float = bpy.props.FloatVectorProperty(name = "Outline",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.000986,0.000986,0.000986,1.0)) 
bpy.types.Scene.inmouth_float = bpy.props.FloatVectorProperty(name = "Base",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.000986,0.000986,0.000986,1.0)) 
bpy.types.Scene.tong_float = bpy.props.FloatVectorProperty(name = "Tongue",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.505879,0.0,0.010592,1.0)) 
bpy.types.Scene.teeth_float = bpy.props.FloatVectorProperty(name = "Teeth",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.904661,0.904661,0.904661,1.0)) 

bpy.types.Scene.lips_float = bpy.props.FloatVectorProperty(name = "Lips",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.439657,0.194618,0.066626,1.0)) 
bpy.types.Bone.line_colour = bpy.props.FloatVectorProperty(name = "Base",subtype = "COLOR",size = 4,min = 0.0,max = 1.0,default = (0.000986,0.000986,0.000986,1.0)) 
bpy.types.Scene.line_amount = bpy.props.IntProperty(default=0) 

bpy.types.Bone.Start = bpy.props.IntProperty(default=0, min=0) 
bpy.types.Bone.End = bpy.props.IntProperty(default=1, min=0) 


def update_solids(self, context):
    numors = str(bpy.context.scene.line_amount)
    
    objectss = bpy.data.objects
    if context.scene.solids_fies==True:
        cb = objectss['Mouth']
        
        cb.modifiers["Solidify"].show_viewport = True
        cb.modifiers["Solidify"].show_render = True
        
        hb = objectss['Lips']

        hb.modifiers["Solidify"].show_viewport = True
        hb.modifiers["Solidify"].show_render = True
        ib = objectss['Eyelash1']

        ib.modifiers["Solidify"].show_viewport = True
        ib.modifiers["Solidify"].show_render = True
        jb = objectss['Eyelash2']

        jb.modifiers["Solidify"].show_viewport = True
        jb.modifiers["Solidify"].show_render = True
        db = objectss['EyeR']

        db.modifiers["Solidify"].show_viewport = True
        db.modifiers["Solidify"].show_render = True
        eb = objectss['EyeL']

        eb.modifiers["Solidify"].show_viewport = True
        eb.modifiers["Solidify"].show_render = True
        fb = objectss['BrowL']

        fb.modifiers["Solidify"].show_viewport = True
        fb.modifiers["Solidify"].show_render = True
        gb = objectss['BrowR']

        gb.modifiers["Solidify"].show_viewport = True
        gb.modifiers["Solidify"].show_render = True
        zb = objectss['FinLineMain' + numors]
        
        zb.modifiers["Solidify"].show_viewport = True
        zb.modifiers["Solidify"].show_render = True
    else:
        cb = objectss['Mouth']
        
        cb.modifiers["Solidify"].show_viewport = False
        cb.modifiers["Solidify"].show_render = False
        
        hb = objectss['Lips']

        hb.modifiers["Solidify"].show_viewport = False
        hb.modifiers["Solidify"].show_render = False
        ib = objectss['Eyelash1']

        ib.modifiers["Solidify"].show_viewport = False
        ib.modifiers["Solidify"].show_render = False
        jb = objectss['Eyelash2']

        jb.modifiers["Solidify"].show_viewport = False
        jb.modifiers["Solidify"].show_render = False
        db = objectss['EyeR']

        db.modifiers["Solidify"].show_viewport = False
        db.modifiers["Solidify"].show_render = False
        eb = objectss['EyeL']

        eb.modifiers["Solidify"].show_viewport = False
        eb.modifiers["Solidify"].show_render = False
        fb = objectss['BrowL']

        fb.modifiers["Solidify"].show_viewport = False
        fb.modifiers["Solidify"].show_render = False
        gb = objectss['BrowR']

        gb.modifiers["Solidify"].show_viewport = False
        gb.modifiers["Solidify"].show_render = False
        zb = objectss['FinLineMain' + numors]
        
        zb.modifiers["Solidify"].show_viewport = False
        zb.modifiers["Solidify"].show_render = False
    

def lipable(self, context):
    objects = bpy.data.objects
    gy = objects['Lips']
    if context.scene.setvisi==True:
        gy.hide_viewport = False
        gy.hide_render = False
    else:
        gy.hide_viewport = True
        gy.hide_render = True
    

def lashable(self, context):
    objects = bpy.data.objects
    gye = objects['Eyelash1']
    gye2 = objects['Eyelash2']
    if context.scene.setlash==True:
        gye.hide_viewport = False
        gye.hide_render = False
        gye2.hide_viewport = False
        gye2.hide_render = False
    else:
        gye.hide_viewport = True
        gye.hide_render = True
        gye2.hide_viewport = True
        gye2.hide_render = True
    

bpy.types.Object.setbevel = bpy.props.BoolProperty(name="bevel", default=True)

bpy.types.Scene.setvisi = bpy.props.BoolProperty(name="Lips", default=False, update=lipable)

bpy.types.Scene.setlash = bpy.props.BoolProperty(name="Lashes", default=False, update=lashable)

class MainMecaFacePanel:
    bl_label = "MecaFace"
    bl_idname = "SCENE_PT_layout"
    bl_category = "MecaFace"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    

    @classmethod
    def poll(cls, context):
        return (context.object is not None)


class MecaF0(MainMecaFacePanel, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "MecaFace"
    bl_idname = "SCENE_PT_layout"

    
    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row(align=True)
        row.operator("do.it", text="Add face rig to selected")
        row = layout.row(align=True)
        row.prop(context.scene,"setvisi")
        row.prop(context.scene,"setlash")
        
class MecaF1(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_1"
    bl_label = "Colour"
    bl_parent_id = 'SCENE_PT_layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        
class MecaF2(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "browee"
    bl_label = "Eyebrows"
    bl_parent_id = 'VIEW3D_PT_test_1'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        layout.prop(context.scene, "test_float")
        layout.operator("do.it2", text="Apply")

class MecaF3(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_3"
    bl_label = "Eyes"
    bl_parent_id = 'VIEW3D_PT_test_1'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        layout.prop(context.scene, "eyes_float")
        layout.prop(context.scene, "pupil_float")
        layout.operator("do.it3", text="Apply")
        
class MecaF4(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_4"
    bl_label = "Mouth"
    bl_parent_id = 'VIEW3D_PT_test_1'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        layout.prop(context.scene, "omouth_float")
        layout.prop(context.scene, "inmouth_float")
        layout.prop(context.scene, "tong_float")
        layout.prop(context.scene, "teeth_float")
        layout.operator("do.it4", text="Apply")

class MecaF5(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_5"
    bl_label = "Extra"
    bl_parent_id = 'VIEW3D_PT_test_1'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        layout.prop(context.scene, "lips_float")
        layout.operator("do.it5", text="Apply")
        
class MecaDoIt2(bpy.types.Operator):
    bl_idname = "do.it2"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        bpy.data.materials['Eyebrows'].node_tree.nodes["Shader"].inputs[0].default_value = bpy.context.scene.test_float
        
        bpy.data.materials['Eyebrows'].diffuse_color = bpy.context.scene.test_float
        return {'FINISHED'}
        

class MecaDoIt3(bpy.types.Operator):
    bl_idname = "do.it3"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        bpy.data.materials['Eyes'].node_tree.nodes["Shader"].inputs[1].default_value = bpy.context.scene.eyes_float
        bpy.data.materials['Eyes'].node_tree.nodes["Shader"].inputs[2].default_value = bpy.context.scene.pupil_float
        
        bpy.data.materials['Eyes'].diffuse_color = bpy.context.scene.eyes_float
        return {'FINISHED'}
    
class MecaDoIt4(bpy.types.Operator):
    bl_idname = "do.it4"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        bpy.data.materials['OutlineMouth'].node_tree.nodes["Shader"].inputs[0].default_value = bpy.context.scene.omouth_float
        bpy.data.materials['InnerMouth'].node_tree.nodes["Shader"].inputs[1].default_value = bpy.context.scene.inmouth_float
        bpy.data.materials['InnerMouth'].node_tree.nodes["Shader"].inputs[2].default_value = bpy.context.scene.tong_float
        bpy.data.materials['InnerMouth'].node_tree.nodes["Teeth1"].inputs[2].default_value = bpy.context.scene.teeth_float
        bpy.data.materials['InnerMouth'].node_tree.nodes["Teeth2"].inputs[2].default_value = bpy.context.scene.teeth_float
        
        bpy.data.materials['OutlineMouth'].diffuse_color = bpy.context.scene.omouth_float
        bpy.data.materials['InnerMouth'].diffuse_color = bpy.context.scene.inmouth_float
        return {'FINISHED'}

class MecaDoIt5(bpy.types.Operator):
    bl_idname = "do.it5"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        bpy.data.materials['Lips'].node_tree.nodes["Shader"].inputs[0].default_value = bpy.context.scene.lips_float
        
        bpy.data.materials['Lips'].diffuse_color = bpy.context.scene.lips_float
        return {'FINISHED'}
        
class MecaF6(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_2"
    bl_label = "Final"
    bl_parent_id = 'SCENE_PT_layout'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.object
        row = layout.row(align=True)
        row.operator("do.app", text="Finish")
        # draw the checkbox (implied from property type = bool)

class MecaF7(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_14"
    bl_label = "Lines"

    def draw(self, context):
        layout = self.layout
        obj = context.object
        row = layout.row(align=True)
        row.operator("line.it", text="Add line")
        # draw the checkbox (implied from property type = bool)

class MecaF8(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_15"
    bl_label = "Colour"
    bl_parent_id = 'VIEW3D_PT_test_14'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (context.active_bone is not None)
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        # draw the checkbox (implied from property type = bool)
        
        layout.prop(context.active_bone, "line_colour")
        layout.operator("do.it9", text="Apply")
        # draw the checkbox (implied from property type = bool)

class MecaF10(MainMecaFacePanel, bpy.types.Panel):
    bl_idname = "VIEW3D_PT_test_16"
    bl_label = "Set Visibility"
    bl_parent_id = 'VIEW3D_PT_test_14'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (context.active_bone is not None)
    
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(context.active_bone, "Start")
        row.operator('temp.line')
        row.prop(context.active_bone, "End")
        # draw the checkbox (implied from property type = bool)

class MecaDoIt9(bpy.types.Operator):
    bl_idname = "do.it9"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        mato = bpy.context.active_bone.name
        
        obmatos = bpy.data.objects[mato]
        
        obmatos.material_slots[0].material.node_tree.nodes["Shader"].inputs[0].default_value = bpy.context.active_bone.line_colour
        obmatos.material_slots[0].material.diffuse_color = bpy.context.active_bone.line_colour
        return {'FINISHED'}

class MecaDoIt(bpy.types.Operator):
    bl_idname = "do.it"
    bl_label = "Button text"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        a = bpy.context.selected_objects[0]

        path = addon_dirc + "/TEst 1 with rig.blend/Collection/"
        object_name = "Collection"
        bpy.ops.wm.append(filename=object_name, directory=path)


        objects = bpy.data.objects

        b = objects['DeOne']

        # Check if object 'a' is child of an Armature
        if a.parent and a.parent.type == 'ARMATURE':
            arm = a.parent

            # Check if bone in Armature
            bone = 'DEF_Cranium'
            if bone in arm.pose.bones.keys():
                b.parent = arm
                b.parent_type = 'BONE'
                b.parent_bone = bone

                b.location = (0, -.96, 0)
                b.scale = (.1, .1, .1)
            else:
                b.parent = a
        else:
            b.parent = a


        c = objects['Mouth']

        c.modifiers["Shrinkwrap"].target = a
        c.modifiers["DataTransfer"].object = a
        c.hide_select = True
        
        h = objects['Lips']

        h.modifiers["Shrinkwrap"].target = a
        h.modifiers["DataTransfer"].object = a
        h.hide_select = True
        
        i = objects['Eyelash1']

        i.modifiers["Shrinkwrap"].target = a
        i.modifiers["DataTransfer"].object = a
        i.hide_select = True
        
        j = objects['Eyelash2']

        j.modifiers["Shrinkwrap"].target = a
        j.modifiers["DataTransfer"].object = a
        j.hide_select = True
        
        d = objects['EyeR']

        d.modifiers["Shrinkwrap"].target = a
        d.modifiers["DataTransfer"].object = a
        d.hide_select = True

        e = objects['EyeL']

        e.modifiers["Shrinkwrap"].target = a
        e.modifiers["DataTransfer"].object = a
        e.hide_select = True

        f = objects['BrowL']

        f.modifiers["Shrinkwrap"].target = a
        f.modifiers["DataTransfer"].object = a
        f.hide_select = True

        g = objects['BrowR']

        g.modifiers["Shrinkwrap"].target = a
        g.modifiers["DataTransfer"].object = a
        g.hide_select = True
        
        collections = bpy.data.collections
        
        h = collections['UV controllers']
        
        h.hide_viewport = True

        
        return {'FINISHED'}
        
        
class MecaDoApp(bpy.types.Operator):
    bl_idname = "do.app"
    bl_label = "Button texts"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        
        
        objectss = bpy.data.objects

        bb = objectss['DeOne']
        
        bb.name = "DeFin"

        cb = objectss['Mouth']

        cb.name = "MouthFin"
        
        hb = objectss['Lips']

        hb.name = "LipsFin"
        
        ib = objectss['Eyelash1']

        ib.name = "Eyelash1Fin"
        
        jb = objectss['Eyelash2']

        jb.name = "Eyelash2Fin"
        
        db = objectss['EyeR']

        db.name = "EyeRFin"

        eb = objectss['EyeL']

        eb.name = "EyeLFin"

        fb = objectss['BrowL']

        fb.name = "BrowLFin"

        gb = objectss['BrowR']

        gb.name = "BrowRFin"
        
        bpy.data.materials['Eyebrows'].name = "EyebrowsFin"
        bpy.data.materials['Eyes'].name = "EyesFin"
        bpy.data.materials['OutlineMouth'].name = "OutlineMouthFin"
        bpy.data.materials['InnerMouth'].name = "InnerMouthFin"
        bpy.data.materials['Lips'].name = "LipsFin"
        
        collectionss = bpy.data.collections
        
        hb = collectionss['UV controllers']
        
        hb.name = "UV controllersFin"
        
        
        
        return {'FINISHED'}

        
class MecaLineIt(bpy.types.Operator):
    bl_idname = "line.it"
    bl_label = "Button text"

    
    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        bpy.context.scene.line_amount = bpy.context.scene.line_amount + 1
        numors = str(bpy.context.scene.line_amount)
        a = bpy.context.selected_objects[0]

        path = addon_dirc + "/lines.blend/Collection/"
        object_name = "Collection"
        bpy.ops.wm.append(filename=object_name, directory=path)


        objects = bpy.data.objects
        arms = bpy.data.armatures
        
        

        c = objects['LineMain']

        c.modifiers["Shrinkwrap"].target = a
        c.modifiers["DataTransfer"].object = a
        
        
        c.hide_select = True
        c.name = "FinLineMain" + numors
        
        objects = bpy.data.objects
        f = objects['Lineys'].children[0]
        
        d = arms['Lineys'].bones['LineMain']
        d.name = f.name
        
        b = objects['Lineys']
        e = arms['Lineys']
        b.parent = a
        b.name = "FinLineys" + numors
        e.name = "FinLineys" + numors
        
        collections = bpy.data.collections
        
        h = collections['VUS']
        
        h.hide_viewport = True

        
        return {'FINISHED'}

class LineTemp(bpy.types.Operator):
    bl_idname = "temp.line"
    bl_label = "Set"


    def execute(self, context):
        #self.report({'INFO'}, "Hello world!")
        mato = bpy.context.active_bone.name
        afaf = bpy.data.objects[mato]
        
        bruv = bpy.context.scene.frame_current-afaf.Start
        bruv2 = bpy.context.scene.frame_current+afaf.End+1
        bruv3 = bpy.context.scene.frame_current-afaf.Start-1
        
        afaf.hide_render = True
        afaf.hide_viewport = True
        afaf.keyframe_insert(data_path="hide_render", frame = bruv3)
        afaf.keyframe_insert(data_path="hide_viewport", frame = bruv3)
        afaf.hide_render = False
        afaf.hide_viewport = False
        afaf.keyframe_insert(data_path="hide_render", frame = bruv)
        afaf.keyframe_insert(data_path="hide_viewport", frame = bruv)
        afaf.hide_render = True
        afaf.hide_viewport = True
        afaf.keyframe_insert(data_path="hide_render", frame = bruv2)
        afaf.keyframe_insert(data_path="hide_viewport", frame = bruv2)
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MecaDoIt)
    bpy.utils.register_class(MecaDoApp)
    bpy.utils.register_class(MecaF0)
    bpy.utils.register_class(MecaF1)
    bpy.utils.register_class(MecaDoIt2)
    bpy.utils.register_class(MecaF2)
    bpy.utils.register_class(MecaF3)
    bpy.utils.register_class(MecaDoIt3)
    bpy.utils.register_class(MecaF4)
    bpy.utils.register_class(MecaDoIt4)
    bpy.utils.register_class(MecaF5)
    bpy.utils.register_class(MecaF6)
    bpy.utils.register_class(MecaDoIt5)
    bpy.utils.register_class(MecaLineIt)
    bpy.utils.register_class(MecaF7)
    bpy.utils.register_class(MecaF8)
    bpy.utils.register_class(MecaDoIt9)
    bpy.utils.register_class(LineTemp)
    bpy.utils.register_class(MecaF10)
    
def unregister():
    bpy.utils.unregister_class(MecaDoIt)
    bpy.utils.unregister_class(MecaDoApp)
    bpy.utils.unregister_class(MecaF0)
    bpy.utils.unregister_class(MecaF1)
    bpy.utils.unregister_class(MecaDoIt2)
    bpy.utils.unregister_class(MecaF2)
    bpy.utils.unregister_class(MecaF3)
    bpy.utils.unregister_class(MecaDoIt3)
    bpy.utils.unregister_class(MecaF4)
    bpy.utils.unregister_class(MecaDoIt4)
    bpy.utils.unregister_class(MecaF5)
    bpy.utils.unregister_class(MecaF6)
    bpy.utils.unregister_class(MecaDoIt5)
    bpy.utils.unregister_class(MecaLineIt)
    bpy.utils.unregister_class(MecaF7)
    bpy.utils.unregister_class(MecaF8)
    bpy.utils.unregister_class(MecaDoIt9)
    bpy.utils.unregister_class(LineTemp)
    bpy.utils.unregister_class(MecaF10)
    
if __name__ == "__main__":
    register()
