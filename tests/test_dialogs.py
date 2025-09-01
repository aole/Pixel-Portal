# This file will contain tests for dialogs and panels.
import os
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton
from PySide6.QtCore import Qt
from portal.ui.palette_dialog import PaletteDialog
from portal.ui.new_file_dialog import NewFileDialog
from portal.ui.resize_dialog import ResizeDialog
from PySide6.QtGui import QImage, QPixmap
from portal.ui.preview_panel import PreviewPanel

def test_new_file_dialog(qtbot):
    """Test that the dialog is created and that the new_document method is called on the app when the dialog is accepted."""
    mock_app = MagicMock()
    dialog = NewFileDialog(mock_app)
    qtbot.addWidget(dialog)

    dialog.width_input.setText("128")
    dialog.height_input.setText("128")
    dialog.accept()

    mock_app.new_document.assert_called_once_with(128, 128)


def test_open_image(qtbot, monkeypatch):
    """Test that an image is opened and colors are extracted."""
    mock_get_open_file_name = MagicMock(return_value=("tests/test_image.png", "Image Files (*.png *.jpg *.bmp)"))
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


def test_get_values(qtbot):
    """Test that the correct width, height, and interpolation values are returned from the dialog."""
    dialog = ResizeDialog(width=100, height=100)
    qtbot.addWidget(dialog)

    dialog.width_input.setText("200")
    dialog.height_input.setText("200")
    dialog.interpolation_combo.setCurrentText("Smooth")

    values = dialog.get_values()

    assert values["width"] == 200
    assert values["height"] == 200
    assert values["interpolation"] == "Smooth"


def test_update_preview(qtbot):
    """Test that the preview is updated with a scaled version of the rendered document."""
    mock_app = MagicMock()
    mock_document = MagicMock()
    mock_app.document = mock_document

    # Create a 200x200 image, which should be scaled down to 128x128
    image = QImage(200, 200, QImage.Format_RGB32)
    mock_document.render.return_value = image

    panel = PreviewPanel(mock_app)
    qtbot.addWidget(panel)

    # The constructor calls update_preview, so reset the mock before calling it again.
    mock_document.render.reset_mock()

    panel.update_preview()

    mock_document.render.assert_called_once()
    pixmap = panel.preview_label.pixmap()
    assert not pixmap.isNull()
    assert pixmap.width() == 128
    assert pixmap.height() == 128
