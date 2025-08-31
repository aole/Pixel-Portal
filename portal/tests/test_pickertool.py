from unittest.mock import Mock, patch
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage
from portal.tools.pickertool import PickerTool

@pytest.fixture
def picker_tool(qtbot):
    mock_canvas = Mock()
    mock_document = Mock()
    image = QImage(100, 100, QImage.Format_ARGB32)
    image.fill(QColor("blue"))
    image.setPixelColor(10, 10, QColor("red"))
    mock_document.render.return_value = image
    mock_canvas.document = mock_document
    tool = PickerTool(mock_canvas)
    return tool

def test_pick_color(picker_tool):
    """
    This test should verify that the correct color is picked from the rendered image.
    """
    tool = picker_tool
    canvas = tool.canvas

    # Test picking a colored pixel
    tool.pick_color(QPoint(10, 10))
    canvas.drawing_context.set_pen_color.assert_called_with("#ff0000")

    # Test picking a transparent pixel (alpha = 0)
    canvas.drawing_context.set_pen_color.reset_mock()
    image = canvas.document.render()
    image.setPixelColor(20, 20, QColor(0,0,0,0))
    tool.pick_color(QPoint(20, 20))
    canvas.drawing_context.set_pen_color.assert_not_called()

    # Test picking outside the image
    canvas.drawing_context.set_pen_color.reset_mock()
    tool.pick_color(QPoint(200, 200))
    canvas.drawing_context.set_pen_color.assert_not_called()
