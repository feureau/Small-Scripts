"""ctypes binding to our header-checked native bridge, not to guessed SDK structs."""
import ctypes as ct
import os
from pathlib import Path


def sdk_directory(explicit=None):
    candidate = explicit or os.environ.get("NVAR_SDK_PATH") or os.environ.get("MAXINE_AR_SDK")
    root = Path(candidate) if candidate else Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "NVIDIA Corporation/NVIDIA AR SDK"
    return root.resolve()


BRIDGE = Path(__file__).resolve().parent / "bin/face_track_bridge.dll"


class Maxine:
    def __init__(self, sdk, models, stream, quality=True):
        self.handle = None
        self.dll_path = None
        if os.name != "nt":
            raise RuntimeError("This Maxine bridge requires Windows x64")
        if not BRIDGE.is_file():
            raise RuntimeError(f"Build the native bridge first: {BRIDGE.parent.parent / 'native/build.ps1'}")
        if not (sdk / "nvARPose.dll").is_file():
            raise RuntimeError(f"Maxine AR runtime not found in {sdk}; use --sdk-dir or NVAR_SDK_PATH")
        if not models.is_dir():
            raise RuntimeError(f"Maxine model directory not found: {models}")
        self.dll_path = os.add_dll_directory(str(sdk))
        try:
            self.lib = ct.CDLL(str(BRIDGE))
            self.lib.ft_abi_version.argtypes = []
            self.lib.ft_abi_version.restype = ct.c_uint
            if self.lib.ft_abi_version() != 1:
                raise RuntimeError("Native bridge ABI mismatch; rebuild it")
            self.lib.ft_error.argtypes = []
            self.lib.ft_error.restype = ct.c_char_p
            self.lib.ft_create.argtypes = [ct.c_wchar_p, ct.c_char_p, ct.c_size_t, ct.c_int]
            self.lib.ft_create.restype = ct.c_void_p
            self.lib.ft_destroy.argtypes = [ct.c_void_p]
            self.lib.ft_destroy.restype = None
            fp = ct.POINTER(ct.c_float)
            self.lib.ft_run.argtypes = [ct.c_void_p, ct.c_size_t, ct.c_uint, ct.c_uint, ct.c_uint, fp, fp, fp]
            self.lib.ft_run.restype = ct.c_int
            self.xy, self.confidence, self.box = (ct.c_float * 136)(), (ct.c_float * 68)(), (ct.c_float * 4)()
            self.handle = self.lib.ft_create(str(sdk), str(models).encode("utf-8"), stream.ptr, int(quality))
            if not self.handle:
                raise RuntimeError(self.error())
        except BaseException:
            self.close()
            raise

    def error(self):
        return self.lib.ft_error().decode("utf-8", errors="replace")

    def run(self, bgr):
        h, w, channels = bgr.shape
        if channels != 3 or bgr.dtype.name != "uint8" or not bgr.flags.c_contiguous:
            raise ValueError("Maxine requires contiguous GPU BGR uint8")
        found = self.lib.ft_run(self.handle, bgr.data.ptr, w, h, bgr.strides[0], self.xy, self.confidence, self.box)
        if found < 0:
            raise RuntimeError(self.error())
        return bool(found), [[self.xy[i*2], self.xy[i*2+1]] for i in range(68)], list(self.confidence), list(self.box)

    def close(self):
        if self.handle:
            self.lib.ft_destroy(self.handle)
            self.handle = None
        if self.dll_path:
            self.dll_path.close()
            self.dll_path = None
