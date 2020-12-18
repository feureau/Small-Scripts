import bpy
from bpy.types import PropertyGroup
from bpy.props import ( BoolProperty, EnumProperty, IntProperty, 
                        StringProperty, FloatProperty, 
                        FloatVectorProperty, PointerProperty,
                        CollectionProperty)
from .util import *
    
#-------------------------------------------------
# Properties for objects added to the object list.
#-------------------------------------------------
class OSTObjectProps( PropertyGroup):
    name : StringProperty( name = "")
    inst : StringProperty( name = "")
    
class OSTObjects( PropertyGroup):
    """Property group for objects to be onion skinned."""
    index : IntProperty( default = 0)
    obs : CollectionProperty( type = OSTObjectProps)

#-------------------------------------------------
# Property group to emulate lists for storing 
# materials, meshes, objects, frames.
#-------------------------------------------------
class OSTMats( PropertyGroup):
    mat : StringProperty()

class OSTObs( PropertyGroup):
    ob : StringProperty()

class OSTMeshes( PropertyGroup):
    mesh : StringProperty()

class OSTFrames( PropertyGroup):
    frame : IntProperty()
    co : FloatVectorProperty( subtype = 'XYZ')

#-------------------------------------------------
# Properties for character sets.
#-------------------------------------------------
class OSTBaseProps():
    # Post-onion skinning generation storage.
    final_mats      :   CollectionProperty( type = OSTMats)
    
    final_meshes    :   CollectionProperty( type = OSTMeshes)
    
    final_obs       :   CollectionProperty( type = OSTObs)
    
    final_frames    :   CollectionProperty( type = OSTFrames)
    
    final_collection_name :   StringProperty()
    
    obs_collection  :   PointerProperty( type = OSTObjects, 
                            name = "Onion Skin Objects", 
                            description = "")
                            
    xray            :   BoolProperty( name = "X-Ray",
                            description = "Turn on X-Ray mode for onion skinning mesh",
                            default = False,
                            update = update_xray)
    
    xray_orig       :   BoolProperty( name = "X-Ray Originals",
                            description = "Turn on X-Ray mode for objects in " \
                            "the onion skinning list",
                            default = False,
                            update = update_xray_orig)
    
    wireframe       :   BoolProperty( name = "Wireframe",
                            description = "Turn on wireframe drawing for onion " \
                            "skinning mesh. Best to keep this disabled when onion " \
                            "skinned frames are close together",
                            default = False,
                            update = update_wire)
                                    
    show_transp     :   BoolProperty( name = "Transparent",
                            description = "Enable transparency for onion " \
                            "skinning mesh",
                            default = True,
                            update = update_transp)
    
    fwd_color       :   FloatVectorProperty( name = "Forward",
                            description = "Color of frames later than " \
                            "the current frame",
                            default = (0.8, 0.1, 0.1),
                            min = 0.0,
                            max = 1.0,
                            subtype = 'COLOR',
                            update = update_color)
                                        
    bwd_color       :   FloatVectorProperty( name = "Backward",
                            description = "Color of frames earlier than " \
                            "the current frame",
                            default = (0.1, 0.1, 0.8),
                            min = 0.0,
                            max = 1.0,
                            subtype = 'COLOR',
                            update = update_color)
                                        
    transp_factor   :   FloatProperty( name = "Transparency Factor",
                            description = "Multiplier for onion skin transparency",
                            default = 1.0,
                            min = 0.1,
                            max = 1.0,
                            update = update_transp)
    
    hide_before     :   BoolProperty( name = "Hide Before",
                            description = "Hide onion skinning objects " \
                            "earlier than the current frame.",
                            default = False,
                            update = update_hide_before)
                                 
    hide_after      :   BoolProperty( name = "Hide After",
                            description = "Hide onion skinning objects " \
                            "later than the current frame.",
                            default = False,
                            update = update_hide_after)
    
    hide_all        :   BoolProperty( name = "Hide All",
                            description = "Hide all onion skinning objects",
                            default = False,
                            update = update_hide_all)
    
    use_transp_range :  BoolProperty( name = "Use Visibility Range",
                            description = "Limit visibility to a specific "\
                            "number of frames around the current frame",
                            default = False,
                            update = update_transp)
    
    transp_range    :   IntProperty( name = "Visibility Range",
                            description = "Number of frames around the current " \
                            "frame to display",
                            default = 10,
                            min = 1,
                            update = update_transp)
    
    
    
class OSTCharacterSetProps( PropertyGroup, OSTBaseProps):
    name            :   StringProperty()
          
