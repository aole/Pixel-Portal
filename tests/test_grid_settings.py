import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QColorDialog

from portal.core.drawing_context import DrawingContext
from portal.core.settings_controller import SettingsController
from portal.ui.canvas import Canvas
from portal.ui.settings_dialog import SettingsDialog


def _configure_controller(controller: SettingsController, **overrides) -> None:
    settings = controller.get_grid_settings()
    settings.update(overrides)
    controller.update_grid_settings(**settings)


def test_settings_dialog_roundtrip_grid_settings(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    controller = SettingsController()
    _configure_controller(
        controller,
        major_visible=False,
        major_spacing=12,
        minor_visible=True,
        minor_spacing=3,
        major_color="#80336699",
        minor_color="#40abcdef",
    )

    dialog = SettingsDialog(controller)
    qtbot.addWidget(dialog)

    assert dialog.get_grid_settings() == controller.get_grid_settings()


def test_settings_dialog_reset_grid_defaults(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    controller = SettingsController()
    _configure_controller(
        controller,
        major_visible=False,
        major_spacing=16,
        minor_visible=False,
        minor_spacing=5,
        major_color="#ff123456",
        minor_color="#ff654321",
    )

    dialog = SettingsDialog(controller)
    qtbot.addWidget(dialog)

    dialog._reset_grid_tab()

    grid_settings = dialog.get_grid_settings()
    defaults = controller.get_default_grid_settings()

    assert grid_settings["major_visible"] == defaults["major_visible"]
    assert grid_settings["minor_visible"] == defaults["minor_visible"]
    assert grid_settings["major_spacing"] == defaults["major_spacing"]
    assert grid_settings["minor_spacing"] == defaults["minor_spacing"]
    assert grid_settings["major_color"] == defaults["major_color"]
    assert grid_settings["minor_color"] == defaults["minor_color"]


def test_choose_grid_color_updates_value(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    controller = SettingsController()
    dialog = SettingsDialog(controller)
    qtbot.addWidget(dialog)

    new_color = QColor("#123456")
    new_color.setAlpha(85)

    monkeypatch.setattr(
        QColorDialog,
        "getColor",
        lambda *args, **kwargs: QColor(new_color),
    )

    dialog._choose_major_grid_color()
    grid_settings = dialog.get_grid_settings()

    assert grid_settings["major_color"] == new_color.name(QColor.NameFormat.HexArgb)


def test_choose_grid_color_cancel_keeps_value(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    controller = SettingsController()
    _configure_controller(controller, major_color="#4099aabb")

    dialog = SettingsDialog(controller)
    qtbot.addWidget(dialog)

    initial_color = dialog.get_grid_settings()["major_color"]

    monkeypatch.setattr(
        QColorDialog,
        "getColor",
        lambda *args, **kwargs: QColor(),
    )

    dialog._choose_major_grid_color()

    assert dialog.get_grid_settings()["major_color"] == initial_color


def test_renderer_draw_grid_uses_major_and_minor_colors(qtbot):
    context = DrawingContext()
    canvas = Canvas(context)
    qtbot.addWidget(canvas)

    canvas.set_document_size(QSize(3, 3))
    canvas.resize(12, 12)
    canvas.zoom = 4
    canvas.grid_visible = True
    canvas.grid_major_visible = True
    canvas.grid_minor_visible = True
    canvas.grid_major_spacing = 2
    canvas.grid_minor_spacing = 1
    canvas.grid_major_color = QColor("#ff0000")
    canvas.grid_minor_color = QColor("#0000ff")

    image = QImage(canvas.width(), canvas.height(), QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    canvas.renderer.draw_grid(painter, canvas.get_target_rect())
    painter.end()

    major_hex = QColor("#ff0000").name(QColor.NameFormat.HexArgb)
    minor_hex = QColor("#0000ff").name(QColor.NameFormat.HexArgb)

    assert image.pixelColor(8, 5).name(QColor.NameFormat.HexArgb) == major_hex
    assert image.pixelColor(4, 5).name(QColor.NameFormat.HexArgb) == minor_hex
    assert image.pixelColor(5, 8).name(QColor.NameFormat.HexArgb) == major_hex
    assert image.pixelColor(5, 4).name(QColor.NameFormat.HexArgb) == minor_hex
    assert image.pixelColor(2, 5).alpha() == 0
