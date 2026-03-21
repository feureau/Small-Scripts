# -*- coding: utf-8 -*-
#
# split_clips_at_markers.py
# -----------------------------------------------------------------------------
# DaVinci Resolve script -- splits clips in the active timeline at each
# marker that lives ON the clip (not timeline markers).
#
# INSTALL
#   Windows : %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
#   macOS   : ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
#
# RUN
#   Inside Resolve:  Workspace > Scripts > split_clips_at_markers
#
# HOW IT WORKS
#   1. Scans every video track for clips that have at least one marker
#      sitting within the clip's own range (not at offset 0).
#   2. Before splitting a clip, all OTHER video tracks are locked so the
#      split keystroke only affects the track being processed.
#   3. Splits are applied right-to-left so earlier marker positions stay valid.
#   4. All tracks are restored to their original lock state when done.
#   5. Logs every action to the Resolve console (Workspace > Console).
#
# WHICH CLIPS GET SPLIT
#   Every clip that has at least one marker within its own playable range.
#   Clips with only out-of-range markers (e.g. sub-clips left over from a
#   previous split run) are automatically skipped.
#
# CONFIGURATION
#   All user-editable settings are in the CONFIG block immediately below.
#
# SPLIT SHORTCUT KEY  (SPLIT_KEY_VK)
#   The script sends a keystroke to trigger Resolve's Split Clip command.
#   Default is 0x45 (E) -- change this if you use a different shortcut.
#
#   Common virtual key codes:
#     E          -> 0x45   (default in this script)
#     Backslash  -> 0xDC   (Resolve factory default, used with Ctrl)
#     B          -> 0x42
#     Any letter -> ord('X')  e.g. ord('E') == 0x45
#   Full list: https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
#
#   If your shortcut requires Ctrl (e.g. Ctrl+\), set SPLIT_KEY_NEEDS_CTRL = True.
#
# SELECTION TOOL KEY  (SELECTION_KEY_VK)
#   Pressed before each split to ensure the Selection (arrow) tool is active.
#   The split shortcut does nothing if the Blade tool is selected instead.
#   Default is 0x41 (A) -- Resolve's built-in Selection tool shortcut.
#
# AUDIO TRACKS  (SPLIT_AUDIO)
#   Set to True to also split audio clips at their markers.
#   Audio tracks are locked/unlocked independently of video tracks.
#
# MARKER FILTER  (MARKER_COLOR_FILTER)
#   Leave as [] to split at ALL marker colours.
#   Set to a list of colour names to only split on specific colours, e.g.:
#     ["Blue", "Red"]
#   Valid names: Blue, Cyan, Green, Yellow, Red, Pink, Purple, Fuchsia,
#                Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream
#
# TIMING  (DELAY_* values)
#   If splits are missed or Resolve falls behind, increase these values.
#   On fast machines you can reduce them to speed up the script.
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

# Seconds to wait after locking/unlocking tracks before continuing.
DELAY_AFTER_TRACK_LOCK = 0.05

# =============================================================================
#  END OF CONFIG -- no need to edit anything below this line
# =============================================================================


# --- Windows INPUT structs for SendInput -------------------------------------

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
VK_CONTROL      = 0x11


def _make_key_input(vk, key_up=False):
    flags = KEYEVENTF_KEYUP if key_up else 0
    return INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, dwFlags=flags))
    )


# --- Window finding ----------------------------------------------------------

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
    if not hwnd:
        return
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(DELAY_AFTER_FOCUS)


# --- Keystroke sending -------------------------------------------------------

def send_inputs(*inputs):
    user32 = ctypes.windll.user32
    arr    = (INPUT * len(inputs))(*inputs)
    n_sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n_sent != len(inputs):
        print("  ! SendInput: only %d/%d events sent." % (n_sent, len(inputs)))


def activate_selection_tool():
    send_inputs(
        _make_key_input(SELECTION_KEY_VK),
        _make_key_input(SELECTION_KEY_VK, key_up=True),
    )
    time.sleep(0.05)


def send_split_shortcut():
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


# --- Resolve helpers ---------------------------------------------------------

def get_resolve():
    try:
        import fusionscript as bmd
        r = bmd.scriptapp("Resolve")
        if r:
            return r
    except ImportError:
        pass
    try:
        import DaVinciResolveScript as dvr
        return dvr.scriptapp("Resolve")
    except ImportError:
        pass
    print("ERROR: Could not import a Resolve scripting module.")
    sys.exit(1)


def frames_to_timecode(frame, fps, drop_frame=False):
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

def get_track_lock_states(timeline, track_type, count):
    """
    Return a dict of {track_index: is_locked} for all tracks of track_type.
    Uses GetTrackLock if available; assumes unlocked if the method is missing.
    """
    states = {}
    for i in range(1, count + 1):
        try:
            locked = timeline.GetTrackLock(track_type, i)
            states[i] = bool(locked)
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
    """Restore all tracks to their original lock states."""
    for i, was_locked in original_states.items():
        try:
            timeline.SetTrackLock(track_type, i, was_locked)
        except Exception:
            pass
    time.sleep(DELAY_AFTER_TRACK_LOCK)


# --- Selection helpers -------------------------------------------------------

