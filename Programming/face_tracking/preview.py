"""GPU warp/overlay + NVENC. Only the compressed bitstream returns to the CPU."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from .video import GPUVideo

WARP = r'''
extern "C" __global__ void warp(const unsigned char* src, unsigned char* dst,
 int w, int h, long long stride, float dx, float dy, float zoom, float ax, float ay, int good) {
 int i = blockDim.x * blockIdx.x + threadIdx.x;
 if (i >= w*h) return;
 int x = i%w, y = i/w;
 float sx = (x-(w-1)*0.5f)/zoom + (w-1)*0.5f-dx;
 float sy = (y-(h-1)*0.5f)/zoom + (h-1)*0.5f-dy;
 int ix = (int)floorf(sx), iy = (int)floorf(sy);
 float fx = sx-ix, fy = sy-iy;
 for (int c=0;c<3;c++) {
   float v=0;
   for(int ky=0;ky<2;ky++) for(int kx=0;kx<2;kx++) {
     int xx=ix+kx, yy=iy+ky;
     if(xx>=0 && xx<w && yy>=0 && yy<h)
       v += src[yy*stride+xx*3+c]*(kx?fx:1-fx)*(ky?fy:1-fy);
   }
   dst[i*4+c]=(unsigned char)fminf(255,fmaxf(0,v));
 }
 float tx=(ax+dx-(w-1)*0.5f)*zoom+(w-1)*0.5f;
 float ty=(ay+dy-(h-1)*0.5f)*zoom+(h-1)*0.5f;
 bool cross = ax>=0 && ((fabsf(x-tx)<1.5f && fabsf(y-ty)<12) || (fabsf(y-ty)<1.5f && fabsf(x-tx)<12));
 bool indicator = x<16 && y<16;
 if(cross || indicator) {dst[i*4]=good?0:255;dst[i*4+1]=good?255:0;dst[i*4+2]=0;}
 dst[i*4+3]=255;
}
'''


def render(source, output, rows, video, gpu, zoom=1, overwrite=False, allow_cpu=False):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to mux the NVENC preview")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Preview exists: {output}")
    decoder = GPUVideo(source, gpu, allow_cpu)
    cp, nvc, stream = decoder.cp, decoder.nvc, decoder.stream
    import numpy as np
    w, h = video["width"], video["height"]
    if w % 2 or h % 2:
        decoder.close()
        raise ValueError("NVENC preview requires even dimensions")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="face-preview-", dir=output.parent) as scratch:
            raw = Path(scratch) / "preview.h264"
            muxed = Path(scratch) / "preview.mp4"
            with stream:
                kernel = cp.RawKernel(WARP, "warp")
                rgba = cp.empty((h, w, 4), dtype=cp.uint8)
                encoder = nvc.CreateEncoder(w, h, "ABGR", False, gpu_id=gpu,
                    cuda_stream=stream.ptr, codec="h264", preset="P4", fps=video["fps"], bitrate="8M")
                count = 0
                with raw.open("wb") as sink:
                    for rgb in decoder.frames():
                        if count >= len(rows):
                            break
                        row = rows[count]
                        if rgb.shape != (h, w, 3):
                            raise ValueError("Preview source dimensions do not match tracking")
                        args = (rgb, rgba, np.int32(w), np.int32(h), np.int64(rgb.strides[0]),
                            np.float32(row["dx_px"]), np.float32(row["dy_px"]), np.float32(zoom),
                            np.float32(row["anchor_x_px"] if row["valid"] else -1),
                            np.float32(row["anchor_y_px"] if row["valid"] else -1), np.int32(row["valid"]))
                        kernel(((w*h+255)//256,), (256,), args)
                        stream.synchronize()
                        sink.write(bytearray(encoder.Encode(rgba)))
                        count += 1
                    sink.write(bytearray(encoder.EndEncode()))
                del encoder
            if count != len(rows):
                raise ValueError("Preview source has fewer frames than tracking")
            command = [ffmpeg, "-v", "error", "-r", video["fps"], "-f", "h264", "-i", str(raw),
                       "-c:v", "copy", "-an", "-movflags", "+faststart", str(muxed)]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError("Preview mux failed: " + result.stderr.strip())
            if overwrite:
                os.replace(muxed, output)
            else:
                os.link(muxed, output)
    finally:
        decoder.close()
