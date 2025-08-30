import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from portal.app import App
from portal.canvas import Canvas

@pytest.fixture
def app_and_canvas(qtbot):
    app = App()
    canvas = Canvas(app)
    qtbot.addWidget(canvas)
    image = QImage(10, 10, QImage.Format_ARGB32)
    image.fill(Qt.white)
    # Draw a black rectangle to create a bounded area
    for x in range(2, 8):
        image.setPixelColor(x, 2, QColor("black"))
        image.setPixelColor(x, 7, QColor("black"))
    for y in range(3, 7):
        image.setPixelColor(2, y, QColor("black"))
        image.setPixelColor(7, y, QColor("black"))
    app.document.layer_manager.layers[0].image = image
    return app, canvas

def test_bucket_tool_fill(app_and_canvas):
    app, canvas = app_and_canvas
    app.set_pen_color("#ff0000") # red

    # The bucket tool is already instantiated in the canvas
    bucket_tool = canvas.tools["Bucket"]

    # Simulate a mouse press inside the bounded area
    bucket_tool.mousePressEvent(None, QPoint(5, 5))

    # Check that the inside is filled with red
    assert app.document.layer_manager.layers[0].image.pixelColor(5, 5) == QColor("red")

    # Check that the border is still black
    assert app.document.layer_manager.layers[0].image.pixelColor(2, 5) == QColor("black")

    # Check that the outside is still white
    assert app.document.layer_manager.layers[0].image.pixelColor(0, 0) == QColor("white")
