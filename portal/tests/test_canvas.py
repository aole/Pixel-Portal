import unittest
from unittest.mock import Mock, call
from PySide6.QtCore import QPoint, Qt, QSize
from PySide6.QtGui import QMouseEvent, QColor
from PySide6.QtWidgets import QApplication
from portal.canvas import Canvas

# Ensure a QApplication instance exists before creating any widgets
app = QApplication.instance()
if app is None:
    app = QApplication([])

from portal.drawing_context import DrawingContext

class TestCanvas(unittest.TestCase):

    def setUp(self):
        """Set up a fresh Canvas for each test."""
        from portal.document import Document
        self.drawing_context = DrawingContext()
        self.canvas = Canvas(self.drawing_context)
        # Set initial properties, as the App would via signal/slot connections
        self.canvas.set_document(Document(100, 100))
        self.canvas.set_pen_color(QColor("red"))
        self.canvas.set_pen_width(5)
        self.canvas.set_brush_type("Square")
        self.canvas.on_tool_changed("Pen")

    def test_pen_tool_emits_command(self):
        """
        Test that using the Pen tool correctly emits the command_generated signal
        with the right data.
        """
        # Create a mock object (a "spy") to connect to the signal
        spy = Mock()
        self.canvas.command_generated.connect(spy)

        # Simulate a mouse drag
        press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        move_event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)

        self.canvas.mousePressEvent(press_event)
        self.canvas.mouseMoveEvent(move_event)
        self.canvas.mouseReleaseEvent(release_event)

        # Assert that the signal was called exactly once
        spy.assert_called_once()

        # Get the arguments the spy was called with
        args = spy.call_args[0][0]  # call_args is a tuple ((args,), kwargs)
        command_type, data = args

        # Assert the command data is correct
        self.assertEqual(command_type, "draw")
        self.assertIn("points", data)
        self.assertEqual(len(data["points"]), 2)
        self.assertEqual(data["points"][0], self.canvas.get_doc_coords(QPoint(10, 10)))
        self.assertEqual(data["points"][1], self.canvas.get_doc_coords(QPoint(20, 20)))
        self.assertEqual(data["color"], QColor("red"))
        self.assertEqual(data["width"], 5)
        self.assertEqual(data["brush_type"], "Square")
        self.assertEqual(data.get("erase", False), False)
        self.assertIsNone(data["selection_shape"])

    def test_set_background(self):
        """Test that the background is updated correctly."""
        from portal.background import Background
        from PySide6.QtGui import QColor

        # Create a new background
        background = Background(QColor("blue"))

        # Set the background
        self.canvas.set_background(background)

        # Assert that the background was updated
        self.assertEqual(self.canvas.background, background)

    def test_select_all(self):
        """Test that a selection is created for the entire document."""
        from PySide6.QtCore import QRect
        self.canvas.select_all()
        self.assertIsNotNone(self.canvas.selection_shape)
        self.assertEqual(self.canvas.selection_shape.boundingRect(), QRect(0, 0, self.canvas.document.width, self.canvas.document.height))

    def test_select_none(self):
        """Test that the selection is cleared."""
        self.canvas.select_all()
        self.assertIsNotNone(self.canvas.selection_shape)
        self.canvas.select_none()
        self.assertIsNone(self.canvas.selection_shape)

    def test_invert_selection(self):
        """Test that the selection is inverted correctly."""
        from PySide6.QtGui import QPainterPath
        from PySide6.QtCore import QRect

        # Create a selection that covers the top-left quadrant
        rect = QRect(0, 0, 50, 50)
        path = QPainterPath()
        path.addRect(rect)
        self.canvas.selection_shape = path

        # Invert the selection
        self.canvas.invert_selection()

        # Check that a point inside the original selection is now outside
        self.assertFalse(self.canvas.selection_shape.contains(QPoint(25, 25)))

        # Check that a point outside the original selection is now inside
        self.assertTrue(self.canvas.selection_shape.contains(QPoint(75, 75)))

    def test_get_doc_coords(self):
        """Test that canvas coordinates are correctly converted to document coordinates."""
        self.canvas.zoom = 2.0
        self.canvas.x_offset = 0
        self.canvas.y_offset = 0

        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        doc_width_scaled = self.canvas.document.width * self.canvas.zoom
        doc_height_scaled = self.canvas.document.height * self.canvas.zoom
        x_offset = (canvas_width - doc_width_scaled) / 2
        y_offset = (canvas_height - doc_height_scaled) / 2

        # Test the center point
        canvas_center = QPoint(canvas_width / 2, canvas_height / 2)
        doc_center = self.canvas.get_doc_coords(canvas_center)
        self.assertEqual(doc_center, QPoint(self.canvas.document.width / 2, self.canvas.document.height / 2))

    def test_get_canvas_coords(self):
        """Test that document coordinates are correctly converted to canvas coordinates."""
        self.canvas.zoom = 2.0
        self.canvas.x_offset = 0
        self.canvas.y_offset = 0

        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        doc_width_scaled = self.canvas.document.width * self.canvas.zoom
        doc_height_scaled = self.canvas.document.height * self.canvas.zoom
        x_offset = (canvas_width - doc_width_scaled) / 2
        y_offset = (canvas_height - doc_height_scaled) / 2

        # Test the center point
        doc_center = QPoint(self.canvas.document.width / 2, self.canvas.document.height / 2)
        canvas_center = self.canvas.get_canvas_coords(doc_center)
        self.assertEqual(canvas_center, QPoint(canvas_width / 2, canvas_height / 2))

    def test_mouse_press_event(self):
        """Test that the correct tool's mousePressEvent is called."""
        from unittest.mock import Mock
        mock_tool = Mock()
        self.canvas.current_tool = mock_tool

        event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.canvas.mousePressEvent(event)

        mock_tool.mousePressEvent.assert_called_once()

    def test_mouse_move_event(self):
        """Test that the correct tool's mouseMoveEvent is called and cursor position is updated."""
        from unittest.mock import Mock
        mock_tool = Mock()
        self.canvas.current_tool = mock_tool

        event = QMouseEvent(QMouseEvent.Type.MouseMove, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.canvas.mouseMoveEvent(event)

        mock_tool.mouseMoveEvent.assert_called_once()
        self.assertNotEqual(self.canvas.cursor_doc_pos, QPoint(0, 0))

    def test_mouse_release_event(self):
        """Test that the correct tool's mouseReleaseEvent is called."""
        from unittest.mock import Mock
        mock_tool = Mock()
        self.canvas.current_tool = mock_tool

        event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.canvas.mouseReleaseEvent(event)

        mock_tool.mouseReleaseEvent.assert_called_once()

    def test_wheel_event(self):
        """Test that the zoom level and offsets are updated correctly."""
        from PySide6.QtGui import QWheelEvent

        initial_zoom = self.canvas.zoom
        initial_x_offset = self.canvas.x_offset
        initial_y_offset = self.canvas.y_offset

        # Zoom in
        event_in = QWheelEvent(
            QPoint(50, 50), QPoint(50, 50), QPoint(0, 120), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        self.canvas.wheelEvent(event_in)

        self.assertGreater(self.canvas.zoom, initial_zoom)
        self.assertNotEqual(self.canvas.x_offset, initial_x_offset)
        self.assertNotEqual(self.canvas.y_offset, initial_y_offset)

        # Zoom out
        event_out = QWheelEvent(
            QPoint(50, 50), QPoint(50, 50), QPoint(0, -120), QPoint(0, -120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        self.canvas.wheelEvent(event_out)

        self.assertAlmostEqual(self.canvas.zoom, initial_zoom)
