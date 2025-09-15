from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
import configparser
import os

from portal.ui.background import BackgroundImageMode


class SettingsController(QObject):
    """Manages application settings persistence."""

    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')
        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

        if not self.config.has_section('Grid'):
            self.config.add_section('Grid')
        self.grid_major_visible = self._get_grid_bool('major_visible', True)
        self.grid_minor_visible = self._get_grid_bool('minor_visible', True)
        self.grid_major_spacing = self._get_grid_int('major_spacing', 8)
        self.grid_minor_spacing = self._get_grid_int('minor_spacing', 1)
        self._sync_grid_settings_to_config()

        if not self.config.has_section('Background'):
            self.config.add_section('Background')
        raw_mode = self.config.get(
            'Background', 'image_mode', fallback=BackgroundImageMode.FIT.value
        )
        try:
            self.background_image_mode = BackgroundImageMode(raw_mode)
        except ValueError:
            self.background_image_mode = BackgroundImageMode.FIT

        try:
            alpha_value = self.config.getfloat('Background', 'image_alpha')
        except (configparser.NoOptionError, ValueError):
            alpha_value = 1.0
        self.background_image_alpha = max(0.0, min(1.0, float(alpha_value)))
        self._sync_background_settings_to_config()

    def save_settings(self, ai_settings=None):
        """Persist settings to disk."""
        try:
            if ai_settings:
                if not self.config.has_section('AI'):
                    self.config.add_section('AI')
                self.config.set('AI', 'last_prompt', ai_settings.get('prompt', ''))

            self._sync_grid_settings_to_config()
            self._sync_background_settings_to_config()

            with open('settings.ini', 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setText("Error saving settings")
            error_box.setInformativeText(f"Could not write to settings.ini.\n\nReason: {e}")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec()

    def _get_grid_bool(self, option, fallback):
        try:
            return self.config.getboolean('Grid', option)
        except (configparser.NoOptionError, ValueError):
            return fallback

    def _get_grid_int(self, option, fallback):
        try:
            return max(1, self.config.getint('Grid', option))
        except (configparser.NoOptionError, ValueError):
            return fallback

    def _sync_grid_settings_to_config(self):
        self.config.set('Grid', 'major_visible', str(self.grid_major_visible))
        self.config.set('Grid', 'minor_visible', str(self.grid_minor_visible))
        self.config.set('Grid', 'major_spacing', str(int(self.grid_major_spacing)))
        self.config.set('Grid', 'minor_spacing', str(int(self.grid_minor_spacing)))

    def _sync_background_settings_to_config(self):
        if not self.config.has_section('Background'):
            self.config.add_section('Background')
        self.config.set('Background', 'image_mode', self.background_image_mode.value)
        self.config.set('Background', 'image_alpha', f"{self.background_image_alpha:.3f}")

    def get_grid_settings(self):
        return {
            'major_visible': self.grid_major_visible,
            'minor_visible': self.grid_minor_visible,
            'major_spacing': int(self.grid_major_spacing),
            'minor_spacing': int(self.grid_minor_spacing),
        }

    def get_background_settings(self):
        return {
            'image_mode': self.background_image_mode,
            'image_alpha': self.background_image_alpha,
        }

    def update_grid_settings(
        self,
        *,
        major_visible,
        major_spacing,
        minor_visible,
        minor_spacing,
    ):
        self.grid_major_visible = bool(major_visible)
        self.grid_minor_visible = bool(minor_visible)
        self.grid_major_spacing = max(1, int(major_spacing))
        self.grid_minor_spacing = max(1, int(minor_spacing))
        self._sync_grid_settings_to_config()

    def update_background_settings(self, *, image_mode=None, image_alpha=None):
        if image_mode is not None:
            if not isinstance(image_mode, BackgroundImageMode):
                try:
                    image_mode = BackgroundImageMode(image_mode)
                except ValueError:
                    image_mode = BackgroundImageMode.FIT
            self.background_image_mode = image_mode

        if image_alpha is not None:
            try:
                alpha_value = float(image_alpha)
            except (TypeError, ValueError):
                alpha_value = self.background_image_alpha
            self.background_image_alpha = max(0.0, min(1.0, alpha_value))
        self._sync_background_settings_to_config()
