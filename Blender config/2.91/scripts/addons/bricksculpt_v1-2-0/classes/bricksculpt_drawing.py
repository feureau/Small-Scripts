# Copyright (C) 2019 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Much of the code in this file was adapted from Retopoflow source code (credit: Dr. John Denning, CG Cookie)

# System imports
import os
import numpy as np
from random import random

# Blender imports
import bpy
import bgl
import blf
from bpy.types import Operator, SpaceView3D
from bpy.props import *

# Module imports
from .bricksculpt_tools import *
from ..functions import *

# b280 specific imports
if b280() and not bpy.app.background:
    import gpu
    from gpu_extras.batch import batch_for_shader

    # https://docs.blender.org/api/blender2.8/gpu.html#triangle-with-custom-shader
    cover_vshader = '''
        in vec2 position;
        void main() {
            gl_Position = vec4(position, 0.0f, 1.0f);
        }
    '''
    cover_fshader = '''
        uniform float darken;
        out vec4 outColor;
        void main() {
            // float r = length(gl_FragCoord.xy - vec2(0.5, 0.5));
            if(mod(floor(gl_FragCoord.x+gl_FragCoord.y), 2) == 0) {
                outColor = vec4(0.0,0.0,0.0,1.0);
            } else {
                outColor = vec4(0.0f, 0.0f, 0.0f, darken);
            }
        }
    '''
    shader = gpu.types.GPUShader(cover_vshader, cover_fshader)

    # create batch to draw large triangle that covers entire clip space (-1,-1)--(+1,+1)
    batch_full = batch_for_shader(shader, 'TRIS', {"position": [(-1, -1), (3, -1), (-1, 3)]})


