from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
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

        self._major_grid_color = "#64000000"
        self._minor_grid_color = "#64808080"

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

        self.major_grid_color_button = QPushButton(grid_tab)
        self.major_grid_color_button.clicked.connect(self._choose_major_grid_color)
        self.major_grid_color_button.setEnabled(self.major_grid_checkbox.isChecked())
        self.major_grid_checkbox.toggled.connect(self.major_grid_color_button.setEnabled)
        self.minor_grid_color_button = QPushButton(grid_tab)
        self.minor_grid_color_button.clicked.connect(self._choose_minor_grid_color)
        self.minor_grid_color_button.setEnabled(self.minor_grid_checkbox.isChecked())
        self.minor_grid_checkbox.toggled.connect(self.minor_grid_color_button.setEnabled)

        grid_layout.addWidget(self.major_grid_checkbox, 0, 0)
        grid_layout.addWidget(QLabel("Spacing (px)", grid_tab), 0, 1)
        grid_layout.addWidget(self.major_grid_spacing, 0, 2)
        grid_layout.addWidget(self.major_grid_color_button, 0, 3)

        grid_layout.addWidget(self.minor_grid_checkbox, 1, 0)
        grid_layout.addWidget(QLabel("Spacing (px)", grid_tab), 1, 1)
        grid_layout.addWidget(self.minor_grid_spacing, 1, 2)
        grid_layout.addWidget(self.minor_grid_color_button, 1, 3)

        self.grid_reset_button = QPushButton("Reset to Defaults", grid_tab)
        self.grid_reset_button.clicked.connect(self._reset_grid_tab)
        grid_layout.addWidget(
            self.grid_reset_button,
            2,
            0,
            1,
            4,
            alignment=Qt.AlignmentFlag.AlignRight,
        )
        grid_layout.setRowStretch(3, 1)

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

        self.canvas_reset_button = QPushButton("Reset to Defaults", canvas_tab)
        self.canvas_reset_button.clicked.connect(self._reset_canvas_tab)
        canvas_layout.addWidget(
            self.canvas_reset_button,
            2,
            0,
            1,
            3,
            alignment=Qt.AlignmentFlag.AlignRight,
        )
        canvas_layout.setRowStretch(3, 1)

        self.tab_widget.addTab(canvas_tab, "Canvas")

    def _apply_settings_to_widgets(self):
        grid_settings = self.settings_controller.get_grid_settings()
        self.major_grid_checkbox.setChecked(grid_settings["major_visible"])
        self.major_grid_spacing.setValue(grid_settings["major_spacing"])
        self.minor_grid_checkbox.setChecked(grid_settings["minor_visible"])
        self.minor_grid_spacing.setValue(grid_settings["minor_spacing"])
        self._major_grid_color = grid_settings.get("major_color", "#64000000")
        self._minor_grid_color = grid_settings.get("minor_color", "#64808080")
        self._update_color_button(self.major_grid_color_button, self._major_grid_color)
        self._update_color_button(self.minor_grid_color_button, self._minor_grid_color)

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
            "major_color": self._major_grid_color,
            "minor_color": self._minor_grid_color,
        }

    def _apply_settings(self):
        self.settings_controller.update_grid_settings(**self.get_grid_settings())
        self.settings_controller.update_background_settings(
            image_mode=self.get_background_image_mode(),
            image_alpha=self.get_background_image_alpha(),
        )

    def _reset_grid_tab(self):
        defaults = self.settings_controller.get_default_grid_settings()
        self.major_grid_checkbox.setChecked(defaults.get("major_visible", True))
        self.major_grid_spacing.setValue(defaults.get("major_spacing", 8))
        self.minor_grid_checkbox.setChecked(defaults.get("minor_visible", True))
        self.minor_grid_spacing.setValue(defaults.get("minor_spacing", 1))

        self._major_grid_color = defaults.get("major_color", "#64000000")
        self._minor_grid_color = defaults.get("minor_color", "#64808080")
        self._update_color_button(self.major_grid_color_button, self._major_grid_color)
        self._update_color_button(self.minor_grid_color_button, self._minor_grid_color)

    def _reset_canvas_tab(self):
        defaults = self.settings_controller.get_default_background_settings()
        mode = defaults.get("image_mode", BackgroundImageMode.FIT)
        if not isinstance(mode, BackgroundImageMode):
            try:
                mode = BackgroundImageMode(mode)
            except ValueError:
                mode = BackgroundImageMode.FIT
        index = self.background_mode_combo.findData(mode)
        if index >= 0:
            self.background_mode_combo.setCurrentIndex(index)

        alpha_value = defaults.get("image_alpha", 1.0)
        try:
            percent = int(round(float(alpha_value) * 100))
        except (TypeError, ValueError):
            percent = 100
        clamped_percent = max(0, min(100, percent))
        self.background_alpha_slider.setValue(clamped_percent)
        self._update_background_alpha_label(clamped_percent)

    def _choose_major_grid_color(self):
        self._major_grid_color = self._choose_grid_color(
            self._major_grid_color, self.major_grid_color_button
        )

    def _choose_minor_grid_color(self):
        self._minor_grid_color = self._choose_grid_color(
            self._minor_grid_color, self.minor_grid_color_button
        )

    def _choose_grid_color(self, current_color, button):
        color = QColor(current_color)
        if not color.isValid():
            color = QColor("#000000")
        chosen_color = QColorDialog.getColor(color, self, "Select grid color")
        if chosen_color.isValid():
            chosen_color.setAlpha(100)
            color_name = chosen_color.name(QColor.NameFormat.HexArgb)
            self._update_color_button(button, color_name)
            return color_name
        self._update_color_button(button, color.name(QColor.NameFormat.HexArgb))
        return current_color

    def _update_color_button(self, button, color_value):
        color = QColor(color_value)
        if not color.isValid():
            color = QColor("#000000")
        rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        text_color = "#000000" if brightness > 160 else "#FFFFFF"
        button.setStyleSheet(
            "QPushButton {"
            f"background-color: {rgba};"
            "border: 1px solid palette(mid);"
            "min-width: 72px;"
            f"color: {text_color};"
            "}"
        )
        button.setText(color.name(QColor.NameFormat.HexRgb).upper())
        button.setToolTip(color.name(QColor.NameFormat.HexArgb))

    def _apply_and_emit(self):
        self._apply_settings()
        self.settings_applied.emit()

    def accept(self):
        self._apply_and_emit()
        super().accept()
