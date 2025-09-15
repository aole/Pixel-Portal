from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
import configparser
import os


class SettingsController(QObject):
    """Manages application settings persistence."""

    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')
        if not self.config.has_section('General'):
            self.config.add_section('General')
        self.last_directory = self.config.get('General', 'last_directory', fallback=os.path.expanduser("~"))

    def save_settings(self, ai_settings=None):
        """Persist settings to disk."""
        try:
            if ai_settings:
                if not self.config.has_section('AI'):
                    self.config.add_section('AI')
                self.config.set('AI', 'last_prompt', ai_settings.get('prompt', ''))

            with open('settings.ini', 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setText("Error saving settings")
            error_box.setInformativeText(f"Could not write to settings.ini.\n\nReason: {e}")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec()
