# -*- coding: utf-8 -*-
#
# split_clips_at_markers.py
# -----------------------------------------------------------------------------
# DaVinci Resolve script -- splits a clip in the active timeline at each
# marker that lives ON the clip (not timeline markers).
#
# -----------------------------------------------------------------------------
# INSTALL
#   Windows : %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
#   macOS   : ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
#
# RUN
#   Inside Resolve:  Workspace > Scripts > split_clips_at_markers
#   Make sure the Edit page is open and a clip is selected (playhead on it)
#   before running.
#
# -----------------------------------------------------------------------------
# HOW IT WORKS
#   1. Reads the clip currently under the playhead via GetCurrentVideoItem().
#      This is the clip you last clicked in the Edit page.
#   2. Uses GetTrackTypeAndIndex() on that clip to find which track it lives
#      on without needing to walk every track manually.
#   3. Reads that clip's markers via GetMarkers(). Marker offsets are relative
#      to the SOURCE MEDIA start, not the clip's trimmed in-point. The script
#      corrects for this using GetLeftOffset() so trimmed clips split correctly.
#   4. Before each split, all OTHER video tracks are locked via SetTrackLock()
#      so the split keystroke only affects the target track.
#   5. Splits are applied right-to-left (highest frame first) so earlier
#      marker positions remain valid after each cut.
#   6. Track lock states are snapshotted with GetIsTrackLocked() before the
#      run and fully restored afterwards, including any tracks you had manually
#      locked before running.
#   7. Logs every action to the Resolve console (Workspace > Console).
#
# -----------------------------------------------------------------------------
# WHY A KEYSTROKE INSTEAD OF AN API CALL
#   The Resolve scripting API (as of v20.3.1 build 6, README.txt dated
#   7 Oct 2025) does NOT include a SplitClips() or equivalent function on
#   the Timeline object. The function appears in some community documentation
#   but returns None (not callable) in this version, confirmed by direct test:
#
#     timeline.SplitClips([clip])
#     --> TypeError: 'NoneType' object is not callable
#
#   The only reliable alternative is to move the playhead to the target frame
#   via SetCurrentTimecode() and then fire Resolve's Split Clip keyboard
#   shortcut. The script uses Windows SendInput (ctypes) to send the keypress
#   rather than the deprecated keybd_event API.
#
#   If a future Resolve version adds a working SplitClips() function, the
#   entire keyboard/ctypes/focus/timing section can be removed and replaced
#   with a single call: timeline.SplitClips([clip])
#   You can test this in the Resolve Python console with:
#     timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
#     clip = timeline.GetItemListInTrack("video", 1)[0]
#     print(timeline.SplitClips([clip]))
#   If it prints True, the API now works and the keyboard approach is no longer
#   needed.
#
# -----------------------------------------------------------------------------
# WHICH CLIPS GET SPLIT
#   Only the clip currently under the playhead is split. If no clip is under
#   the playhead, the script falls back to processing ALL clips on ALL video
#   tracks that have valid in-range markers.
#
#   A marker is "in-range" if, after correcting for left trim offset, its
#   computed timeline frame falls strictly inside the clip's start/end bounds.
#   Markers at offset 0 (the clip's own in-point) are always skipped since
#   splitting exactly at an edge is a no-op in Resolve.
#
#   Sub-clips produced by a previous split run inherit the original clip's
#   markers, but those markers now fall outside the sub-clip's shorter range,
#   so they are automatically skipped without needing any special handling.
#
# -----------------------------------------------------------------------------
# MARKER OFFSET CORRECTION FOR TRIMMED CLIPS
#   GetMarkers() returns frame offsets measured from the SOURCE MEDIA start.
#   GetLeftOffset() returns how many source frames are hidden by the left trim.
#   The correct timeline frame for a split is:
#
#     timeline_frame = clip.GetStart() + marker_offset - clip.GetLeftOffset()
#
#   For untrimmed clips GetLeftOffset() == 0 and this formula is a no-op.
#
# -----------------------------------------------------------------------------
# TRACK LOCKING STRATEGY
#   Resolve's Split Clip shortcut cuts ALL unlocked tracks at the playhead.
#   To prevent clips on other tracks from being accidentally split, the script:
#     1. Calls GetIsTrackLocked(trackType, i) to snapshot the lock state of
#        every track before starting. (Correct API name -- NOT GetTrackLock.)
#     2. Calls SetTrackLock(trackType, i, True) on every track except the one
#        being processed before each individual split.
#     3. Calls SetTrackLock(trackType, i, original_state) after the track is
#        fully processed to restore exactly what was locked before.
#
# -----------------------------------------------------------------------------
# CLIP SELECTION
#   GetCurrentVideoItem() returns the clip at the playhead position on the
#   currently active video track. This is the clip you last clicked.
#   Note: there is no GetSelectedTimelineItems() in this API version, so
#   GetCurrentVideoItem() is the closest available equivalent.
#
#   Once we have the selected clip, GetTrackTypeAndIndex() tells us exactly
#   which track it lives on in one call, replacing the manual track-walk that
#   was needed in earlier versions of this script.
#
# -----------------------------------------------------------------------------
# CONFIGURATION
#   All user-editable settings are in the CONFIG block immediately below.
#
# SPLIT SHORTCUT KEY  (SPLIT_KEY_VK)
#   The virtual key code of your Split Clip shortcut in Resolve.
#   Default: 0x45 = E  (this project's reassigned shortcut)
#   Resolve factory default is Ctrl+\ (0xDC with SPLIT_KEY_NEEDS_CTRL=True).
#
#   Common virtual key codes:
#     A-Z        -> 0x41 to 0x5A  (e.g. E = 0x45, B = 0x42)
#     Backslash  -> 0xDC           (Resolve factory default key)
#     Any letter -> ord('X')       e.g. ord('E') == 0x45
#   Full reference: https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
#
#   If your shortcut requires Ctrl (e.g. Ctrl+\), set SPLIT_KEY_NEEDS_CTRL=True.
#
# SELECTION TOOL KEY  (SELECTION_KEY_VK)
#   Pressed before each split to ensure the Selection (arrow) tool is active.
#   The split shortcut does nothing if the Blade tool (B) is selected instead.
#   Default: 0x41 = A  (Resolve built-in, do not change unless reassigned.)
#
# AUDIO TRACKS  (SPLIT_AUDIO)
#   Set to True to also split audio clips at their markers.
#   When True, audio tracks are locked/unlocked independently of video.
#
# MARKER FILTER  (MARKER_COLOR_FILTER)
#   Leave as [] to split at ALL marker colours.
#   Restrict to specific colours with a list of colour name strings, e.g.:
#     ["Blue", "Red"]
#   Valid colour names (case-sensitive):
#     Blue, Cyan, Green, Yellow, Red, Pink, Purple, Fuchsia,
#     Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream
#
# TIMING  (DELAY_* values in seconds)
#   DELAY_AFTER_PLAYHEAD_MOVE : wait after SetCurrentTimecode() before keypress
#   DELAY_AFTER_SPLIT         : wait after each split for Resolve to process it
#   DELAY_AFTER_FOCUS         : wait after focusing the Resolve window
#   DELAY_AFTER_TRACK_LOCK    : wait after each SetTrackLock() call
#   Increase if splits are missed on slower machines. Safe to reduce on fast ones.
# -----------------------------------------------------------------------------

