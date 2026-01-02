from .extension import PerspectiveCropExtension

# Register the extension with Krita
application = Krita.instance()
extension = PerspectiveCropExtension(parent=application)
application.addExtension(extension)