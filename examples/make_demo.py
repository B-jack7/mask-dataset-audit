"""Generate synthetic data with deliberately planted mistakes; no real images."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def make_demo(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(7)
    first = None
    for split in ("train", "val", "test"):
        for kind in ("images", "masks"):
            (root / split / kind).mkdir(parents=True)
        for index in range(3):
            image = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
            mask = np.zeros((64, 64), dtype=np.uint8)
            mask[12:45, 16:48] = 1
            if split == "train" and index == 0:
                first = image.copy()
            if split == "test" and index == 0:
                image = first.copy()  # Exact train/test duplicate.
            if split == "val" and index == 0:
                mask[0:4, 0:4] = 9  # Unexpected class ID.
            if split == "val" and index == 1:
                mask = mask[:32]  # Wrong mask dimensions.
            Image.fromarray(image).save(root / split / "images" / f"sample_{index}.png")
            if split != "test" or index != 2:  # Missing mask.
                Image.fromarray(mask).save(root / split / "masks" / f"sample_{index}.png")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    print(make_demo(parser.parse_args().directory))
