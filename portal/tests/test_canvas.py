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
        self.drawing_context = DrawingContext()
        self.canvas = Canvas(self.drawing_context)
        # Set initial properties, as the App would via signal/slot connections
        self.canvas.set_document_size(QSize(100, 100))
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
