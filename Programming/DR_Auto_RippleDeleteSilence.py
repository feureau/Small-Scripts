# -*- coding: utf-8 -*-
#
# DR_Auto_RippleDeleteSilence.py
# -----------------------------------------------------------------------------
# DaVinci Resolve script -- applies the "Ripple Delete Silence" (or any other)
# shortcut to clips in the active timeline.
#
# -----------------------------------------------------------------------------
# INSTALL
#   Windows : %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
#   macOS   : ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
#
# RUN
#   Inside Resolve:  Workspace > Scripts > DR_Auto_RippleDeleteSilence
#   Make sure the Edit page is open before running.
#
# -----------------------------------------------------------------------------
# HOW IT WORKS
#   1. Reads the clip currently under the playhead via GetCurrentVideoItem().
#      If no clip is selected, falls back to processing ALL clips on all tracks.
#   2. Clips are processed from right to left (highest frame first) so that
#      ripple deletes don't shift the timeline for clips that haven't been processed yet.
#   3. Before applying the shortcut to each clip, all OTHER tracks are locked 
#      via SetTrackLock() so the shortcut only affects the target track.
#   4. Moves the playhead to the start of the clip, then fires the keyboard
#      shortcut for Ripple Delete Silence.
#   5. Restores original track lock states.
#
# IMPORTANT: 
#   For this to work reliably, you may need "Selection Follows Playhead" 
#   enabled in Resolve (Timeline > Selection Follows Playhead), so that moving
#   the playhead to the clip automatically selects it before the shortcut is pressed.
#
# -----------------------------------------------------------------------------

import sys
import ctypes
import time

# =============================================================================
#  CONFIG -- edit this section to customise the script
# =============================================================================

# Virtual key code of your Ripple Delete Silence shortcut in Resolve.
# You MUST assign a keyboard shortcut to the required function in Resolve.
# F8 = 0x77
SHORTCUT_VK = 0x77

# Modifier keys for your shortcut
SHORTCUT_NEEDS_CTRL  = False
SHORTCUT_NEEDS_SHIFT = False
SHORTCUT_NEEDS_ALT   = False

# Process audio tracks as well as video tracks?
PROCESS_AUDIO = False

# Timing Configuration (Seconds)
# Seconds to wait after moving the playhead before sending the shortcut.
DELAY_AFTER_PLAYHEAD_MOVE = 0.1

# Seconds to wait after sending the shortcut for Resolve to finish processing.
DELAY_AFTER_SHORTCUT = 0.5

# Seconds to wait after focusing the Resolve window before sending keys.
DELAY_AFTER_FOCUS = 0.2

# Seconds to wait after each SetTrackLock() call.
DELAY_AFTER_TRACK_LOCK = 0.05

# =============================================================================
#  END OF CONFIG -- no need to edit anything below this line
# =============================================================================

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki",   KEYBDINPUT),
        ("_pad", ctypes.c_byte * 32),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",   ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]

INPUT_KEYBOARD  = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT        = 0x10
VK_CONTROL      = 0x11
VK_MENU         = 0x12  # Alt

def _make_key_input(vk, key_up=False):
    flags = KEYEVENTF_KEYUP if key_up else 0
    return INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, dwFlags=flags))
    )

def get_resolve_hwnd():
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "DaVinci Resolve")
    if hwnd:
        return hwnd
    results = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    @WNDENUMPROC
    def _cb(hwnd, _lParam):
        if not user32.IsWindowVisible(hwnd): return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length < 1: return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "DaVinci Resolve" in buf.value:
            results.append(hwnd)
            return False
        return True
    user32.EnumWindows(_cb, 0)
    if results: return results[0]
    print("  ! Could not find DaVinci Resolve window -- shortcut may miss.")
    return 0

def focus_resolve_window(hwnd):
    if not hwnd: return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(DELAY_AFTER_FOCUS)

def send_inputs(*inputs):
    user32 = ctypes.windll.user32
    arr    = (INPUT * len(inputs))(*inputs)
    n_sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n_sent != len(inputs):
        print("  ! SendInput: only %d/%d events sent." % (n_sent, len(inputs)))

