import pytest
from PySide6.QtGui import QImage, QColor, QPainter, QPainterPath
from PySide6.QtCore import QPoint, QRect, QSize
from portal.drawing import Drawing
from portal.layer import Layer

@pytest.fixture
def drawing():
    """Returns a Drawing instance."""
    return Drawing()

@pytest.fixture
def image():
    """Returns a blank QImage."""
    return QImage(100, 100, QImage.Format_ARGB32)

def test_draw_brush(drawing, image):
    """Test that the correct brush is drawn at the specified point."""
    painter = QPainter(image)
    point = QPoint(50, 50)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 10
    painter.setPen(QColor("red"))

    drawing.draw_brush(painter, point, doc_size, brush_type, width, False, False)
    painter.end()

    # Check that a pixel in the center of the brush is colored
    assert image.pixelColor(50, 50) == QColor("red")

def test_erase_brush(drawing, image):
    """Test that the correct brush is used to erase at the specified point."""
    # Fill the image with red first
    image.fill(QColor("red"))

    painter = QPainter(image)
    point = QPoint(50, 50)
    doc_size = QSize(100, 100)
    width = 10

    drawing.erase_brush(painter, point, doc_size, width, False, False)
    painter.end()

    # Check that a pixel in the center of the erased area is transparent
    assert image.pixelColor(50, 50) == QColor(0, 0, 0, 0)

def test_draw_line_with_brush(drawing, image):
    """Test that a line is drawn correctly using the selected brush."""
    painter = QPainter(image)
    start_point = QPoint(10, 10)
    end_point = QPoint(90, 90)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 5
    painter.setPen(QColor("blue"))

    drawing.draw_line_with_brush(painter, start_point, end_point, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a point along the line
    assert image.pixelColor(50, 50) == QColor("blue")

def test_draw_rect(drawing, image):
    """Test that a rectangle is drawn correctly."""
    painter = QPainter(image)
    rect = QRect(20, 20, 60, 60)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 1
    painter.setPen(QColor("green"))

    drawing.draw_rect(painter, rect, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a corner of the rectangle
    assert image.pixelColor(20, 20) == QColor("green")

def test_draw_ellipse(drawing, image):
    """Test that an ellipse is drawn correctly."""
    painter = QPainter(image)
    rect = QRect(20, 20, 60, 60)
    doc_size = QSize(100, 100)
    brush_type = "Circular"
    width = 1
    painter.setPen(QColor("purple"))

    drawing.draw_ellipse(painter, rect, doc_size, brush_type, width, False, False)
    painter.end()

    # Check a point on the ellipse's circumference
    assert image.pixelColor(50, 20).alpha() != 0

def test_flood_fill(drawing):
    """Test that the flood_fill algorithm correctly fills the area."""
    layer = Layer(100, 100, "Test Layer")
    # Create a black square to be filled
    for x in range(40, 60):
        for y in range(40, 60):
            layer.image.setPixelColor(x, y, QColor("black"))

    fill_pos = QPoint(50, 50)
    fill_color = QColor("yellow")

    drawing.flood_fill(layer, fill_pos, fill_color, None)

    # Check that the center of the square is now yellow
    assert layer.image.pixelColor(50, 50) == fill_color
    # Check that a point outside the square is not yellow
    assert layer.image.pixelColor(30, 30) != fill_color
