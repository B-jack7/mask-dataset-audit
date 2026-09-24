# Mask Dataset Audit

[![Tests](https://github.com/B-jack7/mask-dataset-audit/actions/workflows/tests.yml/badge.svg)](https://github.com/B-jack7/mask-dataset-audit/actions/workflows/tests.yml)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/B-jack7/mask-dataset-audit/blob/main/notebooks/quickstart.ipynb)

**Catch broken pairs, unexpected labels, and exact train/test image duplicates before training a segmentation model.**

[中文说明](README.zh-CN.md) · [Synthetic example report](docs/example-report.html) · [Report a bug](https://github.com/B-jack7/mask-dataset-audit/issues/new?template=bug_report.yml)

A focused, read-only CLI for datasets containing images and PNG class-index masks. Produces JSON for automation and a self-contained HTML report you can open offline. No GPU, model download, telemetry, or dataset upload.

## Try a dataset with four planted errors

Requires Python 3.10+, NumPy and Pillow. The installation below installs dependencies.

```bash
git clone https://github.com/B-jack7/mask-dataset-audit.git
cd mask-dataset-audit
python -m pip install .
python examples/make_demo.py demo-data
mask-dataset-audit demo-data --labels 0,1 --out demo-report
```

Open `demo-report/report.html` in a browser. **Exit code 1 is expected** for this deliberately faulty dataset: it contains one unknown label, a mask-size mismatch, a missing mask, and an exact cross-split image duplicate. The generated files contain no real patient data. Use fresh directory names when repeating the demo.

## Dataset layout

```text
dataset/
  train/
    images/subject_a/slice_001.png
    masks/subject_a/slice_001.png
  val/
    images/...
    masks/...
  test/
    images/...
    masks/...
```

Pairs are matched by **relative path without extension** within each split. Images: PNG/JPG/JPEG. Masks: single-frame PNG integer class IDs (8-bit, 16-bit, palette indices or binary). RGB color masks are reported as unsupported rather than silently converted. Other file extensions are ignored. JPEG pixels are checked after decoding, not by compressed bytes. EXIF orientation is not applied.

```bash
mask-dataset-audit ./dataset --labels 0,1,2,3 --ignore 255 --out ./audit-report
# A dataset with only train and val:
mask-dataset-audit ./dataset --labels 0,1 --splits train,val --out ./audit-report-2
```

Use `--background` if background is not class 0. `--labels` is explicit: the tool never guesses the meaning of pixel values. `--ignore` values are counted separately. The output directory must be new and outside the dataset; existing reports are not overwritten.

## Checks

| Check | Severity |
|---|---|
| Missing or empty required directory | Error |
| Missing image/mask or ambiguous same-stem files | Error |
| Unreadable / unsupported image or mask | Error |
| Image and mask dimensions differ | Error |
| Label IDs outside `--labels` and `--ignore` | Error |
| Identical decoded images across splits | Error |
| Identical decoded images within one split | Warning |
| Mask contains no configured foreground | Warning: may be intentional |

### CLI exit codes

- **0**: no errors (warnings may still exist).
- **1**: audit completed and found dataset errors; reports were written.
- **2**: invalid arguments/configuration or an execution failure.

`python -m mask_dataset_audit` is equivalent to the installed command. This makes a dataset check usable as a local pre-training step or CI gate.

### Python API

```python
from mask_dataset_audit import audit

report = audit("dataset", labels=[0, 1, 2], ignore=[255], splits=["train", "val"])
print(report["summary"])
for issue in report["issues"]:
    print(issue["code"], issue["path"], issue["message"])
```

## What this cannot prove

- **Exact pixel duplicates are only one leakage signal.** Resized, cropped, slightly changed images and different slices from the same patient are not detected. Patient-level separation needs reliable patient IDs and a separate check.
- Hashes include decoded image mode and size. Equivalent pictures encoded in different modes may not match; palette images are normalized to RGBA for their visible colors.
- No Dice/IoU, model performance, annotation accuracy, clinical validity, or dataset authenticity assessment is made.
- Class totals include every readable mask, including unpaired or size-mismatched masks. Unknown/ignored pixels are excluded from the valid-class chart, and findings must be resolved before treating it as a clean training summary.
- Processing is sequential, but each image/mask must fit in memory. This release targets small-to-medium folder datasets, not whole-slide imagery, NIfTI/DICOM volumes, or distributed data lakes.
- Reports include relative filenames and error details. Review those before sharing. The tool does not anonymize data.

## Scope and related tools

For broader dataset exploration, review [fastdup](https://github.com/visual-layer/fastdup) or [CVFlow](https://github.com/RizwanMunawar/cvflow). This project deliberately focuses on a small, explicit image/index-mask folder contract and offline checks. It is not a novel segmentation algorithm.

## Development and roadmap

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

CI runs on Windows and Ubuntu with Python 3.10 and 3.12. The initial implementation was developed with AI assistance, with synthetic regression fixtures and executable tests. No production adoption or external audit is claimed.

- [ ] Patient-ID manifest checks with explicit split policies.
- [ ] Optional filename suffix mapping, without moving source files.
- [ ] More user-contributed fixtures for unusual PNG encodings.

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.
