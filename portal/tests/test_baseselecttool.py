from unittest.mock import Mock
import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainterPath
from portal.tools.baseselecttool import BaseSelectTool

@pytest.fixture
def base_select_tool(qtbot):
    mock_canvas = Mock()
    mock_canvas.zoom = 1.0
    tool = BaseSelectTool(mock_canvas)
    return tool

def test_is_on_selection_border(base_select_tool):
    """
    This test should check that True is returned when the position is
    on the selection border and False otherwise.
    """
    tool = base_select_tool
    canvas = tool.canvas

    path = QPainterPath()
    path.addRect(QRect(10, 10, 20, 20))
    canvas.selection_shape = path

    # Test a point on the border
    assert tool.is_on_selection_border(QPoint(10, 20)) is True
    # Test a point inside the selection
    assert tool.is_on_selection_border(QPoint(15, 15)) is False
    # Test a point outside the selection
    assert tool.is_on_selection_border(QPoint(50, 50)) is False

    # Test with no selection
    canvas.selection_shape = None
    assert tool.is_on_selection_border(QPoint(10, 20)) is False