class OSTCharacterSets( PropertyGroup):
    index           :   IntProperty( default = 0)
    sets            :   CollectionProperty( type = OSTCharacterSetProps)
    
    @property
    def active( self):
        if len( self.sets) > 0:
            return self.sets[ self.index]
        else:
            return None
            
#-------------------------------------------------
# Onion skinning properties.
#-------------------------------------------------                         
class OSTProps( PropertyGroup, OSTBaseProps):
    """Properties for scene.ost"""
    # Objects list settings.
    show_list       :   BoolProperty( name = "Objects List", 
                            default = True)
    
    show_range      :   BoolProperty( name = "Frame Range Settings",
                            default = True)
    
    use_sets        :   BoolProperty( name = "Use Character Sets",
                            default = False)
                            
    sets_collection :   PointerProperty( type = OSTCharacterSets,
                            name = "Character Sets")
    
    # Frame range settings.
    direction       :   EnumProperty( name = "Direction",
                            items = [ 
                            ('forward', "Forward", ""),
                            ('backward', "Backward", ""),
                            ('both', "Both", "")],
                            description = "Direction on timeline to run onion skinning",
                            default = 'both')
                                        
    orig_frame      :   IntProperty( name = "Start Frame",
                            description = "",
                            default = 10)
                                        
    fwd_range       :   IntProperty( name = "Range Forward", 
                            description = "Number of frames forward to onion skin",
                            default = 10,
                            min = 0)
                                     
    bwd_range       :   IntProperty( name = "Range Backward", 
                            description = "Number of frames backward to onion skin",
                            default = 10,
                            min = 0)
    
    start_range     :   IntProperty( name = "Range Start",
                            description = "Absolute start frame of onion skinning range",
                            default = 1,
                            min = 1)
    
    end_range       :   IntProperty( name = "Range End",
                            description = "Absolute end frame of onion skinning range",
                            default = 250,
                            min = 1)
                                    
    # range_start and range_end are for internal reference and storage.
    range_start     :   IntProperty()
    
    range_end       :   IntProperty()    
    
    range_mode      :   EnumProperty( name = "Range Mode",
                            items = [ 
                            ('absolute', "Absolute", "Use absolute start and " \
                            "end frames (e.g., frames 1 to 100)"),
                            ('relative', "Relative", "Uses backward and " \
                            "forward frame ranges relative to the current frame")],
                            description = "Mode for setting frame range",
                            default = 'absolute')
    
    keyed_only      :   BoolProperty( name = "On Keyframes Only",
                            description = "Generate onion skinning only on keyed frames",
                            default = False)
                            
    # keyed_object returns object names.
    keyed_object    :   EnumProperty( name = "Keyed Object",
                            description = "Object with keyframe data to use for " \
                            "generating onion skinning",
                            items = get_objects)
                            
    step            :   IntProperty( name = "Frame Step",
                            description = "Number of frames between onion skin objects",
                            default = 1,
                            min = 1)
                                     
    current_only    :   BoolProperty( name = "Current Frame Only",
                            description = "Run onion skinning only for current frame",
                            default = False)
    
    include_current :   BoolProperty( name = "Include Current Frame",
                            description = "Include current frame",
                            default = True)
    
    # Viewport visualization settings.
    show_settings   :   BoolProperty( name = "Viewport Settings",
                            default = False)
                                                    
    # Frame number display settings.
    display_frames  :   BoolProperty( default = False)
    
    font_size       :   IntProperty( name = "Size",
                            description = "Frame number font size",
                            default = 12,
                            min = 5, 
                            max = 20)
    
    font_height     :   FloatProperty( name = "Height",
                            description = "Frame number font height",
                            default = 1.0,
                            min = 0.1, 
                            soft_min = 0.5,
                            soft_max = 5)
    
    # Auto update settings.
    show_auto_settings  :   BoolProperty( name = "Auto Update Settings",
                            default = False)
                            
    updater_object  :   StringProperty( name = "Updater",
                            description = "Object to watch for updates " \
                            "when regenerating onion skinning",
                            default = "")
    
    auto_update_on  :   BoolProperty( default = False)
    
    update_context  :   StringProperty( name = "Update Context")
    

classes = (OSTObjectProps, OSTObjects, OSTMats, OSTObs, OSTMeshes, OSTFrames, OSTCharacterSetProps, OSTCharacterSets, OSTProps)

def register():
    for cls in classes:
        bpy.utils.register_class( cls)
    
def unregister():
    for cls in reversed( classes):
        bpy.utils.unregister_class( cls)