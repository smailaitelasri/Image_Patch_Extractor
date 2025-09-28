"""
This module contains the core logic for extracting patches from image/mask pairs.
It includes functions for file I/O, generating patch coordinates, and the main
extraction process.
"""

# =============================
# domain/patch_extractor.py
# =============================
import os
import random
from typing import Iterable, Tuple

import numpy as np
from PIL import Image


# --- IO helpers ---
def ensure_dir(path: str):
    """Creates a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def load_image(path: str) -> np.ndarray:
    """Loads an image file into a numpy array."""
    im = Image.open(path).convert("RGB")
    return np.array(im)


def load_mask(path: str) -> np.ndarray:
    """
    Loads a mask file into a binary numpy array.
    The mask is converted to a single channel and thresholded at 0.
    """
    m = Image.open(path)
    m = np.array(m)
    if m.ndim == 3:
        m = m[..., 0]
    m = (m > 0).astype(np.uint8)
    return m


def save_image(path: str, arr: np.ndarray):
    """Saves a numpy array as an image file."""
    Image.fromarray(arr).save(path)


# --- Core extraction ---
def iter_patch_coords(
    H: int, W: int, ph: int, pw: int, stride: int, include_borders: bool
) -> Iterable[Tuple[int, int]]:
    """
    Generates coordinates for patches to be extracted from an image.

    Args:
        H (int): Height of the source image.
        W (int): Width of the source image.
        ph (int): Height of the patches.
        pw (int): Width of the patches.
        stride (int): The step size between patches.
        include_borders (bool): Whether to include patches at the right and bottom
                                edges if the image dimensions are not a multiple of the stride.

    Returns:
        Iterable[Tuple[int,int]]: An iterable of (y, x) coordinates for the top-left
                                  corner of each patch.
    """
    coords = set()
    for y in range(0, max(1, H - ph + 1), stride):
        for x in range(0, max(1, W - pw + 1), stride):
            coords.add((y, x))
    if include_borders:
        if (H - ph) % stride != 0 and H > ph:
            for x in range(0, max(1, W - pw + 1), stride):
                coords.add((H - ph, x))
        if (W - pw) % stride != 0 and W > pw:
            for y in range(0, max(1, H - ph + 1), stride):
                coords.add((y, W - pw))
    return sorted(list(coords))


def extract_patches_for_pair(
    img_path: str,
    mask_path: str,
    out_img_dir: str,
    out_msk_dir: str,
    patch: int,
    stride: int,
    min_mask_ratio: float,
    max_patches: int = 0,
    save_format: str = "png",
    include_borders: bool = True,
    apply_ratio: bool = True,
) -> Tuple[int, dict, np.ndarray, np.ndarray]:
    """
    Extracts and saves patches from a single image-mask pair.

    Args:
        img_path (str): Path to the source image.
        mask_path (str): Path to the source mask.
        out_img_dir (str): Directory to save image patches.
        out_msk_dir (str): Directory to save mask patches.
        patch (int): The size (height and width) of the patches.
        stride (int): The step size between patches.
        min_mask_ratio (float): The minimum ratio of mask pixels for a patch to be kept.
        max_patches (int, optional): The maximum number of patches to keep per image.
                                     If 0, all are kept. Defaults to 0.
        save_format (str, optional): The format to save patches in. Defaults to "png".
        include_borders (bool, optional): Whether to include edge patches. Defaults to True.
        apply_ratio (bool, optional): Whether to apply the min_mask_ratio filter. Defaults to True.

    Returns:
        Tuple[int, dict, np.ndarray, np.ndarray]: A tuple containing:
            - The number of patches kept.
            - A dictionary of statistics.
            - The loaded source image.
            - The loaded source mask.
    """
    img = load_image(img_path)
    msk = load_mask(mask_path)
    H, W = img.shape[:2]
    ph, pw = patch, patch

    coords = list(iter_patch_coords(H, W, ph, pw, stride, include_borders))

    kept = []
    coverages = []
    for y, x in coords:
        m = msk[y : y + ph, x : x + pw]
        if m.shape[0] != ph or m.shape[1] != pw:
            continue
        ratio = float(m.mean())
        coverages.append(ratio)
        if (not apply_ratio) or (ratio >= min_mask_ratio):
            kept.append((y, x))

    if max_patches > 0 and len(kept) > max_patches:
        random.shuffle(kept)
        kept = kept[:max_patches]

    base = os.path.splitext(os.path.basename(img_path))[0]
    count = 0
    for y, x in kept:
        crop_img = img[y : y + ph, x : x + pw, :]
        crop_msk = msk[y : y + ph, x : x + pw]
        out_name = f"{base}_y{y}_x{x}.{save_format}"
        save_image(os.path.join(out_img_dir, out_name), crop_img)
        save_image(
            os.path.join(out_msk_dir, out_name), (crop_msk * 255).astype(np.uint8)
        )
        count += 1

    stats = {
        "total_coords": len(coords),
        "kept": len(kept),
        "coverage_mean": float(np.mean(coverages)) if coverages else 0.0,
    }
    return count, stats, img, msk
