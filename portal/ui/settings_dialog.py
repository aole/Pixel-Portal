from typing import Any

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

    GRID_COLOR_FALLBACKS = {
        "major": "#64000000",
        "minor": "#64808080",
    }

    def __init__(self, settings_controller, parent=None):
        super().__init__(parent)
        self.settings_controller = settings_controller

        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)

        self._grid_rows: dict[str, dict[str, Any]] = {}

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

        defaults = self.settings_controller.get_default_grid_settings()

        (
            self.major_grid_checkbox,
            self.major_grid_spacing,
            self.major_grid_color_button,
        ) = self._create_grid_row(
            parent=grid_tab,
            layout=grid_layout,
            key="major",
            label="Major",
            row_index=0,
            defaults=defaults,
        )

        (
            self.minor_grid_checkbox,
            self.minor_grid_spacing,
            self.minor_grid_color_button,
        ) = self._create_grid_row(
            parent=grid_tab,
            layout=grid_layout,
            key="minor",
            label="Minor",
            row_index=1,
            defaults=defaults,
        )

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

    def _create_grid_row(
        self,
        *,
        parent: QWidget,
        layout: QGridLayout,
        key: str,
        label: str,
        row_index: int,
        defaults: dict[str, Any],
    ):
        checkbox = QCheckBox(label, parent)
        default_visible = bool(defaults.get(f"{key}_visible", True))
        checkbox.setChecked(default_visible)

        spacing = QSpinBox(parent)
        spacing.setRange(1, 1024)
        default_spacing = defaults.get(f"{key}_spacing", spacing.minimum())
        spacing.setValue(
            self._sanitize_spacing_value(
                default_spacing, spacing.minimum(), spacing.maximum()
            )
        )
        spacing.setEnabled(checkbox.isChecked())
        checkbox.toggled.connect(spacing.setEnabled)

        color_button = QPushButton(parent)
        color_button.setAutoDefault(False)
        color_button.setEnabled(checkbox.isChecked())
        checkbox.toggled.connect(color_button.setEnabled)
        color_button.clicked.connect(
            lambda _checked=False, row_key=key: self._choose_grid_color(row_key)
        )

        layout.addWidget(checkbox, row_index, 0)
        layout.addWidget(QLabel("Spacing (px)", parent), row_index, 1)
        layout.addWidget(spacing, row_index, 2)
        layout.addWidget(color_button, row_index, 3)

        fallback_color = defaults.get(
            f"{key}_color", self.GRID_COLOR_FALLBACKS[key]
        )
        normalized_color = self._normalize_color_value(
            fallback_color, self.GRID_COLOR_FALLBACKS[key]
        )
        self._grid_rows[key] = {
            "checkbox": checkbox,
            "spacing": spacing,
            "color_button": color_button,
            "color": normalized_color,
        }
        self._update_color_button(color_button, normalized_color)

        return checkbox, spacing, color_button

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

        canvas_layout.addWidget(QLabel("Ruler segments", canvas_tab), 2, 0)
        self.ruler_segments_spinbox = QSpinBox(canvas_tab)
        self.ruler_segments_spinbox.setMinimum(1)
        self.ruler_segments_spinbox.setMaximum(4096)
        canvas_layout.addWidget(self.ruler_segments_spinbox, 2, 1)
        canvas_layout.addWidget(QLabel("segments", canvas_tab), 2, 2)

        self.canvas_reset_button = QPushButton("Reset to Defaults", canvas_tab)
        self.canvas_reset_button.clicked.connect(self._reset_canvas_tab)
        canvas_layout.addWidget(
            self.canvas_reset_button,
            3,
            0,
            1,
            3,
            alignment=Qt.AlignmentFlag.AlignRight,
        )
        canvas_layout.setRowStretch(4, 1)

        self.tab_widget.addTab(canvas_tab, "Canvas")

    def _apply_settings_to_widgets(self):
        grid_settings = self.settings_controller.get_grid_settings()
        defaults = self.settings_controller.get_default_grid_settings()
        self._apply_grid_row_settings("major", grid_settings, defaults)
        self._apply_grid_row_settings("minor", grid_settings, defaults)

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
        segments = ruler_settings.get(
            "segments",
            getattr(
                self.settings_controller,
                "DEFAULT_RULER_SEGMENTS",
                2,
            ),
        )
        try:
            segments_value = int(segments)
        except (TypeError, ValueError):
            segments_value = getattr(
                self.settings_controller,
                "DEFAULT_RULER_SEGMENTS",
                2,
            )
        self.ruler_segments_spinbox.setValue(max(1, segments_value))

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
        major_row = self._grid_rows["major"]
        minor_row = self._grid_rows["minor"]
        return {
            "major_visible": major_row["checkbox"].isChecked(),
            "major_spacing": major_row["spacing"].value(),
            "minor_visible": minor_row["checkbox"].isChecked(),
            "minor_spacing": minor_row["spacing"].value(),
            "major_color": major_row["color"],
            "minor_color": minor_row["color"],
        }

    def get_ruler_settings(self):
        return {
            "segments": self.ruler_segments_spinbox.value(),
        }

    def _apply_settings(self):
        self.settings_controller.update_grid_settings(**self.get_grid_settings())
        self.settings_controller.update_background_settings(
            image_mode=self.get_background_image_mode(),
            image_alpha=self.get_background_image_alpha(),
        )
        self.settings_controller.update_ruler_settings(**self.get_ruler_settings())

    def _reset_grid_tab(self):
        defaults = self.settings_controller.get_default_grid_settings()
        self._apply_grid_row_settings("major", defaults, defaults)
        self._apply_grid_row_settings("minor", defaults, defaults)

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
        self.ruler_segments_spinbox.setValue(
            getattr(self.settings_controller, "DEFAULT_RULER_SEGMENTS", 2)
        )

    def _choose_major_grid_color(self):
        self._choose_grid_color("major")

    def _choose_minor_grid_color(self):
        self._choose_grid_color("minor")

    def _choose_grid_color(self, key: str):
        row = self._grid_rows[key]
        defaults = self.settings_controller.get_default_grid_settings()
        fallback = defaults.get(f"{key}_color", self.GRID_COLOR_FALLBACKS[key])
        current_value = row["color"]
        base_color = QColor(
            self._normalize_color_value(current_value, fallback)
        )
        if not base_color.isValid():
            base_color = QColor(fallback)
        if not base_color.isValid():
            base_color = QColor("#000000")

        chosen_color = QColorDialog.getColor(
            base_color,
            self,
            "Select grid color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if not chosen_color.isValid():
            chosen_color = base_color

        color_name = self._normalize_color_value(
            chosen_color.name(QColor.NameFormat.HexArgb), fallback
        )
        row["color"] = color_name
        self._update_color_button(row["color_button"], color_name)
        return color_name

    def _apply_grid_row_settings(
        self,
        key: str,
        settings: dict[str, Any],
        defaults: dict[str, Any],
    ):
        row = self._grid_rows[key]
        checkbox: QCheckBox = row["checkbox"]
        spacing: QSpinBox = row["spacing"]
        color_button: QPushButton = row["color_button"]

        visible_value = settings.get(
            f"{key}_visible", defaults.get(f"{key}_visible", True)
        )
        checkbox.setChecked(bool(visible_value))
        spacing.setEnabled(checkbox.isChecked())
        color_button.setEnabled(checkbox.isChecked())

        spacing_value = settings.get(
            f"{key}_spacing", defaults.get(f"{key}_spacing", spacing.value())
        )
        spacing.setValue(
            self._sanitize_spacing_value(
                spacing_value, spacing.minimum(), spacing.maximum()
            )
        )

        fallback_color = defaults.get(
            f"{key}_color", self.GRID_COLOR_FALLBACKS[key]
        )
        color_value = settings.get(f"{key}_color", fallback_color)
        normalized_color = self._normalize_color_value(color_value, fallback_color)
        row["color"] = normalized_color
        self._update_color_button(color_button, normalized_color)

    @staticmethod
    def _sanitize_spacing_value(value, minimum: int, maximum: int) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return minimum
        return max(minimum, min(maximum, numeric))

    @staticmethod
    def _normalize_color_value(color_value, fallback: str) -> str:
        color = QColor(color_value) if color_value is not None else QColor()
        if not color.isValid():
            color = QColor(fallback)
        if not color.isValid():
            color = QColor("#000000")
        return color.name(QColor.NameFormat.HexArgb)

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
