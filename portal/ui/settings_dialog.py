from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from portal.ui.background import BackgroundImageMode


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    settings_applied = Signal()

    def __init__(self, settings_controller, parent=None):
        super().__init__(parent)
        self.settings_controller = settings_controller

        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget(self)
        layout.addWidget(self.tab_widget)

        self._build_grid_tab()
        self._build_canvas_tab()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply,
            parent=self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        apply_button = self.button_box.button(QDialogButtonBox.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply_and_emit)
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

    def _build_canvas_tab(self):
        canvas_tab = QWidget(self)
        canvas_layout = QGridLayout(canvas_tab)
        canvas_layout.setColumnStretch(1, 1)

        canvas_layout.addWidget(QLabel("Background image mode", canvas_tab), 0, 0)
        self.background_mode_combo = QComboBox(canvas_tab)
        self.background_mode_combo.setEditable(False)
        for mode, label in (
            (BackgroundImageMode.FIT, "Fit"),
            (BackgroundImageMode.STRETCH, "Stretch"),
            (BackgroundImageMode.FILL, "Fill"),
            (BackgroundImageMode.CENTER, "Center"),
        ):
            self.background_mode_combo.addItem(label, mode)
        canvas_layout.addWidget(self.background_mode_combo, 0, 1)
        canvas_layout.addWidget(QLabel("Background image opacity", canvas_tab), 1, 0)
        self.background_alpha_slider = QSlider(Qt.Horizontal, canvas_tab)
        self.background_alpha_slider.setRange(0, 100)
        self.background_alpha_slider.setSingleStep(1)
        self.background_alpha_slider.setPageStep(5)
        self.background_alpha_slider.setValue(100)
        canvas_layout.addWidget(self.background_alpha_slider, 1, 1)

        self.background_alpha_value_label = QLabel(canvas_tab)
        self.background_alpha_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._update_background_alpha_label(self.background_alpha_slider.value())
        canvas_layout.addWidget(self.background_alpha_value_label, 1, 2)
        self.background_alpha_slider.valueChanged.connect(
            self._update_background_alpha_label
        )

        canvas_layout.addWidget(QLabel("Ruler interval", canvas_tab), 2, 0)
        self.ruler_interval_spinbox = QSpinBox(canvas_tab)
        self.ruler_interval_spinbox.setMinimum(1)
        self.ruler_interval_spinbox.setMaximum(4096)
        canvas_layout.addWidget(self.ruler_interval_spinbox, 2, 1)
        canvas_layout.addWidget(QLabel("px", canvas_tab), 2, 2)

        canvas_layout.setRowStretch(3, 1)

        self.tab_widget.addTab(canvas_tab, "Canvas")

    def _apply_settings_to_widgets(self):
        grid_settings = self.settings_controller.get_grid_settings()
        self.major_grid_checkbox.setChecked(grid_settings["major_visible"])
        self.major_grid_spacing.setValue(grid_settings["major_spacing"])
        self.minor_grid_checkbox.setChecked(grid_settings["minor_visible"])
        self.minor_grid_spacing.setValue(grid_settings["minor_spacing"])

        background_settings = self.settings_controller.get_background_settings()
        background_mode = background_settings.get("image_mode")
        if not isinstance(background_mode, BackgroundImageMode):
            try:
                background_mode = BackgroundImageMode(background_mode)
            except ValueError:
                background_mode = BackgroundImageMode.FIT
        index = self.background_mode_combo.findData(background_mode)
        if index >= 0:
            self.background_mode_combo.setCurrentIndex(index)

        background_alpha = background_settings.get("image_alpha", 1.0)
        try:
            percent = int(round(float(background_alpha) * 100))
        except (TypeError, ValueError):
            percent = 100
        clamped_percent = max(0, min(100, percent))
        self.background_alpha_slider.setValue(clamped_percent)
        self._update_background_alpha_label(clamped_percent)

        ruler_settings = self.settings_controller.get_ruler_settings()
        interval = ruler_settings.get("interval", 8)
        try:
            interval_value = int(interval)
        except (TypeError, ValueError):
            interval_value = 8
        self.ruler_interval_spinbox.setValue(max(1, interval_value))

    def get_background_image_mode(self):
        data = self.background_mode_combo.currentData()
        if isinstance(data, BackgroundImageMode):
            return data
        try:
            return BackgroundImageMode(data)
        except ValueError:
            return BackgroundImageMode.FIT

    def get_background_image_alpha(self):
        value = self.background_alpha_slider.value() / 100.0
        return max(0.0, min(1.0, value))

    def _update_background_alpha_label(self, value):
        self.background_alpha_value_label.setText(f"{int(value)}%")

    def get_grid_settings(self):
        return {
            "major_visible": self.major_grid_checkbox.isChecked(),
            "major_spacing": self.major_grid_spacing.value(),
            "minor_visible": self.minor_grid_checkbox.isChecked(),
            "minor_spacing": self.minor_grid_spacing.value(),
        }

    def get_ruler_settings(self):
        return {
            "interval": self.ruler_interval_spinbox.value(),
        }

    def _apply_settings(self):
        self.settings_controller.update_grid_settings(**self.get_grid_settings())
        self.settings_controller.update_background_settings(
            image_mode=self.get_background_image_mode(),
            image_alpha=self.get_background_image_alpha(),
        )
        self.settings_controller.update_ruler_settings(**self.get_ruler_settings())

    def _apply_and_emit(self):
        self._apply_settings()
        self.settings_applied.emit()

    def accept(self):
        self._apply_and_emit()
        super().accept()
