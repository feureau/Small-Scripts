import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROGRAMMING = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROGRAMMING))
from face_tracking.motion import calculate, validate
from face_tracking.export import fusion_setting, write_outputs
from face_tracking.video import probe


def fixture(points, fps="10", segments=None):
    return {"schema": "maxine-face-track/1", "source": {"path": "unused.mkv", "size": 0, "mtime_ns": 0},
        "video": {"width": 1000, "height": 500, "fps": fps},
        "frames": [{"frame": i, "pts_seconds": i/float(fps), "segment": segments[i] if segments else 0,
                    "valid": p is not None, "confidence": 30 if p else 0,
                    "anchor_x_px": p[0] if p else None, "anchor_y_px": p[1] if p else None}
                   for i, p in enumerate(points)]}


class MotionTests(unittest.TestCase):
    def test_lock_cancels_motion(self):
        data = fixture([(400, 200), (450, 220), (380, 180)])
        before = copy.deepcopy(data)
        rows, _, _ = calculate(data)
        self.assertEqual(data, before)
        for row in rows:
            self.assertAlmostEqual(row["anchor_x_px"] + row["dx_px"], 400)
            self.assertAlmostEqual(row["anchor_y_px"] + row["dy_px"], 200)

    def test_target_y_direction(self):
        rows, _, _ = calculate(fixture([(400, 200)]), target=[0.5, 0.8])
        self.assertAlmostEqual(rows[0]["dx_px"], 100)
        self.assertAlmostEqual(rows[0]["dy_px"], -100)

    def test_follow_preserves_linear_motion_interior(self):
        rows, _, _ = calculate(fixture([(100+i*5, 200) for i in range(9)]), mode="follow", smoothing=.4)
        self.assertAlmostEqual(rows[4]["dx_px"], 0)

    def test_follow_removes_spike(self):
        rows, _, _ = calculate(fixture([(200, 200), (200, 200), (290, 200), (200, 200), (200, 200)]), mode="follow", smoothing=.2)
        self.assertAlmostEqual(rows[2]["dx_px"], -60)

    def test_short_gap_interpolation(self):
        rows, _, _ = calculate(fixture([(100, 200), None, (120, 200)]))
        self.assertEqual(rows[1]["status"], "interpolated")
        self.assertEqual(rows[1]["dx_px"], -10)
        self.assertFalse(rows[1]["valid"])

    def test_long_gap_holds_correction(self):
        rows, warnings, _ = calculate(fixture([(100, 200), (120, 200), None, None, None, (180, 200)]))
        self.assertEqual([rows[i]["dx_px"] for i in (2, 3, 4)], [-20]*3)
        self.assertTrue(warnings)

    def test_leading_missing_uses_identity(self):
        rows, _, _ = calculate(fixture([None, (120, 200), (140, 200)]))
        self.assertEqual(rows[0]["dx_px"], 0)
        self.assertEqual(rows[2]["dx_px"], -20)

    def test_cut_resets_lock(self):
        rows, _, _ = calculate(fixture([(100, 200), (120, 200), (800, 300)], segments=[0, 0, 1]))
        self.assertEqual(rows[2]["dx_px"], 0)

    def test_no_face_rejected(self):
        with self.assertRaisesRegex(ValueError, "No reliable face"):
            calculate(fixture([None, None]))

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            calculate(fixture([(math.nan, 0)]))

    def test_zoom_matches_separate_post_transform(self):
        _, _, zoom = calculate(fixture([(100, 200), (200, 200)]))
        self.assertAlmostEqual(zoom, 1.25)
        self.assertAlmostEqual((500-100)*zoom, 500)

    def test_impossible_zoom(self):
        _, _, zoom = calculate(fixture([(100, 200), (800, 200)]))
        self.assertIsNone(zoom)


class ExportTests(unittest.TestCase):
    def test_fusion_coordinates_and_trim(self):
        rows, _, _ = calculate(fixture([(400, 200), (500, 250)]))
        settings = fusion_setting(rows, 1000, 500, source_start=1, fusion_start=1001)
        self.assertIn('[1001] = { 0.4,', settings)
        self.assertIn('[1001] = { 0.6,', settings)
        self.assertIn('Linear = true', settings)
        self.assertNotIn('[0] =', settings)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / name for name in ("a.json", "a.csv", "a.setting")]
            paths[0].write_text("keep")
            with self.assertRaises(FileExistsError):
                write_outputs(paths, {}, [], "", False)
            self.assertEqual(paths[0].read_text(), "keep")
            self.assertFalse(paths[1].exists())

    def test_cli_from_different_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "test clip.track.json"
            source.write_text(json.dumps(fixture([(400, 200), (450, 200)])))
            cmd = [sys.executable, str(PROGRAMMING / "track.py"), source.name]
            result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(folder)/"test clip.lock.setting").is_file())
            self.assertTrue((Path(folder)/"test clip.track.csv").is_file())
            self.assertTrue((Path(folder)/"test clip.lock.track.json").is_file())
            self.assertNotIn("motion", json.loads(source.read_text()))
            result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Outputs exist", result.stderr)
            result = subprocess.run(cmd + ["--overwrite", "--mode", "follow"], cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(folder)/"test clip.follow.setting").is_file())


class TimingTests(unittest.TestCase):
    def mocked_probe(self, pts):
        stream = {"width": 1000, "height": 500, "time_base": "1/1000", "r_frame_rate": "30000/1001"}
        payload = {"streams": [stream], "packets": [{"pts": p} for p in pts]}
        with patch("face_tracking.video.shutil.which", return_value="ffprobe"), patch("face_tracking.video.subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), "")):
            return probe(Path("unused.mkv"))

    def test_mkv_rounding_and_b_frame_order(self):
        result = self.mocked_probe([1000, 1100, 1033, 1067, 1133])
        self.assertEqual(result["pts"], [1000, 1033, 1067, 1100, 1133])
        self.assertEqual(result["fps"], "30000/1001")

    def test_vfr_rejected(self):
        with self.assertRaisesRegex(ValueError, "Variable frame rate"):
            self.mocked_probe([0, 33, 67, 140])

    def test_duplicate_pts_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.mocked_probe([0, 33, 33])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_real_mkv_packet_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "timing.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=64x64:r=30000/1001:d=0.5", "-c:v", "libx264", "-bf", "2", str(path)], check=True)
            metadata = probe(path)
            self.assertEqual(metadata["fps"], "30000/1001")
            self.assertEqual(len(metadata["pts"]), 15)


if __name__ == "__main__":
    unittest.main()
