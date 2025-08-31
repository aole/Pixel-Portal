import pytest
from unittest.mock import Mock, call
from PySide6.QtCore import QPoint, Qt, QSize
from PySide6.QtGui import QMouseEvent, QColor
from portal.canvas import Canvas
from portal.drawing_context import DrawingContext
from portal.document import Document

@pytest.fixture
def drawing_context():
    return DrawingContext()

@pytest.fixture
def canvas(qapp, drawing_context):
    canvas = Canvas(drawing_context)
    canvas.set_document(Document(100, 100))
    drawing_context.set_pen_color(QColor("red"))
    drawing_context.set_pen_width(5)
    drawing_context.set_brush_type("Square")
    canvas.on_tool_changed("Pen")
    return canvas

def test_pen_tool_emits_command(canvas):
    """
    Test that using the Pen tool correctly emits the command_generated signal
    with the right data.
    """
    spy = Mock()
    canvas.command_generated.connect(spy)

    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)

    canvas.mousePressEvent(press_event)
    canvas.mouseMoveEvent(move_event)
    canvas.mouseReleaseEvent(release_event)

    spy.assert_called_once()
    command = spy.call_args[0][0]
    from portal.command import DrawCommand
    assert isinstance(command, DrawCommand)
    assert len(command.points) == 2
    assert command.points[0] == canvas.get_doc_coords(QPoint(10, 10))
    assert command.points[1] == canvas.get_doc_coords(QPoint(20, 20))
    assert command.color == QColor("red")
    assert command.width == 5
    assert command.brush_type == "Square"
    assert command.erase is False
    assert command.selection_shape is None

def test_set_background(canvas):
    """Test that the background is updated correctly."""
    from portal.background import Background
    background = Background(QColor("blue"))
    canvas.set_background(background)
    assert canvas.background == background

def test_select_all(canvas):
    """Test that a selection is created for the entire document."""
    from PySide6.QtCore import QRect
    canvas.select_all()
    assert canvas.selection_shape is not None
    assert canvas.selection_shape.boundingRect() == QRect(0, 0, canvas.document.width, canvas.document.height)

def test_select_none(canvas):
    """Test that the selection is cleared."""
    canvas.select_all()
    assert canvas.selection_shape is not None
    canvas.select_none()
    assert canvas.selection_shape is None

def test_invert_selection(canvas):
    """Test that the selection is inverted correctly."""
    from PySide6.QtGui import QPainterPath
    from PySide6.QtCore import QRect
    rect = QRect(0, 0, 50, 50)
    path = QPainterPath()
    path.addRect(rect)
    canvas.selection_shape = path
    canvas.invert_selection()
    assert not canvas.selection_shape.contains(QPoint(25, 25))
    assert canvas.selection_shape.contains(QPoint(75, 75))

def test_get_doc_coords(canvas):
    """Test that canvas coordinates are correctly converted to document coordinates."""
    canvas.zoom = 2.0
    canvas.x_offset = 0
    canvas.y_offset = 0
    canvas_width = canvas.width()
    canvas_height = canvas.height()
    canvas_center = QPoint(canvas_width / 2, canvas_height / 2)
    doc_center = canvas.get_doc_coords(canvas_center)
    assert doc_center == QPoint(canvas.document.width / 2, canvas.document.height / 2)

def test_get_canvas_coords(canvas):
    """Test that document coordinates are correctly converted to canvas coordinates."""
    canvas.zoom = 2.0
    canvas.x_offset = 0
    canvas.y_offset = 0
    canvas_width = canvas.width()
    canvas_height = canvas.height()
    doc_center = QPoint(canvas.document.width / 2, canvas.document.height / 2)
    canvas_center = canvas.get_canvas_coords(doc_center)
    assert canvas_center == QPoint(canvas_width / 2, canvas_height / 2)

def test_mouse_press_event(canvas):
    """Test that the correct tool's mousePressEvent is called."""
    mock_tool = Mock()
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mousePressEvent(event)
    mock_tool.mousePressEvent.assert_called_once()

def test_mouse_move_event(canvas):
    """Test that the correct tool's mouseMoveEvent is called and cursor position is updated."""
    mock_tool = Mock()
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mouseMoveEvent(event)
    mock_tool.mouseMoveEvent.assert_called_once()
    assert canvas.cursor_doc_pos != QPoint(0, 0)

def test_mouse_release_event(canvas):
    """Test that the correct tool's mouseReleaseEvent is called."""
    mock_tool = Mock()
    canvas.current_tool = mock_tool
    event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mouseReleaseEvent(event)
    mock_tool.mouseReleaseEvent.assert_called_once()

def test_wheel_event(canvas):
    """Test that the zoom level and offsets are updated correctly."""
    from PySide6.QtGui import QWheelEvent
    initial_zoom = canvas.zoom
    initial_x_offset = canvas.x_offset
    initial_y_offset = canvas.y_offset
    event_in = QWheelEvent(QPoint(50, 50), QPoint(50, 50), QPoint(0, 120), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    canvas.wheelEvent(event_in)
    assert canvas.zoom > initial_zoom
    assert canvas.x_offset != initial_x_offset
    assert canvas.y_offset != initial_y_offset
    event_out = QWheelEvent(QPoint(50, 50), QPoint(50, 50), QPoint(0, -120), QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    canvas.wheelEvent(event_out)
    assert canvas.zoom == pytest.approx(initial_zoom)

def test_toggle_grid(canvas):
    """Test that the grid visibility is toggled and the canvas is updated."""
    from unittest.mock import patch
    assert not canvas.grid_visible
    with patch.object(canvas, 'update') as mock_update:
        canvas.toggle_grid()
        assert canvas.grid_visible
        mock_update.assert_called_once()
    with patch.object(canvas, 'update') as mock_update:
        canvas.toggle_grid()
        assert not canvas.grid_visible
        mock_update.assert_called_once()
