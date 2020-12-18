from ..icons.__init__ import *

def ui_template_help(layout):
    box = layout.box()

    #box.label(text='Need help ?')

    col = box.column()

    row = col.row()
    row.alignment = 'LEFT'
    row.operator('wm.url_open',text='Mecabricks Community', icon_value=get_icon('mecabricks_logo_white'), emboss=False).url = 'https://www.mecabricks.com/en/forum/topic/1560'

    row = col.row()
    row.alignment = 'LEFT'
    row.operator('wm.url_open',text='MecaFig Video Tutorials', icon_value=get_icon('VIDEO'), emboss=False).url = 'https://www.youtube.com/playlist?list=PLZVEBAeoJ05VtohUCe8D8Pe24EqsUBQ6_'

    row = col.row()
    row.alignment = 'LEFT'
    row.operator('wm.url_open',text='MecaFig Online Manual', icon='HELP', emboss=False).url = 'https://www.dropbox.com/s/dsw312s60wk3fjo/mecafig_manual.pdf?dl=0'
