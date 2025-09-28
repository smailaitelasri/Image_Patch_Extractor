# =============================
# domain/config_model.py
# =============================
"""
This module defines the data model for the application's configuration.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class AppConfig:
    """
    A dataclass that holds all the configuration parameters for the application.
    """

    data_root: str = ""
    patch_root: str = ""
    patch_size: int = 256
    stride: int = 256
    min_mask_ratio: float = 0.0
    max_patches_per_image: int = 0
    save_format: str = "png"
    seed: int = 123
    include_borders: bool = True
    apply_min_mask_ratio: bool = True
    dry_run: bool = False

    # New field for file extensions
    image_extensions: List[str] = field(
        default_factory=lambda: ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"]
    )

    def validate(self) -> Optional[str]:
        """Validates the configuration parameters."""
        if not self.data_root or not os.path.isdir(self.data_root):
            return "Invalid data_root"
        if not self.patch_root:
            return "patch_root is required"
        if self.patch_size <= 0 or self.stride <= 0:
            return "patch_size and stride must be > 0"
        if not isinstance(self.image_extensions, list) or not all(
            isinstance(ext, str) for ext in self.image_extensions
        ):
            return "image_extensions must be a list of strings"
        if self.save_format not in ("png", "jpg", "tif"):
            return "Unsupported save format"
        return None

    def to_json(self) -> str:
        """Serializes the configuration to a JSON string."""
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(s: str) -> "AppConfig":
        """Deserializes a JSON string into an AppConfig object."""
        return AppConfig(**json.loads(s))
