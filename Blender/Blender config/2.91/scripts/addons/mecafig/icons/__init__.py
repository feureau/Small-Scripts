import os
import bpy
import bpy.utils.previews

mecafig_icons = {}
icons_directory = os.path.dirname(__file__)

def get_icon(icon):
    if icon not in mecafig_icons['main']:
        mecafig_icons['main'].load(icon, os.path.join(icons_directory, icon + '.png'), 'IMAGE')
    return mecafig_icons['main'][icon].icon_id

def register_icons():
    #global mecafig_icons
    mecafig_icons['main'] = bpy.utils.previews.new()

def unregister_icons():
    for pcoll in mecafig_icons.values():
        bpy.utils.previews.remove(pcoll)
    mecafig_icons.clear()
