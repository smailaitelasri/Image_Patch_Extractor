"""
This module handles the persistence of application settings, such as the last
used configuration, by using PyQt's QSettings.
"""

from typing import Optional

from PyQt5.QtCore import QSettings

from app.domain.config_model import AppConfig


class AppSettings:
    """
    A wrapper around QSettings to save and load application configuration.
    """

    KEY_LAST = "last_config"
    KEY_IMG_FOLDER = "app/image_folder_name"
    KEY_MASK_FOLDER = "app/mask_folder_name"

    def __init__(self):
        """Initializes the QSettings object."""
        self.s = QSettings()
        if not self.s.value(self.KEY_IMG_FOLDER):
            self.s.setValue(self.KEY_IMG_FOLDER, "Image")
        if not self.s.value(self.KEY_MASK_FOLDER):
            self.s.setValue(self.KEY_MASK_FOLDER, "Mask")

    def image_folder_name(self) -> str:
        """Returns the name of the folder containing images."""
        return self.s.value(self.KEY_IMG_FOLDER, "Image")

    def mask_folder_name(self) -> str:
        """Returns the name of the folder containing masks."""
        return self.s.value(self.KEY_MASK_FOLDER, "Mask")

    def save_last_config(self, cfg: AppConfig):
        """
        Saves the given AppConfig object as the last used configuration.

        Args:
            cfg (AppConfig): The configuration to save.
        """
        self.s.setValue(self.KEY_LAST, cfg.to_json())

    def load_last_config(self) -> Optional[AppConfig]:
        """
        Loads the last used configuration.

        Returns:
            Optional[AppConfig]: The loaded configuration, or None if it can't be loaded.
        """
        s = self.s.value(self.KEY_LAST, "")
        if s:
            try:
                return AppConfig.from_json(s)
            except Exception:
                # Could log this error
                return None
        return None