import sys
import ctypes
import time


# =============================================================================
#  CONFIG -- edit this section to customise the script
# =============================================================================

# Virtual key code of your Split Clip shortcut in Resolve.
# Default: 0x45 = E
SPLIT_KEY_VK = 0x45

# Set to True if the split shortcut requires Ctrl held down (e.g. Ctrl+\).
# Set to False if it is a bare single key (e.g. just E).
SPLIT_KEY_NEEDS_CTRL = False

# Virtual key code for Resolve's Selection tool shortcut.
# Default: 0x41 = A  (Resolve built-in)
SELECTION_KEY_VK = 0x41

# Process audio tracks as well as video tracks?
SPLIT_AUDIO = False

# Only split on markers of these colours (case-sensitive).
# Leave as [] to process ALL marker colours.
MARKER_COLOR_FILTER = []      # e.g. ["Blue", "Red"] or [] for all

# Seconds to wait after moving the playhead before sending the shortcut.
DELAY_AFTER_PLAYHEAD_MOVE = 0.1

# Seconds to wait after each split for Resolve to finish processing.
DELAY_AFTER_SPLIT = 0.15

# Seconds to wait after focusing the Resolve window before sending keys.
DELAY_AFTER_FOCUS = 0.2

# Seconds to wait after each SetTrackLock() call.
DELAY_AFTER_TRACK_LOCK = 0.05

