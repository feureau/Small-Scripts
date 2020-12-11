import base64
import os
import bpy

class TextureLoader():
    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self, dir):
        self.dir = dir

    # --------------------------------------------------------------------------
    # Load texture
    # --------------------------------------------------------------------------
    def load(self, filename, **kwargs):
        # Load image from base64 data
        if 'base64' in kwargs:
            # Save texture in temporary file to be imported into Blender
            filepath = os.path.join(self.dir, filename)
            with open(filepath, 'wb') as fh:
                fh.write(base64.b64decode(kwargs['base64']))

            # Import and pack image
            image = bpy.data.images.load(filepath, check_existing=False)
            image.pack()

            # Delete temporary file if any
            if os.path.exists(filepath):
                os.remove(filepath)

        # Load image from file path
        elif 'path' in kwargs:
            pass

        # load image from url
        elif 'url' in kwargs:
            pass

        # Colour space
        color_space = kwargs['colorspace'] if 'colorspace' in kwargs else 'sRGB'
        image.colorspace_settings.name = color_space

        # Alpha
        alpha_mode = kwargs['alpha_mode'] if 'alpha_mode' in kwargs else 'CHANNEL_PACKED'
        image.alpha_mode = alpha_mode

        return image
