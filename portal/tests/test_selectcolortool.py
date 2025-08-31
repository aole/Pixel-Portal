from unittest.mock import Mock
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QColor, QImage, QPainterPath
from portal.tools.selectcolortool import SelectColorTool

@pytest.fixture
def select_color_tool(qtbot):
    mock_canvas = Mock()
    mock_document = Mock()
    image = QImage(10, 10, QImage.Format_ARGB32)
    image.fill(QColor("blue"))
    # Create a pattern of red pixels
    image.setPixelColor(2, 2, QColor("red"))
    image.setPixelColor(4, 4, QColor("red"))
    image.setPixelColor(6, 6, QColor("red"))
    mock_document.render.return_value = image
    mock_canvas.document = mock_document
    tool = SelectColorTool(mock_canvas)
    return tool

def test_mouse_press_event(select_color_tool):
    """
    This test should check that all pixels of the same color are selected.
    """
    tool = select_color_tool
    canvas = tool.canvas

    # Press on a red pixel
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(2, 2), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tool.mousePressEvent(event, QPoint(2, 2))

    canvas._update_selection_and_emit_size.assert_called_once()
    path = canvas._update_selection_and_emit_size.call_args[0][0]

    expected_path = QPainterPath()
    expected_path.addRect(QRect(2, 2, 1, 1))
    expected_path.addRect(QRect(4, 4, 1, 1))
    expected_path.addRect(QRect(6, 6, 1, 1))

    assert path == expected_path.simplified()
