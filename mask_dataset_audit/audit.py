"""Dataset checks. No label remapping or source-file modification."""

from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import warnings

import numpy as np
from PIL import Image


def audit(root, *, labels, ignore=(), splits=("train", "val", "test"), background=0):
    """Inspect root/<split>/{images,masks}/<relative-stem> files.

    Masks must be single-frame PNGs containing integer class indices. Palette
    indices are preserved. Duplicate images are matched by decoded pixels,
    shape and mode, NOT by filename or compressed file bytes.
    """
    root = Path(root)
    labels, ignore = set(labels), set(ignore)
    splits = tuple(splits)
    if not labels or labels & ignore:
        raise ValueError("labels must be nonempty and disjoint from ignore")
    if any(type(x) is not int or x < 0 or x > 65535 for x in labels | ignore):
        raise ValueError("labels and ignore must be integers between 0 and 65535")
    if background not in labels:
        raise ValueError("background must be in labels")
    if (not splits or len(set(splits)) != len(splits)
            or any(s in ("", ".", "..") or "/" in s or "\\" in s for s in splits)):
        raise ValueError("splits must be unique directory names")
    if not root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {root}")
    issues, pairs, fingerprints = [], [], defaultdict(list)
    totals, ignored = Counter(), Counter()

    def issue(code, split, path, message, severity="error"):
        issues.append(dict(code=code, severity=severity, split=split,
                           path=str(path), message=message))

    def index(folder, extensions, split):
        files = defaultdict(list)
        if not folder.is_dir():
            issue("missing_directory", split, folder.relative_to(root).as_posix(),
                  "Required directory is missing")
            return files
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                files[path.relative_to(folder).with_suffix("").as_posix()].append(path)
        if not files:
            issue("empty_directory", split, folder.relative_to(root).as_posix(),
                  "No supported files found")
        return files

    for split in splits:
        images = index(root / split / "images", {".png", ".jpg", ".jpeg"}, split)
        masks = index(root / split / "masks", {".png"}, split)
        for key in sorted(images.keys() | masks.keys()):
            image_paths, mask_paths = images.get(key, []), masks.get(key, [])
            relative_key = f"{split}/{key}"
            if len(image_paths) > 1 or len(mask_paths) > 1:
                issue("ambiguous_pair", split, relative_key,
                      "Multiple files share the same relative stem")
                continue
            image_size = None
            if not image_paths:
                issue("missing_image", split, relative_key, "Mask has no matching image")
            else:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", Image.DecompressionBombWarning)
                        with Image.open(image_paths[0]) as image:
                            if getattr(image, "n_frames", 1) != 1:
                                raise ValueError("Multi-frame images are not supported")
                            image.load()
                            if image.mode == "P":
                                image = image.convert("RGBA")
                            image_size = image.size
                            digest = hashlib.sha256()
                            digest.update(f"{image.mode}:{image.size}:".encode())
                            digest.update(image.tobytes())
                            fingerprints[digest.hexdigest()].append({
                                "split": split, "path": image_paths[0].relative_to(root).as_posix()})
                except (OSError, ValueError, Image.DecompressionBombError,
                        Image.DecompressionBombWarning) as error:
                    issue("unreadable_image", split, relative_key, str(error))
            if not mask_paths:
                issue("missing_mask", split, relative_key, "Image has no matching PNG mask")
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(mask_paths[0]) as mask:
                        if mask.format != "PNG" or getattr(mask, "n_frames", 1) != 1:
                            raise ValueError("Masks must be single-frame PNG files")
                        mask.load()
                        values = np.asarray(mask)
                        if values.ndim != 2 or values.dtype.kind not in "bui":
                            raise ValueError("Mask must contain 2D integer indices, not RGB colors")
                        mask_size = mask.size
                if image_size is not None and image_size != mask_size:
                    issue("size_mismatch", split, relative_key,
                          f"Image is {image_size}; mask is {mask_size}")
                ids, counts = np.unique(values, return_counts=True)
                histogram = {int(k): int(v) for k, v in zip(ids, counts)}
                unknown = {k: v for k, v in histogram.items() if k not in labels | ignore}
                if unknown:
                    issue("unknown_labels", split, relative_key,
                          f"Unexpected label pixel counts: {unknown}")
                for k, v in histogram.items():
                    if k in labels:
                        totals[k] += v
                    elif k in ignore:
                        ignored[k] += v
                foreground = sum(v for k, v in histogram.items() if k in labels - {background})
                if not unknown and foreground == 0:
                    issue("no_foreground", split, relative_key,
                          "Mask has no foreground pixels; review if intentional", "warning")
                pairs.append({"split": split, "key": key, "mask_size": list(mask_size),
                              "label_pixels": {str(k): v for k, v in histogram.items()}})
            except (OSError, ValueError, Image.DecompressionBombError,
                    Image.DecompressionBombWarning) as error:
                issue("unreadable_mask", split, relative_key, str(error))

    duplicates = []
    for digest, members in sorted(fingerprints.items()):
        if len(members) < 2:
            continue
        cross_split = len({m["split"] for m in members}) > 1
        duplicates.append({"sha256": digest, "cross_split": cross_split, "files": members})
        issue("cross_split_duplicate" if cross_split else "duplicate_image", "multiple",
              ", ".join(m["path"] for m in members),
              "Identical decoded image pixels detected", "error" if cross_split else "warning")
    return {
        "schema_version": 1,
        "configuration": {"labels": sorted(labels), "ignore": sorted(ignore),
                          "splits": list(splits), "background": background},
        "summary": {"masks_read": len(pairs),
                    "images_read": sum(len(v) for v in fingerprints.values()),
                    "errors": sum(i["severity"] == "error" for i in issues),
                    "warnings": sum(i["severity"] == "warning" for i in issues),
                    "cross_split_duplicate_groups": sum(d["cross_split"] for d in duplicates)},
        "class_pixels": {str(k): totals[k] for k in sorted(labels)},
        "ignored_pixels": {str(k): ignored[k] for k in sorted(ignore)},
        "issues": issues, "duplicates": duplicates, "masks": pairs,
    }
