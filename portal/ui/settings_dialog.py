from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, settings_controller, parent=None):
        super().__init__(parent)
        self.settings_controller = settings_controller

        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)

        self._build_grid_tab()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._apply_settings_to_widgets()

    def _build_grid_tab(self):
        grid_tab = QWidget(self)
        grid_layout = QGridLayout(grid_tab)
        grid_layout.setColumnStretch(0, 1)

        self.major_grid_checkbox = QCheckBox("Show major grid lines", grid_tab)
        self.major_grid_spacing = QSpinBox(grid_tab)
        self.major_grid_spacing.setMinimum(1)
        self.major_grid_spacing.setMaximum(1024)
        self.major_grid_spacing.setEnabled(self.major_grid_checkbox.isChecked())
        self.major_grid_checkbox.toggled.connect(self.major_grid_spacing.setEnabled)

        self.minor_grid_checkbox = QCheckBox("Show minor grid lines", grid_tab)
        self.minor_grid_spacing = QSpinBox(grid_tab)
        self.minor_grid_spacing.setMinimum(1)
        self.minor_grid_spacing.setMaximum(1024)
        self.minor_grid_spacing.setEnabled(self.minor_grid_checkbox.isChecked())
        self.minor_grid_checkbox.toggled.connect(self.minor_grid_spacing.setEnabled)

        grid_layout.addWidget(self.major_grid_checkbox, 0, 0)
        grid_layout.addWidget(QLabel("Spacing (px)", grid_tab), 0, 1)
        grid_layout.addWidget(self.major_grid_spacing, 0, 2)

        grid_layout.addWidget(self.minor_grid_checkbox, 1, 0)
        grid_layout.addWidget(QLabel("Spacing (px)", grid_tab), 1, 1)
        grid_layout.addWidget(self.minor_grid_spacing, 1, 2)

        self.tab_widget.addTab(grid_tab, "Grid")

    def _apply_settings_to_widgets(self):
        grid_settings = self.settings_controller.get_grid_settings()
        self.major_grid_checkbox.setChecked(grid_settings["major_visible"])
        self.major_grid_spacing.setValue(grid_settings["major_spacing"])
        self.minor_grid_checkbox.setChecked(grid_settings["minor_visible"])
        self.minor_grid_spacing.setValue(grid_settings["minor_spacing"])

    def get_grid_settings(self):
        return {
            "major_visible": self.major_grid_checkbox.isChecked(),
            "major_spacing": self.major_grid_spacing.value(),
            "minor_visible": self.minor_grid_checkbox.isChecked(),
            "minor_spacing": self.minor_grid_spacing.value(),
        }

    def accept(self):
        self.settings_controller.update_grid_settings(**self.get_grid_settings())
        super().accept()
