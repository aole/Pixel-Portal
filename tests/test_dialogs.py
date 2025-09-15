# This file will contain tests for dialogs and panels.
import os
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton
from PySide6.QtCore import Qt, QPoint, QSize
from portal.ui.new_file_dialog import NewFileDialog
from portal.ui.resize_dialog import ResizeDialog
from PySide6.QtGui import QImage, QPixmap
from portal.ui.preview_panel import PreviewPanel
from portal.ui.canvas import Canvas
from portal.core.drawing_context import DrawingContext

def test_new_file_dialog(qtbot):
    """Test that the dialog is created and that the new_document method is called on the app when the dialog is accepted."""
    mock_app = MagicMock()
    dialog = NewFileDialog(mock_app)
    qtbot.addWidget(dialog)

    dialog.width_input.setText("128")
    dialog.height_input.setText("128")
    dialog.accept()

    mock_app.new_document.assert_called_once_with(128, 128)




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


def test_canvas_tile_preview_toggle(qtbot):
    context = DrawingContext()
    canvas = Canvas(context)
    qtbot.addWidget(canvas)

    assert not canvas.tile_preview_enabled
    canvas.toggle_tile_preview(True)
    assert canvas.tile_preview_enabled
    canvas.toggle_tile_preview(False)
    assert not canvas.tile_preview_enabled


def test_canvas_tile_preview_coord_wrap(qtbot):
    context = DrawingContext()
    canvas = Canvas(context)
    qtbot.addWidget(canvas)
    canvas.set_document_size(QSize(10, 10))
    canvas.resize(100, 100)
    canvas.toggle_tile_preview(True)
    target = canvas.get_target_rect()
    outside = QPoint(target.right() + 1, target.top() + 3)
    wrapped = canvas.get_doc_coords(outside)
    assert wrapped.x() == 0
    assert wrapped.y() == 3
