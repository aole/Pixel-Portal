import os
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton
from PySide6.QtCore import Qt
from portal.palette_dialog import PaletteDialog

def test_open_image(qtbot, monkeypatch):
    """Test that an image is opened and colors are extracted."""
    mock_get_open_file_name = MagicMock(return_value=("portal/tests/test_image.png", "Image Files (*.png *.jpg *.bmp)"))
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", mock_get_open_file_name)

    dialog = PaletteDialog()
    qtbot.addWidget(dialog)

    dialog.open_image()

    def check_colors():
        assert len(dialog.colors) > 0
        assert dialog.color_list_widget.count() > 0

    qtbot.waitUntil(check_colors)

def test_get_selected_colors(qtbot):
    """Test that the correct colors are returned based on the checkbox selections."""
    dialog = PaletteDialog()
    qtbot.addWidget(dialog)

    colors = [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
    dialog.on_colors_extracted(colors)

    # Uncheck the second color
    item_widget = dialog.color_list_widget.itemWidget(dialog.color_list_widget.item(1))
    checkbox = item_widget.findChild(QCheckBox)
    checkbox.setChecked(False)

    selected_colors = dialog.get_selected_colors()

    assert len(selected_colors) == 2
    assert "#ff0000" in selected_colors
    assert "#0000ff" in selected_colors