def send_shortcut():
    inputs = []
    if SHORTCUT_NEEDS_CTRL:
        inputs.append(_make_key_input(VK_CONTROL))
    if SHORTCUT_NEEDS_SHIFT:
        inputs.append(_make_key_input(VK_SHIFT))
    if SHORTCUT_NEEDS_ALT:
        inputs.append(_make_key_input(VK_MENU))

    inputs.append(_make_key_input(SHORTCUT_VK))
    inputs.append(_make_key_input(SHORTCUT_VK, key_up=True))

    if SHORTCUT_NEEDS_ALT:
        inputs.append(_make_key_input(VK_MENU, key_up=True))
    if SHORTCUT_NEEDS_SHIFT:
        inputs.append(_make_key_input(VK_SHIFT, key_up=True))
    if SHORTCUT_NEEDS_CTRL:
        inputs.append(_make_key_input(VK_CONTROL, key_up=True))

    send_inputs(*inputs)
    time.sleep(DELAY_AFTER_SHORTCUT)

def get_resolve():
    try:
        import fusionscript as bmd
        r = bmd.scriptapp("Resolve")
        if r: return r
    except ImportError: pass
    try:
        import DaVinciResolveScript as bmd
        return bmd.scriptapp("Resolve")
    except ImportError: pass
    import importlib.util
    import os
    if sys.platform.startswith("darwin"):
        module_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/DaVinciResolveScript.py"
    elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
        module_path = os.path.join(
            os.getenv("PROGRAMDATA", ""),
            "Blackmagic Design", "DaVinci Resolve", "Support",
            "Developer", "Scripting", "Modules", "DaVinciResolveScript.py"
        )
    else:
        module_path = "/opt/resolve/Developer/Scripting/Modules/DaVinciResolveScript.py"
    try:
        spec = importlib.util.spec_from_file_location("DaVinciResolveScript", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["DaVinciResolveScript"] = module
        spec.loader.exec_module(module)
        return module.scriptapp("Resolve")
    except Exception as e:
        print("ERROR: Could not load DaVinciResolveScript.")
        sys.exit(1)

def frames_to_timecode(frame, fps, drop_frame=False):
    fps_int = round(fps)
    if drop_frame and fps_int in (30, 60):
        drop_frames = round(fps * 0.066666)
        frames_per_10min = round(fps * 600)
        frames_per_min = round(fps * 60) - drop_frames
        d, m = divmod(frame, frames_per_10min)
        if m > drop_frames:
            frame += drop_frames * (9 * d + (m - drop_frames) // frames_per_min)
        else:
            frame += drop_frames * 9 * d
    ff = frame % fps_int
    total_seconds = frame // fps_int
    hh = total_seconds // 3600
    mm = (total_seconds // 60) % 60
    ss = total_seconds % 60
    return "%02d:%02d:%02d:%02d" % (hh, mm, ss, ff)

def parse_fps(timeline):
    setting = timeline.GetSetting("timelineFrameRate")
    if isinstance(setting, (int, float)):
        return float(setting), False
    s = str(setting)
    drop = "DF" in s.upper() or "DROP" in s.upper()
    try:
        fps = float(s.replace("DF", "").replace("df", "").strip())
    except ValueError:
        fps = 24.0
    return fps, drop

def get_track_lock_states(timeline, track_type, count):
    states = {}
    for i in range(1, count + 1):
        try: states[i] = bool(timeline.GetIsTrackLocked(track_type, i))
        except Exception: states[i] = False
    return states

def lock_all_tracks_except(timeline, track_type, count, keep_unlocked_index):
    for i in range(1, count + 1):
        if i != keep_unlocked_index:
            try: timeline.SetTrackLock(track_type, i, True)
            except Exception: pass
    time.sleep(DELAY_AFTER_TRACK_LOCK)

def restore_track_lock_states(timeline, track_type, original_states):
    for i, was_locked in original_states.items():
        try: timeline.SetTrackLock(track_type, i, was_locked)
        except Exception: pass
    time.sleep(DELAY_AFTER_TRACK_LOCK)

def process_clip(timeline, clip, track_type, track_index, track_count, fps, drop, resolve_hwnd):
    clip_name = clip.GetName()
    start_frame = clip.GetStart()
    
    # Mimic split_clips_at_markers: only process if the clip has markers
    markers = clip.GetMarkers()
    if not markers:
        return False

    print("\n  Clip : '%s'  (track %s%d, start frame %d)"
          % (clip_name, track_type[0].upper(), track_index, start_frame))

    # Track locking might deselect the clip, so we will disable it for Ripple Delete Silence.
    # original_lock_states = get_track_lock_states(timeline, track_type, track_count)
    # lock_all_tracks_except(timeline, track_type, track_count, track_index)

    # Move playhead to the start of the clip
    tc = frames_to_timecode(start_frame, fps, drop)
    if not timeline.SetCurrentTimecode(tc):
        print("  ! SetCurrentTimecode(%s) failed -- skipping." % tc)
        # restore_track_lock_states(timeline, track_type, original_lock_states)
        return False

    time.sleep(DELAY_AFTER_PLAYHEAD_MOVE)
    focus_resolve_window(resolve_hwnd)
    
    # Send the Ripple Delete Silence shortcut
    send_shortcut()

    # restore_track_lock_states(timeline, track_type, original_lock_states)
    return True

def main():
    resolve = get_resolve()
    pm = resolve.GetProjectManager()
    if not pm: sys.exit(1)
    project = pm.GetCurrentProject()
    if not project: sys.exit(1)
    timeline = project.GetCurrentTimeline()
    if not timeline: sys.exit(1)

    resolve.OpenPage("edit")
    time.sleep(0.3)

    fps, drop = parse_fps(timeline)
    resolve_hwnd = get_resolve_hwnd()
    focus_resolve_window(resolve_hwnd)

    grand_total = 0
    video_count = timeline.GetTrackCount("video")
    selected_video = timeline.GetCurrentVideoItem()

    if selected_video:
        track_info = selected_video.GetTrackTypeAndIndex()
        track_type = track_info[0]
        track_index = track_info[1]
        print("\n[Processing all clips on track V%d]" % track_index)
        
        clips = timeline.GetItemListInTrack("video", track_index)
        if clips:
            clips_sorted = sorted(clips, key=lambda c: c.GetStart(), reverse=True)
            for clip in clips_sorted:
                if process_clip(timeline, clip, track_type, track_index, video_count, fps, drop, resolve_hwnd):
                    grand_total += 1
    else:
        print("\n[No video clip selected -- processing ALL clips on ALL video tracks]")
        for i in range(1, video_count + 1):
            clips = timeline.GetItemListInTrack("video", i)
            if not clips: continue
            
            # Sort right-to-left so ripple deletes don't shift upcoming clips
            clips_sorted = sorted(clips, key=lambda c: c.GetStart(), reverse=True)
            for clip in clips_sorted:
                if process_clip(timeline, clip, "video", i, video_count, fps, drop, resolve_hwnd):
                    grand_total += 1

    if PROCESS_AUDIO:
        audio_count = timeline.GetTrackCount("audio")
        selected_audio = timeline.GetCurrentAudioItem()
        if selected_audio:
            track_info = selected_audio.GetTrackTypeAndIndex()
            track_type = track_info[0]
            track_index = track_info[1]
            print("\n[Processing all clips on track A%d]" % track_index)
            
            clips = timeline.GetItemListInTrack("audio", track_index)
            if clips:
                clips_sorted = sorted(clips, key=lambda c: c.GetStart(), reverse=True)
                for clip in clips_sorted:
                    if process_clip(timeline, clip, track_type, track_index, audio_count, fps, drop, resolve_hwnd):
                        grand_total += 1
        else:
            print("\n[Processing ALL clips on ALL audio tracks]")
            for i in range(1, audio_count + 1):
                clips = timeline.GetItemListInTrack("audio", i)
                if not clips: continue
                clips_sorted = sorted(clips, key=lambda c: c.GetStart(), reverse=True)
                for clip in clips_sorted:
                    if process_clip(timeline, clip, "audio", i, audio_count, fps, drop, resolve_hwnd):
                        grand_total += 1

    print("\n" + "-"*60)
    print("  Done.  Total clips processed: %d" % grand_total)
    print("-"*60 + "\n")

if __name__ == "__main__":
    main()
