from ..operators.armature import *
from ..icons.__init__ import *

def ui_template_armature_header(layout, data):
    ob = data.name
    OB = ob.upper().replace('.', '_')

    row = layout.row()
    # Show/Hide bones
    row.prop(
        data,
        'show_bones',
        icon_value=(
            get_icon('MINIFIG_%s_ON' % OB)
            if data.show_bones
            else get_icon('MINIFIG_%s_OFF' % OB)
        ),
        toggle=True,
        emboss=False
    )
    # Show/Hide sub-panel
    row.prop(
        data,
        'show_panel',
        text=ob.upper(),
        icon=('REMOVE' if data.show_panel else 'ADD'),
        toggle=True,
        emboss=False
    )
    # Clear bones position
    row.operator(
        'mecafig.clear_bones',
        text='',
        icon='LOOP_BACK',
        emboss=False
    ).part = ob

def ui_template_armature_link(layout, data):
    row = layout.row()
    # Link
    row.prop(
        data,
        'enable_link',
        text=('Linked' if data.enable_link else 'Unlinked'),
        icon=('LINKED' if data.enable_link else 'UNLINKED'),
        toggle=True
    )

def ui_template_armature_rigid_soft(layout, data):
    row = layout.row()
    # Switch Rigid/Soft
    row.prop(
        data,
        'switch_rigid_soft',
        expand=True
    )

def ui_template_armature_fk_ik(layout, data, lock):
    col = layout.column()
    # Switch FK/IK
    row = col.row()
    row.prop(
        data,
        'switch_fk_ik',
        expand=True
    )
    # Snapping
    row.prop(
        data,
        'enable_snapping',
        text=('Snapped' if data.enable_snapping else 'Unsnapped'),
        icon=('SNAP_ON' if data.enable_snapping else 'SNAP_OFF'),
        toggle=True,
        emboss=False
    )
    # Lock IK Target
    if lock:
        if data.switch_fk_ik == 'IK':
            row = col.row(align=True)
            row.prop(
                data,
                'lock_ik_target',
                text='IK %s' %('Locked' if data.lock_ik_target else 'Unlocked'),
                icon=('LOCKED' if data.lock_ik_target else 'UNLOCKED'),
                toggle=True,
                emboss=True
            )
            # To bone
            row.prop(
                data,
                'lock_ik_target_to_bone',
                text=''
            )

def ui_template_armature_sub_panel(layout, data, lock):
    # Sub-panel header
    ui_template_armature_header(layout, data)
    # Sub-panel body
    if data.show_panel:
        sub = layout.column()
        sub.enabled = data.show_bones
        # Link
        ui_template_armature_link(sub, data)
        # Switch Rigid/Soft
        if data.name != 'Hip':
            ui_template_armature_rigid_soft(sub, data)
            # Switch FK/IK
            if not data.name.startswith('Hand'):
                if data.name == 'Body':
                    if data.switch_rigid_soft == 'SOFT':
                        ui_template_armature_fk_ik(sub, data, lock)
                else:
                    ui_template_armature_fk_ik(sub, data, lock)

        layout.separator()

def ui_template_armature(context, layout):
    ob = context.active_object
    data = ob.mecafig.armature

    if ob.mode == 'POSE':
        # Show Root, Specials & Anchors
        row = layout.row(align=True)
        row.prop(data, 'show_root_bones', text='Roots', toggle=True)
        row.prop(data, 'show_special_bones', text='Specials', toggle=True)
        row.prop(data, 'show_anchor_bones', text='Anchors', toggle=True)

        # Clear All, All Rigid & All Soft
        col = layout.column()
        col.operator('mecafig.clear_all_bones', text='Clear All')
        row = col.row(align=True)
        row.operator('mecafig.rigid_mode_all', text='All Rigid')
        row.operator('mecafig.soft_mode_all', text='All Soft')

        layout.separator()

        # ### SUB-PANELS ###
        PARTS = [part for part in MECAFIG]
        for part in reversed(PARTS):
            ui_template_armature_sub_panel(layout, data.parts[part], False)
        layout.separator()

        # Quit Pose Mode
        layout.operator('object.posemode_toggle', text='Quit Pose Mode')

    else:
        # Scale
        layout.prop(data, 'scale')
        # Enter Pose Mode
        layout.operator('object.posemode_toggle', text='Enter Pose Mode')
