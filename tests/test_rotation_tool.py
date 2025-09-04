import pytest
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QImage, QPainterPath, QColor, QPainter
from PySide6.QtTest import QTest

from portal.core.document import Document
from portal.tools.rotatetool import RotateTool
from portal.core.command import RotateCommand
from portal.ui.canvas import Canvas


class MockCanvas(Canvas):
    def __init__(self, doc):
        # We need to properly initialize the Canvas, which requires an app object.
        # For this test, we can create a mock app object.
        class MockApp:
            def __init__(self):
                self.drawing_context = self
                self.pen_width = 1
                self.pen_color = Qt.black
                self.brush_type = "Circular"
                self.mirror_x = False
                self.mirror_y = False

        super().__init__(MockApp(), None)
        self.document = doc

    def update(self):
        pass


class MockTool(RotateTool):
    command_generated = Signal(object)


@pytest.fixture
def doc():
    doc = Document(20, 20)
    doc.layer_manager.add_layer("Layer 1")
    # Use a pattern instead of a solid color to make rotation detectable
    painter = QPainter(doc.layer_manager.active_layer.image)
    painter.fillRect(0, 0, 10, 10, Qt.red)
    painter.fillRect(10, 10, 10, 10, Qt.blue)
    painter.end()
    return doc


@pytest.fixture
def canvas(doc, qtbot):
    canvas = MockCanvas(doc)
    qtbot.addWidget(canvas)
    return canvas


def test_rotate_tool_no_selection(canvas, qtbot):
    tool = MockTool(canvas)
    canvas.tool = tool
    before_image = canvas.document.layer_manager.active_layer.image.copy()

    def execute_command(cmd):
        if isinstance(cmd, RotateCommand):
            cmd.execute()

    tool.command_generated.connect(execute_command)

    # Simulate a drag that results in a 90-degree rotation
    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    QTest.mouseMove(canvas, QPoint(10, 0))
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, QPoint(10, 0))

    after_image = canvas.document.layer_manager.active_layer.image

    assert after_image != before_image
    # A 90-degree rotation of the top-left red square should move it to the top-right
    assert after_image.pixelColor(1, 1) == QColor(Qt.transparent) # Original top-left is now empty
    assert after_image.pixelColor(18, 1).red() > 200 # New top-right is now red


def test_rotate_command_undo_redo(doc):
    before_image = doc.layer_manager.active_layer.image.copy()

    # Create a command for a 90-degree rotation
    command = RotateCommand(
        layer=doc.layer_manager.active_layer,
        before_rotate_image=before_image,
        rotated_image=None, # Not used in no-selection case
        angle=90,
        center=before_image.rect().center(),
        selection=None
    )

    command.execute()
    after_image = doc.layer_manager.active_layer.image.copy()
    assert after_image != before_image

    command.undo()
    assert doc.layer_manager.active_layer.image == before_image

    command.execute() # Redo
    assert doc.layer_manager.active_layer.image == after_image
