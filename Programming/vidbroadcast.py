#!/usr/bin/env python3
"""
vidbroadcast.py
Converts any FFmpeg-readable video to NVIDIA Broadcast File Processor format:
  * Video: H.264 (8-bit, All-I high bitrate, BT.709 SDR) via NVENC (or stream copy if already compatible)
  * Audio: AAC stereo 48 kHz (track 5 by default, stream copy if already compatible)
  * Container: MP4 (standard sequential layout with faststart)

Processing pipeline:
  * Pure rewrap: stream copy video & audio if already compatible (no re-encoding)
  * SDR encode: NVDEC decode -> scale_cuda -> NVENC All-I (high bitrate)
  * HDR encode: Vulkan decode -> libplacebo Vulkan tonemap (BT.2390 to BT.709) -> NVENC All-I (high bitrate)

Usage:
  vidbroadcast.py video.mp4
  vidbroadcast.py *.mkv
  vidbroadcast.py                        # scan cwd for supported files
  vidbroadcast.py --audio-track 2 --output-dir out a.mp4 b.mkv
  vidbroadcast.py --qp 16                # custom All-I QP (default: 18)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTS = {
    '.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.ts', '.m2ts',
    '.mts', '.m2t', '.wmv', '.flv', '.mpg', '.mpeg', '.3gp', '.ogv', '.vob',
}
HDR_TRC = {'smpte2084', 'arib-std-b67', 'smpte428', 'bt2020-10', 'bt2020-12'}


def log(msg, level='info'):
    prefix = {'info': '[ ]', 'ok': '[+]', 'warn': '[!]', 'err': '[x]'}.get(level, '[ ]')
    print(f"{prefix} {msg}", flush=True)


def find_bin(name):
    """Prefer binaries next to this script, then PATH."""
    here = Path(__file__).resolve().parent
    for cand in (here / f"{name}.exe", here / name):
        if cand.is_file():
            return str(cand)
    return shutil.which(name)


def check_ffmpeg(ffmpeg):
    """Verify NVENC encoder and (optionally) libplacebo filter are present."""
    enc = subprocess.run([ffmpeg, '-hide_banner', '-encoders'],
                         capture_output=True, text=True).stdout
    if 'h264_nvenc' not in enc:
        log("FFmpeg build lacks h264_nvenc (NVENC unavailable) — aborting", 'err')
        return False
    filt = subprocess.run([ffmpeg, '-hide_banner', '-filters'],
                          capture_output=True, text=True).stdout
    if 'libplacebo' not in filt:
        log("FFmpeg lacks libplacebo — HDR inputs will fail. "
            "Use a BtbN build with --enable-libplacebo", 'warn')
    return True


def probe(ffprobe, path):
    r = subprocess.run(
        [ffprobe, '-v', 'error', '-print_format', 'json',
         '-show_streams', '-show_format', str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "ffprobe failed")
    return json.loads(r.stdout)


def analyze(data, audio_track_1based=1):
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise RuntimeError("no video stream")
    audios = [s for s in data['streams'] if s['codec_type'] == 'audio']

    codec = (video.get('codec_name') or '').lower()
    pix = (video.get('pix_fmt') or '').lower()
    trc = (video.get('color_transfer') or '').lower()
    prim = (video.get('color_primaries') or '').lower()

    is_10bit = any(x in pix for x in ('10', '12', '16'))
    is_hdr = trc in HDR_TRC or prim == 'bt2020'

    # Compatible video for Broadcast: H.264, 8-bit, 4:2:0, SDR
    can_copy_video = (
        codec == 'h264'
        and not is_hdr
        and not is_10bit
        and pix in ('yuv420p', 'nv12', 'yuvj420p')
    )

    audio_count = len(audios)
    can_copy_audio = False
    want_track = 0

    if audio_count > 0:
        want_track = audio_track_1based - 1
        if want_track >= audio_count or want_track < 0:
            want_track = 0
        sel_audio = audios[want_track]
        acodec = (sel_audio.get('codec_name') or '').lower()
        channels = int(sel_audio.get('channels') or 2)
        srate = int(sel_audio.get('sample_rate') or 48000)
        can_copy_audio = (
            acodec == 'aac'
            and channels in (1, 2)
            and srate in (44100, 48000)
        )

    return {
        'video_codec': codec,
        'pix_fmt': pix,
        'audio_count': audio_count,
        'selected_audio_track': want_track,
        'is_10bit': is_10bit,
        'is_hdr': is_hdr,
        'can_copy_video': can_copy_video,
        'can_copy_audio': can_copy_audio,
    }


def build_vf(info):
    """Return the video filter chain."""
    if info['is_hdr']:
        # Vulkan decode -> libplacebo GPU tonemap/downconvert -> NV12 -> NVENC
        return (
            "libplacebo=tonemapping=bt.2390"
            ":colorspace=bt709:color_primaries=bt709:color_trc=bt709"
            ":format=nv12,hwdownload,format=nv12"
        )
    # SDR (8- or 10-bit): downconvert on GPU
    return "scale_cuda=format=yuv420p"


def build_cmd(ffmpeg, inp, out, audio_track_1based, info, qp=18, bitrate=None):
    cmd = [
        ffmpeg, '-hide_banner', '-loglevel', 'warning', '-stats',
    ]

    # Hardware acceleration is only needed if decoding video to transcode
    if not info['can_copy_video']:
        if info['is_hdr']:
            cmd += [
                '-init_hw_device', 'vulkan=vk',
                '-hwaccel', 'vulkan', '-hwaccel_output_format', 'vulkan',
            ]
        else:
            cmd += [
                '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda',
            ]

    cmd += [
        '-i', str(inp),
        '-map', '0:v:0',
    ]

    # --- audio track selection ---
    has_audio = info['audio_count'] > 0
    if has_audio:
        want = info['selected_audio_track']
        if audio_track_1based - 1 != want and audio_track_1based > 1:
            log(f"audio track {audio_track_1based} not present "
                f"({info['audio_count']} available); using track 1", 'warn')
        cmd += ['-map', f'0:a:{want}?']

    # --- video codec ---
    if info['can_copy_video']:
        cmd += ['-c:v', 'copy']
    else:
        cmd += [
            '-vf', build_vf(info),
            '-c:v', 'h264_nvenc',
            '-preset', 'p5',
            '-tune', 'hq',
            '-profile:v', 'high',
            '-g', '0',
        ]
        if bitrate:
            cmd += [
                '-rc', 'vbr',
                '-b:v', str(bitrate),
                '-maxrate', str(bitrate),
                '-bufsize', str(bitrate),
            ]
        else:
            cmd += [
                '-rc', 'constqp',
                '-qp', str(qp),
            ]

    # --- audio codec ---
    if has_audio:
        if info['can_copy_audio']:
            cmd += ['-c:a', 'copy']
        else:
            cmd += ['-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', '48000']
    else:
        cmd += ['-an']

    cmd += ['-movflags', '+faststart', '-y', str(out)]
    return cmd


def process(ffmpeg, ffprobe, inp, audio_track, out_dir, overwrite, qp=18, bitrate=None):
    inp = Path(inp).resolve()
    if not inp.is_file():
        log(f"not a file: {inp}", 'err'); return False
    if inp.suffix.lower() not in SUPPORTED_EXTS:
        log(f"unsupported extension: {inp.name}", 'warn'); return False

    out = ((Path(out_dir) if out_dir else inp.parent)
           / f"{inp.stem}_broadcast.mp4")
    if out.exists() and not overwrite:
        log(f"exists, skipping: {out.name} (use --overwrite)", 'warn'); return False
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        info = analyze(probe(ffprobe, inp), audio_track)
    except Exception as e:
        log(f"probe failed: {e}", 'err'); return False

    tag = 'HDR' if info['is_hdr'] else ('10-bit' if info['is_10bit'] else 'SDR')
    if info['can_copy_video']:
        v_desc = "copy video"
    else:
        v_desc = f"encode All-I {tag} ({bitrate})" if bitrate else f"encode All-I {tag} (QP {qp})"

    if info['audio_count'] > 0:
        t_num = info['selected_audio_track'] + 1
        a_desc = f"copy audio t{t_num}" if info['can_copy_audio'] else f"encode audio t{t_num}"
    else:
        a_desc = "no audio"

    is_pure_rewrap = info['can_copy_video'] and (info['audio_count'] == 0 or info['can_copy_audio'])
    action = "rewrap" if is_pure_rewrap else "convert"
    log(f"{action}: {inp.name}  [{v_desc}, {a_desc}]")

    cmd = build_cmd(ffmpeg, inp, out, audio_track, info, qp, bitrate)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        log(f"ffmpeg exit {r.returncode}", 'err')
        out.unlink(missing_ok=True)
        return False

    log(f"done: {out.name}", 'ok')
    return True


def main():
    p = argparse.ArgumentParser(
        prog='vidbroadcast.py',
        description='Convert videos to NVIDIA Broadcast File Processor format '
                    '(H.264 8-bit SDR + AAC stereo MP4). All video processing on GPU.',
    )
    p.add_argument('files', nargs='*',
                   help='Input video file(s). If omitted, scans the current directory.')
    p.add_argument('--audio-track', type=int, default=5, metavar='N',
                   help='1-indexed audio track to keep (default: 5).')
    p.add_argument('--qp', type=int, default=18, metavar='N',
                   help='Constant QP for All-I re-encoding (default: 18, high bitrate/quality).')
    p.add_argument('--bitrate', default=None, metavar='BITRATE',
                   help='Target bitrate for All-I re-encoding (e.g. 100M). If omitted, uses --qp.')
    p.add_argument('--output-dir', default=None, metavar='DIR',
                   help='Write *_broadcast.mp4 here (default: next to source).')
    p.add_argument('--overwrite', action='store_true',
                   help='Overwrite existing *_broadcast.mp4 files.')
    p.add_argument('--ffmpeg', default=None,
                   help='Path to the ffmpeg executable (auto-detected by default).')
    args = p.parse_args()

    ffmpeg = args.ffmpeg or find_bin('ffmpeg')
    ffprobe = find_bin('ffprobe')
    if not ffmpeg or not ffprobe:
        log("ffmpeg/ffprobe not found — place them next to this script or add to PATH", 'err')
        return 2
    if not check_ffmpeg(ffmpeg):
        return 2

    # Build input list
    if args.files:
        files = args.files
    else:
        cwd = Path.cwd()
        files = sorted(
            str(f) for f in cwd.iterdir()
            if f.is_file()
            and f.suffix.lower() in SUPPORTED_EXTS
            and not f.stem.endswith('_broadcast')
        )
        if not files:
            log(f"no supported video files in {cwd}", 'err'); return 1
        log(f"scanning {cwd} -> {len(files)} file(s)")

    ok = fail = 0
    for f in files:
        (ok := ok + 1) if process(ffmpeg, ffprobe, f, args.audio_track,
                                  args.output_dir, args.overwrite,
                                  args.qp, args.bitrate) else (fail := fail + 1)

    print()
    log(f"complete: {ok} ok, {fail} skipped/failed",
        'ok' if fail == 0 else 'warn')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())