# =============================================================================
#  END OF CONFIG -- no need to edit anything below this line
# =============================================================================


# --- Windows INPUT structs for SendInput -------------------------------------
# We use SendInput (not the deprecated keybd_event) because it is the correct
# modern Windows API for synthetic keystrokes and works reliably inside
# Resolve's embedded Python environment.

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
        ("_pad", ctypes.c_byte * 32),   # pad to MOUSEINPUT size on 64-bit
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",   ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]

INPUT_KEYBOARD  = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL      = 0x11


def _make_key_input(vk, key_up=False):
    flags = KEYEVENTF_KEYUP if key_up else 0
    return INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, dwFlags=flags))
    )


# --- Window finding ----------------------------------------------------------
# SendInput sends keystrokes to whichever window currently has focus.
# We must focus the Resolve window before each split or the keypress lands
# in the script console instead of the timeline.
#
# FindWindowW is tried first (fast, exact title match).
# EnumWindows is the fallback (partial title match).
# The EnumWindows callback uses c_void_p so hwnd arrives as a plain Python
# int -- using LP_c_long caused TypeError in Resolve's embedded Python.
# Results are collected into a Python list rather than assigned to a ctypes
# value, which also avoids that LP_c_long assignment issue.

def get_resolve_hwnd():
    """Return the HWND of the DaVinci Resolve main window, or 0 if not found."""
    user32 = ctypes.windll.user32

    hwnd = user32.FindWindowW(None, "DaVinci Resolve")
    if hwnd:
        print("  [focus] found Resolve window via FindWindowW (hwnd=%d)" % hwnd)
        return hwnd

    results = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p)

    @WNDENUMPROC
    def _cb(hwnd, _lParam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length < 1:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "DaVinci Resolve" in buf.value:
            results.append(hwnd)
            return False
        return True

    user32.EnumWindows(_cb, 0)

    if results:
        print("  [focus] found Resolve window via EnumWindows (hwnd=%d)" % results[0])
        return results[0]

    print("  ! Could not find DaVinci Resolve window -- splits may miss.")
    return 0


def focus_resolve_window(hwnd):
    """Bring the Resolve window to the foreground."""
    if not hwnd:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)   # SW_RESTORE in case minimised
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(DELAY_AFTER_FOCUS)


# --- Keystroke sending -------------------------------------------------------

def send_inputs(*inputs):
    """Send a sequence of INPUT structs via SendInput."""
    user32 = ctypes.windll.user32
    arr    = (INPUT * len(inputs))(*inputs)
    n_sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n_sent != len(inputs):
        print("  ! SendInput: only %d/%d events sent." % (n_sent, len(inputs)))


def activate_selection_tool():
    """Press SELECTION_KEY_VK to ensure the Selection tool is active.
    The split shortcut is a no-op if the Blade tool (B) is active instead."""
    send_inputs(
        _make_key_input(SELECTION_KEY_VK),
        _make_key_input(SELECTION_KEY_VK, key_up=True),
    )
    time.sleep(0.05)


def send_split_shortcut():
    """Send the configured split shortcut (with or without Ctrl)."""
    if SPLIT_KEY_NEEDS_CTRL:
        send_inputs(
            _make_key_input(VK_CONTROL),
            _make_key_input(SPLIT_KEY_VK),
            _make_key_input(SPLIT_KEY_VK,  key_up=True),
            _make_key_input(VK_CONTROL,    key_up=True),
        )
    else:
        send_inputs(
            _make_key_input(SPLIT_KEY_VK),
            _make_key_input(SPLIT_KEY_VK, key_up=True),
        )
    time.sleep(DELAY_AFTER_SPLIT)


