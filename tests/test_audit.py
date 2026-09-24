import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from PIL import Image, PngImagePlugin

from mask_dataset_audit import audit
from mask_dataset_audit.report import render_html
from examples.make_demo import make_demo


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "data"
        for name in ("images", "masks"):
            (self.root / "train" / name).mkdir(parents=True)

    def pair(self, key="a", value=1):
        Image.fromarray(np.arange(64, dtype=np.uint8).reshape(8, 8)).save(self.root / "train/images" / f"{key}.png")
        Image.fromarray(np.full((8, 8), value, dtype=np.uint8)).save(self.root / "train/masks" / f"{key}.png")

    def run_audit(self, **kwargs):
        return audit(self.root, labels=[0, 1], splits=["train"], **kwargs)

    def test_clean_dataset_and_no_mutation(self):
        self.pair()
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*.png")}
        result = self.run_audit()
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["class_pixels"], {"0": 0, "1": 64})
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*.png")})

    def test_unknown_and_ignore_are_distinct(self):
        self.pair(value=255)
        self.assertIn("unknown_labels", [i["code"] for i in self.run_audit()["issues"]])
        result = self.run_audit(ignore=[255])
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["ignored_pixels"], {"255": 64})

    def test_palette_indices_preserved(self):
        self.pair()
        mask = Image.fromarray(np.ones((8, 8), dtype=np.uint8)).convert("P")
        mask.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
        mask.save(self.root / "train/masks/a.png")
        self.assertEqual(self.run_audit()["class_pixels"]["1"], 64)

    def test_rgb_masks_rejected(self):
        self.pair()
        Image.new("RGB", (8, 8), "red").save(self.root / "train/masks/a.png")
        self.assertIn("unreadable_mask", [i["code"] for i in self.run_audit()["issues"]])

    def test_16bit_label_ids_preserved(self):
        self.pair()
        Image.fromarray(np.full((8, 8), 1024, dtype=np.uint16)).save(self.root / "train/masks/a.png")
        result = audit(self.root, labels=[0, 1024], splits=["train"])
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["class_pixels"]["1024"], 64)

    def test_corrupt_image_reported(self):
        self.pair()
        (self.root / "train/images/a.png").write_bytes(b"broken")
        self.assertIn("unreadable_image", [i["code"] for i in self.run_audit()["issues"]])

    def test_duplicate_ignores_png_metadata(self):
        self.pair()
        self.pair("b")
        info = PngImagePlugin.PngInfo()
        info.add_text("note", "different compression and metadata")
        with Image.open(self.root / "train/images/a.png") as image:
            image.save(self.root / "train/images/b.png", pnginfo=info, compress_level=0)
        result = self.run_audit()
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertFalse(result["duplicates"][0]["cross_split"])

    def test_missing_and_ambiguous_pairs(self):
        self.pair()
        Image.new("L", (8, 8)).save(self.root / "train/images/a.jpg")
        self.assertIn("ambiguous_pair", [i["code"] for i in self.run_audit()["issues"]])
        (self.root / "train/images/a.jpg").unlink()
        (self.root / "train/masks/a.png").unlink()
        self.assertIn("missing_mask", [i["code"] for i in self.run_audit()["issues"]])

    def test_demo_finds_all_four_errors(self):
        root = make_demo(Path(self.tmp.name) / "demo")
        result = audit(root, labels=[0, 1])
        self.assertEqual({i["code"] for i in result["issues"]},
                         {"unknown_labels", "size_mismatch", "missing_mask", "cross_split_duplicate"})
        self.assertEqual(result["summary"]["errors"], 4)

    def test_html_escapes_paths(self):
        self.pair()
        result = self.run_audit()
        result["issues"].append(dict(severity="error", code="test", path='<script>alert(1)</script>', message='"&'))
        html = render_html(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_dataset_is_not_success(self):
        self.assertGreater(self.run_audit()["summary"]["errors"], 0)

    def test_cli_exit_codes_and_reports(self):
        self.pair()
        args = [sys.executable, "-m", "mask_dataset_audit", str(self.root), "--labels", "0,1",
                "--splits", "train", "--out", str(Path(self.tmp.name) / "report")]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((Path(self.tmp.name) / "report/report.html").is_file())
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)  # Do not overwrite existing report.
        self.pair(value=8)
        args[-1] = str(Path(self.tmp.name) / "bad-report")
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        data = json.loads((Path(args[-1]) / "report.json").read_text())
        self.assertEqual(data["summary"]["errors"], 1)

    def test_invalid_configuration(self):
        for kwargs in ({"labels": [0], "ignore": [0]}, {"labels": [1]}, {"labels": [0], "splits": [".."]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                audit(self.root, **kwargs)


if __name__ == "__main__":
    unittest.main()
