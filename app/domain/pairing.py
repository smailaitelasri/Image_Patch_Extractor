# =============================
# domain/pairing.py
# =============================
"""
This module provides a function to find pairs of corresponding image and mask files.
"""

import glob
import os
from typing import List, Tuple


def list_pairs(
    images_dir: str, masks_dir: str, extensions: List[str]
) -> List[Tuple[str, str]]:
    """
    Finds pairs of image and mask files in the given directories.

    A pair is formed if an image and a mask have the same filename (excluding extension).

    Args:
        images_dir (str): The directory containing the images.
        masks_dir (str): The directory containing the masks.
        extensions (List[str]): A list of glob patterns for image file extensions to consider.

    Returns:
        List[Tuple[str, str]]: A list of tuples, where each tuple contains the
                               path to an image and its corresponding mask.
    """
    img_paths = []
    for ext in extensions:
        img_paths.extend(glob.glob(os.path.join(images_dir, ext)))
    img_paths = sorted(img_paths)

    mask_paths = []
    for ext in extensions:
        mask_paths.extend(glob.glob(os.path.join(masks_dir, ext)))

    pairs = []
    mask_index = {os.path.splitext(os.path.basename(m))[0]: m for m in mask_paths}
    for ip in img_paths:
        key = os.path.splitext(os.path.basename(ip))[0]
        if key in mask_index:
            pairs.append((ip, mask_index[key]))
    return pairs