class BricksculptDrawing:

    ##############################################
    # Draw onscreen text

    def ui_start(self):
        # initialize handler list
        self._handlers = {}

        # get pixel size
        self.pixel_size = self.blender_prefs.system.pixel_size

        # set the font drawing routine to run every frame
        self.font_id = 0  # blf.load(font_path)
        self.font_handler = SpaceView3D.draw_handler_add(self.draw_callback_px, (bpy.context, ), "WINDOW", "POST_PIXEL")

        # update screen properties
        self.stored_screen_properties = {
            # "show_gizmo": bpy.context.space_data.show_gizmo,
            # "show_region_header": bpy.context.space_data.show_region_header,
            "show_text": bpy.context.space_data.overlay.show_text,
        }
        # bpy.context.space_data.show_gizmo = False
        # bpy.context.space_data.show_region_header = False
        bpy.context.space_data.overlay.show_text = False
        self.region_darken()
        self.panels_store()
        self.panels_hide()

        # # darken non-ui panels
        # self.spaces = [
        #     bpy.types.SpaceClipEditor,
        #     bpy.types.SpaceConsole,
        #     bpy.types.SpaceDopeSheetEditor,
        #     bpy.types.SpaceFileBrowser,
        #     bpy.types.SpaceGraphEditor,
        #     bpy.types.SpaceImageEditor,
        #     bpy.types.SpaceInfo,
        #     bpy.types.SpaceNLA,
        #     bpy.types.SpaceNodeEditor,
        #     bpy.types.SpaceOutliner,
        #     bpy.types.SpaceProperties,
        #     bpy.types.SpaceSequenceEditor,
        #     bpy.types.SpaceTextEditor,
        #     # bpy.types.SpaceView3D,                 # <- specially handled
        # ]
        # if b280():
        #     self.spaces.append(bpy.types.SpacePreferences)
        #     self.spaces.append(bpy.types.SpaceUVEditor)
        # else:
        #     self.spaces.append(bpy.types.SpaceUserPreferences)
        #     self.spaces.append(bpy.types.SpaceLogicEditor)
        #     self.spaces.append(bpy.types.SpaceTimeline)
        # self.areas = ("WINDOW", "HEADER")
        # # ("WINDOW", "HEADER", "CHANNELS", "TEMPORARY", "UI", "TOOLS", "TOOL_PROPS", "PREVIEW")
        # self.cb_pp_tools   = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), "TOOLS",      "POST_PIXEL")
        # # self.cb_pp_props   = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), "TOOL_PROPS", "POST_PIXEL")
        # self.cb_pp_ui      = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), "UI",         "POST_PIXEL")
        # self.cb_pp_header  = SpaceView3D.draw_handler_add(self.draw_callback_cover, (bpy.context, ), "HEADER",     "POST_PIXEL")
        # # self.cb_pp_all = [
        # #     (s, a, s.draw_handler_add(self.draw_callback_cover, (bpy.context,), a, "POST_PIXEL"))
        # #     for s in self.spaces
        # #     for a in self.areas
        # # ]
        # # self.draw_preview()

        # redraw viewport
        tag_redraw_areas("VIEW_3D")

    def ui_end(self):
        # disable font drawing
        if hasattr(self, "font_handler"):
            SpaceView3D.draw_handler_remove(self.font_handler, "WINDOW")
            del self.font_handler
        # reset screen properties
        # bpy.context.space_data.show_gizmo = self.stored_screen_properties["show_gizmo"]
        # bpy.context.space_data.show_region_header = self.stored_screen_properties["show_region_header"]
        bpy.context.space_data.overlay.show_text = self.stored_screen_properties["show_text"]
        self.region_restore()
        self.panels_restore()
        # redraw viewport
        tag_redraw_areas("VIEW_3D")

    def set_cursor_type(self, event=None):
        if self.mode == "DRAW":
            if event and event.alt:
                self.cursor_text = "CUT" if event and event.shift else "REMOVE"
                self.cursor_type = "KNIFE"
            else:
                self.cursor_text = "DRAW"
                self.cursor_type = "PAINT_BRUSH"
        elif self.mode == "MERGE_SPLIT":
            if event and event.shift and event.alt:
                self.cursor_text = "SPLIT (xy)"
                self.cursor_type = "SCROLL_XY"
            elif event and event.shift:
                self.cursor_text = "SPLIT (y)"
                self.cursor_type = "SCROLL_Y"
            elif event and event.alt:
                self.cursor_text = "SPLIT (x)"
                self.cursor_type = "SCROLL_X"
            else:
                self.cursor_text = "MERGE"
                self.cursor_type = "PAINT_BRUSH"
        elif self.mode == "PAINT":
            if (event and event.alt) or bpy.context.scene.bricksculpt.paintbrush_mat is None:
                self.cursor_text = "COLOR PICKER"
                self.cursor_type = "EYEDROPPER"
            else:
                self.cursor_text = "PAINT"
                self.cursor_type = "PAINT_BRUSH"
        elif self.mode == "HIDE":
            if (event and event.alt) or bpy.context.scene.bricksculpt.paintbrush_mat is None:
                self.cursor_text = "HIDE LAYER"
                self.cursor_type = "EYEDROPPER"
            else:
                self.cursor_text = "HIDE"
                self.cursor_type = "PAINT_BRUSH"
        bpy.context.window.cursor_set(self.cursor_type)
        tag_redraw_areas()


    def draw_callback_px(self, context):
        """Draw on the viewports"""
        dtext = "  'D' for Draw/Cut Tool"
        mtext = "  'M' for Merge/Split Tool"
        ptext = "  'P' for Paintbrush Tool"
        regions = dict()
        for region in context.area.regions:
            regions[region.type] = region
        header_height = regions["HEADER"].height + regions["TOOL_HEADER"].height
        tools_width = regions["TOOLS"].width
        ui_width = regions["UI"].width

        # update dpi
        self.ui_scale = self.blender_prefs.view.ui_scale
        self.ui_scale_adjusted = (self.ui_scale - 1) / self.pixel_size + self.prefs.ui_text_scale
        self.dpi = int(72 * self.ui_scale_adjusted * self.pixel_size)
        self.ui_pixel_size = self.pixel_size * self.ui_scale_adjusted

        # get starting positions
        x_pos1 = self.static_dist(20)  # + self.blender_pixel_dist(tools_width)
        y_pos1 = self.static_dist(45)
        # draw instructions text
        if self.mode == "DRAW":
            text = "Click & drag to add bricks"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 90))
            text = "  + 'ALT' to remove bricks created during this session"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 75))
            text = "  + 'SHIFT' + 'ALT' to cut"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 60))
            dtext = "*" + dtext[1:]
        elif self.mode == "MERGE_SPLIT":
            text = "Click & drag to merge bricks"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 90))
            text = "  + 'ALT' to split horizontally"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 75))
            text = "  + 'SHIFT' to split vertically (only works if brick type is 'Bricks and Plates')"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 60))
            mtext = "*" + mtext[1:]
        elif self.mode == "PAINT":
            scn = bpy.context.scene
            mat = scn.bricksculpt.paintbrush_mat
            text_color = (1, 1, 1, 1) if mat is None else mat.diffuse_color
            self.draw_text_2d("*", position=(x_pos1, y_pos1 + 107.5), size=100, color=text_color)
            text = "Material: " + (mat.name if mat is not None else "None")
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 115))
            text = "Press 'SPACE' to choose material from dropdown"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 90))
            text = "Click & drag to paint bricks"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 75))
            text = "  + 'ALT' for material picker"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 60))
            ptext = "*" + ptext[1:]
        prefs = get_addon_preferences()
        if prefs.enable_layer_soloing:
            text = "'CTRL' or 'UP/DOWN ARROW' to solo layer"
            self.draw_text_2d(text, position=(x_pos1, y_pos1 + 35))
        text = "'RETURN' to commit changes"
        self.draw_text_2d(text, position=(x_pos1, y_pos1 + 20))
        text = "'ESC' to cancel changes" if self.layer_solod is None else "'ESC' to unsolo layer"
        self.draw_text_2d(text, position=(x_pos1, y_pos1 + 5))

        # draw tool near cursor
        adjusted_mouse_pos = self.blender_pixel_dist(self.mouse)
        hover_text_pos = adjusted_mouse_pos + self.static_dist(Vector((35, 45))) / 2
        self.draw_text_2d(self.cursor_text, position=hover_text_pos + Vector((3, 2)))
        self.draw_text_2d("+", position=adjusted_mouse_pos - Vector((4, 3)))

        # get starting positions
        x_pos2 = self.blender_pixel_dist(tools_width) + self.static_dist(15)
        y_pos2 = self.blender_pixel_dist(bpy.context.area.height - header_height) - self.static_dist(40)
        # draw tool switcher text
        text = "Switch Tools:"
        self.draw_text_2d(text, position=(x_pos2 + 7, y_pos2 - 10))
        self.draw_text_2d(dtext, position=(x_pos2 + 7, y_pos2 - 25))
        self.draw_text_2d(mtext, position=(x_pos2 + 7, y_pos2 - 40))
        self.draw_text_2d(ptext, position=(x_pos2 + 7, y_pos2 - 55))

    def static_dist(self, value):
        return value / self.ui_scale_adjusted

    def blender_pixel_dist(self, value):
        return value / self.ui_pixel_size

    def draw_text_2d(self, text, position=(0, 0), size=11, color=None):
        color = color or self.prefs.ui_text_color
        blf.enable(self.font_id, blf.SHADOW)
        blf.shadow(self.font_id, 5, 0, 0, 0, 1)
        blf.shadow_offset(self.font_id, round(1.5 * self.ui_pixel_size), round(-1.5 * self.ui_pixel_size))
        blf.color(self.font_id, *color)
        adjusted_pos = Vector(position) * self.ui_pixel_size
        blf.position(self.font_id, adjusted_pos[0], adjusted_pos[1], 0)
        blf.size(self.font_id, size, self.dpi)
        blf.draw(self.font_id, text)
        blf.disable(self.font_id, blf.SHADOW)

    def draw_brick_3d(self, mesh, color=(1, 1, 1, 1), loc=(0, 0, 0)):
        mesh.calc_loop_triangles()

        vertices = np.empty((len(mesh.vertices), 3), "f")
        indices = np.empty((len(mesh.loop_triangles), 3), "i")

        mesh.vertices.foreach_get(
            "co", np.reshape(vertices, len(mesh.vertices) * 3))
        mesh.loop_triangles.foreach_get(
            "vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))

        # move to location
        vertices[:,0] += loc[0]
        vertices[:,1] += loc[1]
        vertices[:,2] += loc[2]

        # vertex_colors = [(random(), random(), random(), 1) for _ in range(len(mesh.vertices))]
        vertex_colors = np.empty((len(mesh.vertices), 4))
        vertex_colors[:] = color

        shader = gpu.shader.from_builtin("3D_SMOOTH_COLOR")
        batch = batch_for_shader(
            shader, "TRIS",
            {"pos": vertices, "color": vertex_colors},
            indices=indices,
        )

        def draw():
            batch.draw(shader)

        self.draw_handlers.append(SpaceView3D.draw_handler_add(draw, (), "WINDOW", "POST_VIEW"))

        # redraw viewport
        tag_redraw_areas("VIEW_3D")

    #########################################
    # Region Darkening

    @blender_version_wrapper("<=", "2.79")
    def _cc_region_draw_cover(self, darkness=0.25):
        bgl.glPushAttrib(bgl.GL_ALL_ATTRIB_BITS)
        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glPushMatrix()
        bgl.glLoadIdentity()
        bgl.glColor4f(0,0,0,darkness)    # TODO: use window background color??
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glBegin(bgl.GL_QUADS)   # TODO: not use immediate mode
        bgl.glVertex2f(-1, -1)
        bgl.glVertex2f( 1, -1)
        bgl.glVertex2f( 1,  1)
        bgl.glVertex2f(-1,  1)
        bgl.glEnd()
        bgl.glPopMatrix()
        bgl.glPopAttrib()
    @blender_version_wrapper(">=", "2.80")
    def _cc_region_draw_cover(self, darkness=0.25):
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        shader.bind()
        shader.uniform_float("darken", darkness)
        batch_full.draw(shader)
        gpu.shader.unbind()

    def region_darken(self):
        if hasattr(self, '_region_darkened'): return    # already darkened!
        self._region_darkened = True
        self._postpixel_callbacks = []

        # darken all spaces
        spaces = [(getattr(bpy.types, n), n) for n in dir(bpy.types) if n.startswith('Space')]
        spaces = [(s,n) for (s,n) in spaces if hasattr(s, 'draw_handler_add')]

        # https://docs.blender.org/api/blender2.8/bpy.types.Region.html#bpy.types.Region.type
        #     ['WINDOW', 'HEADER', 'CHANNELS', 'TEMPORARY', 'UI', 'TOOLS', 'TOOL_PROPS', 'PREVIEW', 'NAVIGATION_BAR', 'EXECUTE']
        # NOTE: b280 has no TOOL_PROPS region for SpaceView3D!
        # handling SpaceView3D differently!
        general_areas  = ['WINDOW', 'HEADER', 'CHANNELS', 'TEMPORARY', 'UI', 'TOOLS', 'TOOL_PROPS', 'PREVIEW', 'HUD', 'NAVIGATION_BAR', 'EXECUTE', 'FOOTER', 'TOOL_HEADER'] #['WINDOW', 'HEADER', 'UI', 'TOOLS', 'NAVIGATION_BAR']
        SpaceView3D_areas = ['TOOLS', 'UI', 'HEADER', 'TOOL_PROPS']

        for (s,n) in spaces:
            areas = SpaceView3D_areas if n == 'SpaceView3D' else general_areas
            for a in areas:
                try:
                    cb = s.draw_handler_add(self._cc_region_draw_cover, (0.35, ), a, 'POST_PIXEL')
                    self._postpixel_callbacks += [(s, a, cb)]
                except:
                    pass

        tag_redraw_areas()

    def region_restore(self):
        # remove callback handlers
        if hasattr(self, '_postpixel_callbacks'):
            for (s,a,cb) in self._postpixel_callbacks: s.draw_handler_remove(cb, a)
            del self._postpixel_callbacks
        if hasattr(self, '_region_darkened'):
            del self._region_darkened
        tag_redraw_areas()

    #########################################
    # Panels

    def _cc_panels_get_details(self):
        # regions for 3D View:
        #     279: [ HEADER, TOOLS, TOOL_PROPS, UI,  WINDOW ]
        #     280: [ HEADER, TOOLS, UI,         HUD, WINDOW ]
        #            0       1      2           3   4
        # could hard code the indices, but these magic numbers might change.
        # will stick to magic (but also way more descriptive) types
        def iter_head(i, default=None):
            try:
                return next(iter(i))
            except StopIteration:
                return default
        rgn_header = iter_head(r for r in self._area.regions if r.type == 'HEADER')
        rgn_toolshelf = iter_head(r for r in self._area.regions if r.type == 'TOOLS')
        rgn_properties = iter_head(r for r in self._area.regions if r.type == 'UI')
        rgn_hud = iter_head(r for r in self._area.regions if r.type == 'HUD')
        return (rgn_header, rgn_toolshelf, rgn_properties, rgn_hud)

    def panels_store(self):
        rgn_header,rgn_toolshelf,rgn_properties,rgn_hud = self._cc_panels_get_details()
        show_header,show_toolshelf,show_properties = rgn_header.height>1, rgn_toolshelf.width>1, rgn_properties.width>1
        show_hud = rgn_hud.width>1 if rgn_hud else False
        self._show_header = show_header
        self._show_toolshelf = show_toolshelf
        # self._show_properties = show_properties
        self._show_hud = show_hud

    def panels_restore(self):
        rgn_header,rgn_toolshelf,rgn_properties,rgn_hud = self._cc_panels_get_details()
        show_header,show_toolshelf,show_properties = rgn_header.height>1, rgn_toolshelf.width>1, rgn_properties.width>1
        show_hud = rgn_hud.width>1 if rgn_hud else False
        ctx = {
            'area': self._area,
            'space_data': self._space,
            'window': self._window,
            'screen': self._screen,
            'region': self._region,
        }
        if self._show_header and not show_header: toggle_screen_header(ctx)
        if self._show_toolshelf and not show_toolshelf: toggle_screen_toolbar(ctx)
        # if self._show_properties and not show_properties: toggle_screen_properties(ctx)
        if self._show_hud and not show_hud: toggle_screen_lastop(ctx)

    def panels_hide(self):
        rgn_header,rgn_toolshelf,rgn_properties,rgn_hud = self._cc_panels_get_details()
        show_header,show_toolshelf,show_properties = rgn_header.height>1, rgn_toolshelf.width>1, rgn_properties.width>1
        show_hud = rgn_hud.width>1 if rgn_hud else False
        ctx = {
            'area': self._area,
            'space_data': self._space,
            'window': self._window,
            'screen': self._screen,
            'region': self._region,
        }
        if show_header: toggle_screen_header(ctx)
        if show_toolshelf: toggle_screen_toolbar(ctx)
        # if show_properties: toggle_screen_properties(ctx)
        if show_hud: toggle_screen_lastop(ctx)

    ##############################################

@blender_version_wrapper('<=', '2.79')
def toggle_screen_header(ctx): bpy.ops.screen.header(ctx)
@blender_version_wrapper('>=', '2.80')
def toggle_screen_header(ctx):
    space = ctx['space_data'] if type(ctx) is dict else ctx.space_data
    space.show_region_header = not space.show_region_header

@blender_version_wrapper('<=', '2.79')
def toggle_screen_toolbar(ctx):
    bpy.ops.view3d.toolshelf(ctx)
@blender_version_wrapper('>=', '2.80')
def toggle_screen_toolbar(ctx):
    space = ctx['space_data'] if type(ctx) is dict else ctx.space_data
    space.show_region_toolbar = not space.show_region_toolbar

@blender_version_wrapper('<=', '2.79')
def toggle_screen_properties(ctx):
    bpy.ops.view3d.properties(ctx)
@blender_version_wrapper('>=', '2.80')
def toggle_screen_properties(ctx):
    space = ctx['space_data'] if type(ctx) is dict else ctx.space_data
    space.show_region_ui = not space.show_region_ui

@blender_version_wrapper('<=', '2.79')
def toggle_screen_lastop(ctx):
    # Blender 2.79 does not have a last operation region
    pass
@blender_version_wrapper('>=', '2.80')
def toggle_screen_lastop(ctx):
    space = ctx['space_data'] if type(ctx) is dict else ctx.space_data
    space.show_region_hud = not space.show_region_hud