# --- Resolve bootstrap -------------------------------------------------------

def get_resolve():
    """Return the top-level Resolve object.

    Resolution order:
      1. fusionscript  -- injected by Resolve when running from Workspace > Scripts
      2. DaVinciResolveScript on PYTHONPATH  -- standard external use
      3. DaVinciResolveScript loaded from its default install path  -- works even
         when PYTHONPATH is not configured (adapted from Blackmagic's own examples)
    """
    # 1. Fusion-injected module (most common when running from inside Resolve)
    try:
        import fusionscript as bmd
        r = bmd.scriptapp("Resolve")
        if r:
            return r
    except ImportError:
        pass

    # 2. Standard import via PYTHONPATH
    try:
        import DaVinciResolveScript as bmd
        return bmd.scriptapp("Resolve")
    except ImportError:
        pass

    # 3. Load from the known default install location for each platform.
    #    This handles the common case where PYTHONPATH was never configured.
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
        spec   = importlib.util.spec_from_file_location("DaVinciResolveScript", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["DaVinciResolveScript"] = module
        spec.loader.exec_module(module)
        return module.scriptapp("Resolve")
    except Exception as e:
        print("ERROR: Could not load DaVinciResolveScript.")
        print("  Tried path: %s" % module_path)
        print("  Reason: %s" % e)
        print("  Make sure DaVinci Resolve is running and the script is")
        print("  either launched from Workspace > Scripts or PYTHONPATH")
        print("  includes the Scripting/Modules directory.")
        sys.exit(1)


# --- Timecode helpers --------------------------------------------------------

def frames_to_timecode(frame, fps, drop_frame=False):
    """Convert an absolute frame number to a SMPTE HH:MM:SS:FF string.
    SetCurrentTimecode() requires exactly this format."""
    fps_int = round(fps)
    if drop_frame and fps_int in (30, 60):
        drop_frames      = round(fps * 0.066666)
        frames_per_10min = round(fps * 600)
        frames_per_min   = round(fps * 60) - drop_frames
        d, m = divmod(frame, frames_per_10min)
        if m > drop_frames:
            frame += drop_frames * (9 * d + (m - drop_frames) // frames_per_min)
        else:
            frame += drop_frames * 9 * d
    ff            = frame % fps_int
    total_seconds = frame // fps_int
    hh = total_seconds // 3600
    mm = (total_seconds // 60) % 60
    ss = total_seconds % 60
    return "%02d:%02d:%02d:%02d" % (hh, mm, ss, ff)


def parse_fps(timeline):
    """Return (fps_float, is_drop_frame) for the timeline.
    GetSetting('timelineFrameRate') returns a float in some Resolve versions
    and a string like '29.97 DF' in others -- both are handled."""
    setting = timeline.GetSetting("timelineFrameRate")
    if isinstance(setting, (int, float)):
        return float(setting), False
    s    = str(setting)
    drop = "DF" in s.upper() or "DROP" in s.upper()
    try:
        fps = float(s.replace("DF", "").replace("df", "").strip())
    except ValueError:
        print("WARNING: Could not parse FPS from '%s', defaulting to 24." % s)
        fps = 24.0
    return fps, drop


# --- Track locking -----------------------------------------------------------
# The correct API function name is GetIsTrackLocked() -- NOT GetTrackLock().
# GetTrackLock() does not exist in the v20.3.1 API and silently returns None,
# causing the original snapshot to always store False and preventing correct
# restoration of tracks that were manually locked before running the script.

def get_track_lock_states(timeline, track_type, count):
    """Snapshot {track_index: is_locked} for all tracks using GetIsTrackLocked."""
    states = {}
    for i in range(1, count + 1):
        try:
            states[i] = bool(timeline.GetIsTrackLocked(track_type, i))
        except Exception:
            states[i] = False
    return states


def lock_all_tracks_except(timeline, track_type, count, keep_unlocked_index):
    """Lock every track of track_type except keep_unlocked_index."""
    for i in range(1, count + 1):
        if i != keep_unlocked_index:
            try:
                timeline.SetTrackLock(track_type, i, True)
            except Exception:
                pass
    time.sleep(DELAY_AFTER_TRACK_LOCK)


def restore_track_lock_states(timeline, track_type, original_states):
    """Restore all tracks to their pre-run lock states."""
    for i, was_locked in original_states.items():
        try:
            timeline.SetTrackLock(track_type, i, was_locked)
        except Exception:
            pass
    time.sleep(DELAY_AFTER_TRACK_LOCK)


# --- Core logic --------------------------------------------------------------

def get_valid_split_frames(clip, markers):
    """Return a reverse-sorted list of (timeline_frame, offset, info) tuples.

    Marker offsets from GetMarkers() are relative to the SOURCE MEDIA start,
    not the clip's trimmed in-point. GetLeftOffset() returns how many source
    frames are hidden by the left trim. The correct timeline frame is:

        timeline_frame = clip.GetStart() + marker_offset - clip.GetLeftOffset()

    Markers at offset 0 (clip in-point) and markers outside the clip's playable
    range are skipped. Sub-clips from previous splits inherit the original
    markers but those fall outside the sub-clip's shorter range, so they are
    automatically skipped here without any special handling.
    """
    clip_start = clip.GetStart()
    clip_end   = clip.GetEnd()

    try:
        left_offset = clip.GetLeftOffset()
    except Exception:
        left_offset = 0

    if left_offset:
        print("    [trim] clip has left offset of %d source frames" % left_offset)

    split_frames = []
    for offset, info in markers.items():
        if offset == 0:
            continue
        tf = clip_start + offset - left_offset
        if clip_start < tf < clip_end:
            split_frames.append((tf, offset, info))
        else:
            print("    ! Offset %d -> frame %d outside clip range [%d,%d] -- skipped."
                  % (offset, tf, clip_start, clip_end))

    split_frames.sort(key=lambda x: x[0], reverse=True)
    return split_frames


def split_at_frame(timeline, timeline_frame, fps, drop, resolve_hwnd):
    """Move playhead to timeline_frame and fire the split shortcut."""
    tc = frames_to_timecode(timeline_frame, fps, drop)
    if not timeline.SetCurrentTimecode(tc):
        print("  ! SetCurrentTimecode(%s) failed -- skipping." % tc)
        return False
    time.sleep(DELAY_AFTER_PLAYHEAD_MOVE)
    focus_resolve_window(resolve_hwnd)
    activate_selection_tool()
    send_split_shortcut()
    return True


def process_clip(timeline, clip, track_type, track_index, track_count,
                 fps, drop, resolve_hwnd):
    """Split one clip at all its valid in-range markers.
    Locks all other tracks before each split and restores them after."""
    clip_name = clip.GetName()
    markers   = clip.GetMarkers()

    if not markers:
        print("  Clip '%s' has no markers -- nothing to do." % clip_name)
        return 0

    if MARKER_COLOR_FILTER:
        markers = {o: m for o, m in markers.items()
                   if m.get("color", "") in MARKER_COLOR_FILTER}
    if not markers:
        print("  Clip '%s' has no markers matching the colour filter." % clip_name)
        return 0

    split_frames = get_valid_split_frames(clip, markers)
    if not split_frames:
        print("  Clip '%s' has no splittable markers in range." % clip_name)
        return 0

    skipped_zero = sum(1 for o in markers if o == 0)
    print("\n  Clip : '%s'  (track %s%d, start frame %d)"
          % (clip_name, track_type[0].upper(), track_index, clip.GetStart()))
    print("  Splits: %d queued%s"
          % (len(split_frames),
             ("  |  %d at offset 0 skipped" % skipped_zero) if skipped_zero else ""))

    original_lock_states = get_track_lock_states(timeline, track_type, track_count)
    total_splits = 0

    for tf, offset, marker_info in split_frames:
        color = marker_info.get("color", "?")
        name  = marker_info.get("name",  "")
        print("    -> frame %d  (clip offset %d)  [%s | '%s']"
              % (tf, offset, color, name))

        lock_all_tracks_except(timeline, track_type, track_count, track_index)

        if split_at_frame(timeline, tf, fps, drop, resolve_hwnd):
            total_splits += 1

    restore_track_lock_states(timeline, track_type, original_lock_states)
    return total_splits


# --- Entry point -------------------------------------------------------------

def main():
    resolve = get_resolve()

    pm = resolve.GetProjectManager()
    if not pm:
        print("ERROR: Could not get ProjectManager.")
        sys.exit(1)

    project = pm.GetCurrentProject()
    if not project:
        print("ERROR: No project is currently open.")
        sys.exit(1)

    timeline = project.GetCurrentTimeline()
    if not timeline:
        print("ERROR: No active timeline found.")
        sys.exit(1)

    # Edit page must be active for the split shortcut to work
    resolve.OpenPage("edit")
    time.sleep(0.3)

    timeline_name = timeline.GetName()
    fps, drop     = parse_fps(timeline)

    split_key_label = ("Ctrl+%s" % chr(SPLIT_KEY_VK)) if SPLIT_KEY_NEEDS_CTRL else chr(SPLIT_KEY_VK)
    color_label     = ", ".join(MARKER_COLOR_FILTER) if MARKER_COLOR_FILTER else "all colours"

    print("\n" + "-"*60)
    print("  Split Clips at Markers")
    print("  Timeline     : %s" % timeline_name)
    print("  FPS          : %s%s" % (fps, "  (drop-frame)" if drop else ""))
    print("  Split key    : %s" % split_key_label)
    print("  Marker filter: %s" % color_label)
    print("  Split audio  : %s" % ("yes" if SPLIT_AUDIO else "no"))
    print("-"*60)

    resolve_hwnd = get_resolve_hwnd()
    focus_resolve_window(resolve_hwnd)

    grand_total  = 0
    video_count  = timeline.GetTrackCount("video")

    # GetCurrentVideoItem() returns the clip under the playhead -- the one the
    # user last clicked. GetTrackTypeAndIndex() on that clip directly returns
    # [trackType, trackIndex] without needing to walk all tracks manually.
    selected = timeline.GetCurrentVideoItem()

    if selected:
        track_info = selected.GetTrackTypeAndIndex()
        track_type  = track_info[0]   # "video"
        track_index = track_info[1]   # 1-based

        print("  Selected clip : '%s' (track %s%d, start frame %d)"
              % (selected.GetName(), track_type[0].upper(),
                 track_index, selected.GetStart()))
        print("\n[Processing selected clip only]")

        grand_total += process_clip(
            timeline, selected, track_type, track_index, video_count,
            fps, drop, resolve_hwnd)
    else:
        # Fallback: no clip selected -- process every clip on every video track
        print("  No clip selected -- processing ALL clips on ALL video tracks.")
        print("\n[Video tracks: %d]" % video_count)
        for i in range(1, video_count + 1):
            print("\n Track V%d" % i)
            clips = timeline.GetItemListInTrack("video", i)
            if not clips:
                continue
            for clip in clips:
                grand_total += process_clip(
                    timeline, clip, "video", i, video_count,
                    fps, drop, resolve_hwnd)

    if SPLIT_AUDIO:
        audio_count = timeline.GetTrackCount("audio")
        print("\n[Audio tracks: %d]" % audio_count)
        for i in range(1, audio_count + 1):
            print("\n Track A%d" % i)
            clips = timeline.GetItemListInTrack("audio", i)
            if not clips:
                continue
            for clip in clips:
                grand_total += process_clip(
                    timeline, clip, "audio", i, audio_count,
                    fps, drop, resolve_hwnd)

    print("\n" + "-"*60)
    print("  Done.  Total splits performed: %d" % grand_total)
    print("-"*60 + "\n")


if __name__ == "__main__":
    main()
