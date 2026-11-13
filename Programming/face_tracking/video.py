"""Compressed-packet timing inspection and GPU-resident frame decoding."""
import json
import shutil
import subprocess
from fractions import Fraction


def probe(path):
    executable = shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe is required on PATH (install FFmpeg)")
    command = [executable, "-v", "error", "-select_streams", "v", "-show_streams", "-show_packets",
               "-show_entries", "packet=stream_index,pts:stream=index,width,height,avg_frame_rate,r_frame_rate,time_base,pix_fmt,color_transfer,color_space,color_primaries,sample_aspect_ratio,field_order:stream_tags=rotate:stream_side_data=rotation",
               "-of", "json", str(path)]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError("ffprobe: " + run.stderr.strip())
    info = json.loads(run.stdout)
    if len(info.get("streams", [])) != 1:
        raise ValueError("Version 1 requires exactly one video stream")
    stream = info["streams"][0]
    if stream.get("sample_aspect_ratio", "1:1") not in ("1:1", "0:1", "N/A"):
        raise ValueError("Anamorphic video is not supported; use square-pixel analysis media")
    if stream.get("field_order", "unknown") not in ("progressive", "unknown"):
        raise ValueError("Interlaced video is not supported; deinterlace first")
    rotation = int(stream.get("tags", {}).get("rotate", 0))
    for side in stream.get("side_data_list", []):
        rotation = side.get("rotation", rotation)
    if rotation % 360:
        raise ValueError("Rotation metadata is not supported; bake orientation into analysis media first")
    if stream.get("color_transfer") in ("smpte2084", "arib-std-b67"):
        raise ValueError("HDR analysis is not supported yet; use a tone-mapped SDR proxy with identical dimensions and frames")
    rate = Fraction(stream.get("r_frame_rate", "0/1"))
    if rate <= 0:
        rate = Fraction(stream.get("avg_frame_rate", "0/1"))
    if rate <= 0:
        raise ValueError("Cannot determine video frame rate")
    tick = Fraction(stream["time_base"])
    packets = info.get("packets", [])
    if not packets or any("pts" not in p for p in packets):
        raise ValueError("All video packets must have presentation timestamps")
    pts = sorted(int(p["pts"]) for p in packets)
    if len(set(pts)) != len(pts):
        raise ValueError("Duplicate presentation timestamps are not supported")
    # MKV often quantizes CFR timestamps to milliseconds. Check the entire grid,
    # not just adjacent durations, so missing frames and gradual drift fail.
    tolerance = max(float(tick) * 1.1, 1e-6)
    if any(abs(float((p - pts[0]) * tick - Fraction(i, 1) / rate)) > tolerance for i, p in enumerate(pts)):
        raise ValueError("Variable frame rate or discontinuous timing detected; create a CFR analysis clip first")
    return {
        "width": stream["width"], "height": stream["height"], "fps": str(rate),
        "time_base": str(tick), "pts": pts, "pts_seconds": [float(p*tick) for p in pts],
        "pixel_format": stream.get("pix_fmt"), "color_transfer": stream.get("color_transfer"),
        "rotation": 0, "sample_aspect_ratio": "1:1",
    }


class GPUVideo:
    def __init__(self, path, gpu=0, allow_cpu=False):
        try:
            import cupy as cp
            import PyNvVideoCodec as nvc
        except ImportError as error:
            raise RuntimeError("GPU dependencies missing. See face_tracking/README.md and run track.py --doctor") from error
        self.cp, self.nvc = cp, nvc
        self.cpu_container = None
        self.backend = "NVDEC"
        cp.cuda.Device(gpu).use()
        self.stream = cp.cuda.Stream(non_blocking=True)
        try:
            self.decoder = nvc.SimpleDecoder(str(path), gpu_id=gpu, cuda_context=0,
                cuda_stream=self.stream.ptr, use_device_memory=True,
                output_color_type=nvc.OutputColorType.RGB)
        except Exception as error:
            if not allow_cpu:
                raise RuntimeError(f"NVDEC could not open the input: {error}. No CPU fallback was used.") from error
            import av
            import sys
            print(f"NVDEC initialization failed; explicitly permitted CPU decode: {error}", file=sys.stderr)
            self.decoder = None
            self.cpu_container = av.open(str(path))
            self.backend = "CPU (explicit fallback)"

    def frames(self):
        if self.cpu_container is not None:
            for frame in self.cpu_container.decode(video=0):
                with self.stream:
                    rgb = self.cp.asarray(frame.to_ndarray(format="rgb24"))
                    yield rgb
                self.stream.synchronize()
            return
        while True:
            batch = self.decoder.get_batch_frames(4)
            if not batch:
                return
            for frame in batch:
                # Retain frame and batch until the consumer finishes. The decoder
                # and conversion share a stream, so copies cannot race decode.
                with self.stream:
                    if hasattr(frame, "__dlpack__"):
                        rgb = self.cp.from_dlpack(frame)
                    elif hasattr(frame, "dlpack"):
                        rgb = self.cp.from_dlpack(frame.dlpack(self.stream.ptr))
                    else:
                        rgb = self.cp.asarray(frame.cuda()[0])
                    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != self.cp.uint8:
                        raise RuntimeError(f"Unexpected NVDEC RGB surface: {rgb.shape}, {rgb.dtype}")
                    yield rgb
                self.stream.synchronize()

    def close(self):
        self.stream.synchronize()
        self.decoder = None
        if self.cpu_container is not None:
            self.cpu_container.close()
            self.cpu_container = None