def find_clip_track(timeline, track_type, track_count, target_clip):
    """
    Find which track index a given clip lives on.
    Matches by start frame -- unique per track since clips cannot overlap.
    Returns (track_index, clip_object) or (None, None) if not found.
    """
    target_start = target_clip.GetStart()
    target_end   = target_clip.GetEnd()
    for i in range(1, track_count + 1):
        clips = timeline.GetItemListInTrack(track_type, i)
        if not clips:
            continue
        for clip in clips:
            if clip.GetStart() == target_start and clip.GetEnd() == target_end:
                return i, clip
    return None, None


# --- Core logic --------------------------------------------------------------

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


def get_valid_split_frames(clip, markers):
    """
    Return a reverse-sorted list of (timeline_frame, offset, info) tuples.

    Marker offsets from GetMarkers() are relative to the SOURCE MEDIA start,
    not the clip's trimmed in-point. GetLeftOffset() tells us how many source
    frames were trimmed from the front of the clip. The correct timeline frame
    for a marker is:

        timeline_frame = clip.GetStart() + marker_offset - clip.GetLeftOffset()

    Markers that fall before the clip's in-point or after its out-point
    (i.e. outside its trimmed range) are skipped.
    """
    clip_start   = clip.GetStart()
    clip_end     = clip.GetEnd()

    try:
        left_offset = clip.GetLeftOffset()
    except Exception:
        left_offset = 0   # method not available in this Resolve version

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


def process_track(timeline, track_type, track_index, track_count,
                  fps, drop, resolve_hwnd, only_start_frame=None):
    """
    Process one track. Locks all other tracks of the same type before each
    split so the E keypress only affects this track.
    Returns the number of splits performed.
    """
    clips = timeline.GetItemListInTrack(track_type, track_index)
    if not clips:
        return 0

    # Snapshot lock states so we can restore them afterwards
    original_lock_states = get_track_lock_states(timeline, track_type, track_count)

    total_splits = 0

    for clip in clips:
        # If we have a specific target clip, skip everything else
        if only_start_frame is not None and clip.GetStart() != only_start_frame:
            continue

        clip_name = clip.GetName()
        markers   = clip.GetMarkers()

        if not markers:
            continue

        # Apply colour filter if configured
        if MARKER_COLOR_FILTER:
            markers = {o: m for o, m in markers.items()
                       if m.get("color", "") in MARKER_COLOR_FILTER}
        if not markers:
            continue

        split_frames = get_valid_split_frames(clip, markers)

        if not split_frames:
            # All markers are out of range -- this clip was already split before
            continue

        clip_start   = clip.GetStart()
        skipped_zero = sum(1 for o in markers if o == 0)

        print("\n  Clip : '%s'  (track %s%d, start frame %d)"
              % (clip_name, track_type[0].upper(), track_index, clip_start))
        print("  Splits: %d queued%s"
              % (len(split_frames),
                 ("  |  %d offset-0 marker(s) skipped" % skipped_zero) if skipped_zero else ""))

        for tf, offset, marker_info in split_frames:
            color = marker_info.get("color", "?")
            name  = marker_info.get("name",  "")
            print("    -> frame %d  (clip offset %d)  [%s | '%s']"
                  % (tf, offset, color, name))

            # Lock all other tracks so the split keystroke only hits this one
            lock_all_tracks_except(timeline, track_type, track_count, track_index)

            if split_at_frame(timeline, tf, fps, drop, resolve_hwnd):
                total_splits += 1

    # Restore original lock states when done with this track
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

    grand_total = 0

    video_count = timeline.GetTrackCount("video")

    # GetCurrentVideoItem() returns the clip the playhead is parked on,
    # which is the clip the user clicked/selected in the Edit page.
    selected = timeline.GetCurrentVideoItem()

    if selected:
        # Find which track it lives on so we can lock all others
        track_idx, matched_clip = find_clip_track(timeline, "video", video_count, selected)
        if track_idx is None:
            print("  ! Selected clip not found on any video track -- aborting.")
            return
        print("  Selected clip : '%s' (track V%d, start frame %d)"
              % (selected.GetName(), track_idx, selected.GetStart()))
        print("\n[Processing track V%d only]" % track_idx)
        grand_total += process_track(
            timeline, "video", track_idx, video_count, fps, drop, resolve_hwnd,
            only_start_frame=selected.GetStart())
    else:
        # Nothing selected -- process all tracks (fallback behaviour)
        print("  No clip selected -- processing ALL video tracks.")
        print("\n[Video tracks: %d]" % video_count)
        for i in range(1, video_count + 1):
            print("\n Track V%d" % i)
            grand_total += process_track(
                timeline, "video", i, video_count, fps, drop, resolve_hwnd)

    if SPLIT_AUDIO:
        audio_count = timeline.GetTrackCount("audio")
        print("\n[Audio tracks: %d]" % audio_count)
        for i in range(1, audio_count + 1):
            print("\n Track A%d" % i)
            grand_total += process_track(
                timeline, "audio", i, audio_count, fps, drop, resolve_hwnd)

    print("\n" + "-"*60)
    print("  Done.  Total splits performed: %d" % grand_total)
    print("-"*60 + "\n")


if __name__ == "__main__":
    main()
