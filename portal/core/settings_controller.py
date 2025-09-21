from PySide6.QtCore import QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox
import configparser
import os

from portal.ui.background import BackgroundImageMode


class SettingsController(QObject):
    """Manages application settings persistence."""

    DEFAULT_GRID_SETTINGS = {
        "major_visible": True,
        "minor_visible": True,
        "major_spacing": 8,
        "minor_spacing": 1,
        "major_color": "#64000000",
        "minor_color": "#64808080",
    }
    DEFAULT_RULER_SEGMENTS = 2

    DEFAULT_BACKGROUND_SETTINGS = {
        "image_mode": BackgroundImageMode.FIT,
        "image_alpha": 1.0,
    }

    DEFAULT_AI_SETTINGS = {
        "negative_prompt": "",
    }

    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')
        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

        if not self.config.has_section('Grid'):
            self.config.add_section('Grid')
        self.grid_major_visible = self._get_grid_bool(
            'major_visible', self.DEFAULT_GRID_SETTINGS["major_visible"]
        )
        self.grid_minor_visible = self._get_grid_bool(
            'minor_visible', self.DEFAULT_GRID_SETTINGS["minor_visible"]
        )
        self.grid_major_spacing = self._get_grid_int(
            'major_spacing', self.DEFAULT_GRID_SETTINGS["major_spacing"]
        )
        self.grid_minor_spacing = self._get_grid_int(
            'minor_spacing', self.DEFAULT_GRID_SETTINGS["minor_spacing"]
        )
        self.grid_major_color = self._get_grid_color(
            'major_color', self.DEFAULT_GRID_SETTINGS["major_color"]
        )
        self.grid_minor_color = self._get_grid_color(
            'minor_color', self.DEFAULT_GRID_SETTINGS["minor_color"]
        )
        self._sync_grid_settings_to_config()

        if not self.config.has_section('Background'):
            self.config.add_section('Background')
        raw_mode = self.config.get(
            'Background',
            'image_mode',
            fallback=self.DEFAULT_BACKGROUND_SETTINGS["image_mode"].value,
        )
        try:
            self.background_image_mode = BackgroundImageMode(raw_mode)
        except ValueError:
            self.background_image_mode = BackgroundImageMode.FIT

        try:
            alpha_value = self.config.getfloat('Background', 'image_alpha')
        except (configparser.NoOptionError, ValueError):
            alpha_value = self.DEFAULT_BACKGROUND_SETTINGS["image_alpha"]
        self.background_image_alpha = max(0.0, min(1.0, float(alpha_value)))
        self._sync_background_settings_to_config()

        if not self.config.has_section('Ruler'):
            self.config.add_section('Ruler')
        self.ruler_segments = self._get_ruler_int(
            'segments', self.DEFAULT_RULER_SEGMENTS
        )
        self._sync_ruler_settings_to_config()

        if not self.config.has_section('AI'):
            self.config.add_section('AI')
        self.ai_negative_prompt = self.config.get(
            'AI',
            'negative_prompt',
            fallback=self.DEFAULT_AI_SETTINGS["negative_prompt"],
        )
        self._sync_ai_settings_to_config()

    def save_settings(self, ai_settings=None):
        """Persist settings to disk."""
        try:
            if ai_settings:
                if not self.config.has_section('AI'):
                    self.config.add_section('AI')
                self.config.set('AI', 'last_prompt', ai_settings.get('prompt', ''))
                if 'negative_prompt' in ai_settings:
                    self.ai_negative_prompt = str(ai_settings['negative_prompt'])

            self._sync_grid_settings_to_config()
            self._sync_background_settings_to_config()
            self._sync_ruler_settings_to_config()
            self._sync_ai_settings_to_config()

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

    def _get_ruler_int(self, option, fallback):
        keys_to_try: tuple[str, ...]
        if option == 'segments':
            keys_to_try = ('segments', 'interval')
        else:
            keys_to_try = (option,)
        for key in keys_to_try:
            try:
                return max(1, self.config.getint('Ruler', key))
            except (configparser.NoOptionError, ValueError):
                continue
        return fallback

    def _get_grid_color(self, option, fallback):
        raw_value = self.config.get('Grid', option, fallback=fallback)
        color = QColor(raw_value)
        if not color.isValid():
            color = QColor(fallback)
        return color.name(QColor.NameFormat.HexArgb)

    def _sync_grid_settings_to_config(self):
        self.config.set('Grid', 'major_visible', str(self.grid_major_visible))
        self.config.set('Grid', 'minor_visible', str(self.grid_minor_visible))
        self.config.set('Grid', 'major_spacing', str(int(self.grid_major_spacing)))
        self.config.set('Grid', 'minor_spacing', str(int(self.grid_minor_spacing)))
        self.config.set('Grid', 'major_color', self.grid_major_color)
        self.config.set('Grid', 'minor_color', self.grid_minor_color)

    def _sync_background_settings_to_config(self):
        if not self.config.has_section('Background'):
            self.config.add_section('Background')
        self.config.set('Background', 'image_mode', self.background_image_mode.value)
        self.config.set('Background', 'image_alpha', f"{self.background_image_alpha:.3f}")

    def _sync_ruler_settings_to_config(self):
        if not self.config.has_section('Ruler'):
            self.config.add_section('Ruler')
        self.config.set('Ruler', 'segments', str(int(self.ruler_segments)))
        if self.config.has_option('Ruler', 'interval'):
            self.config.remove_option('Ruler', 'interval')

    def _sync_ai_settings_to_config(self):
        if not self.config.has_section('AI'):
            self.config.add_section('AI')
        self.config.set('AI', 'negative_prompt', self.ai_negative_prompt or '')

    def get_grid_settings(self):
        return {
            'major_visible': self.grid_major_visible,
            'minor_visible': self.grid_minor_visible,
            'major_spacing': int(self.grid_major_spacing),
            'minor_spacing': int(self.grid_minor_spacing),
            'major_color': self.grid_major_color,
            'minor_color': self.grid_minor_color,
        }

    def get_background_settings(self):
        return {
            'image_mode': self.background_image_mode,
            'image_alpha': self.background_image_alpha,
        }

    def get_ruler_settings(self):
        return {
            'segments': int(self.ruler_segments),
        }

    def get_ai_settings(self):
        return {
            'negative_prompt': self.ai_negative_prompt,
        }

    def get_default_grid_settings(self):
        return dict(self.DEFAULT_GRID_SETTINGS)

    def get_default_background_settings(self):
        return dict(self.DEFAULT_BACKGROUND_SETTINGS)

    def get_default_ai_settings(self):
        return dict(self.DEFAULT_AI_SETTINGS)

    def update_grid_settings(
        self,
        *,
        major_visible,
        major_spacing,
        minor_visible,
        minor_spacing,
        major_color=None,
        minor_color=None,
    ):
        self.grid_major_visible = bool(major_visible)
        self.grid_minor_visible = bool(minor_visible)
        self.grid_major_spacing = max(1, int(major_spacing))
        self.grid_minor_spacing = max(1, int(minor_spacing))
        if major_color is not None:
            color = QColor(major_color)
            if color.isValid():
                self.grid_major_color = color.name(QColor.NameFormat.HexArgb)
        if minor_color is not None:
            color = QColor(minor_color)
            if color.isValid():
                self.grid_minor_color = color.name(QColor.NameFormat.HexArgb)
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

    def update_ruler_settings(self, *, segments=None, interval=None):
        if segments is None and interval is not None:
            segments = interval
        if segments is not None:
            try:
                segments_value = int(segments)
            except (TypeError, ValueError):
                segments_value = self.ruler_segments
            self.ruler_segments = max(1, segments_value)
        self._sync_ruler_settings_to_config()

    def update_ai_settings(self, *, negative_prompt=None):
        if negative_prompt is not None:
            self.ai_negative_prompt = str(negative_prompt)
        self._sync_ai_settings_to_config()
