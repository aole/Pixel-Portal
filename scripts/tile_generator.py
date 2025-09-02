import math
from PySide6.QtGui import QPainter, QPolygonF, QColor
from PySide6.QtCore import QPointF

def draw_isometric_tile(painter, size):
    """Draws an isometric tile."""
    half_size = size / 2
    polygon = QPolygonF([
        QPointF(half_size, 0),
        QPointF(size, half_size),
        QPointF(half_size, size),
        QPointF(0, half_size)
    ])
    painter.drawPolygon(polygon)

def draw_hex_tile(painter, size):
    """Draws a hexagonal tile."""
    half_size = size / 2
    quarter_size = size / 4
    polygon = QPolygonF([
        QPointF(quarter_size, 0),
        QPointF(size - quarter_size, 0),
        QPointF(size, half_size),
        QPointF(size - quarter_size, size),
        QPointF(quarter_size, size),
        QPointF(0, half_size)
    ])
    painter.drawPolygon(polygon)

# Get user input
tile_type = api.get_item("Choose tile type", "Select the type of tile to generate:", ["Isometric", "Hexagonal"])
if tile_type:
    size_text = api.get_text("Enter size", "Enter the size of the tile:")
    if size_text:
        try:
            size = int(size_text)
            if size <= 0:
                raise ValueError("Size must be a positive integer.")

            # Create a new layer
            new_layer = api.create_layer(f"{tile_type} Tile")

            if new_layer:
                # Draw the tile
                painter = QPainter(new_layer.image)
                painter.setBrush(QColor(128, 128, 128, 255))  # Gray fill
                painter.setPen(QColor(0, 0, 0, 255))      # Black outline

                if tile_type == "Isometric":
                    draw_isometric_tile(painter, size)
                elif tile_type == "Hexagonal":
                    draw_hex_tile(painter, size)

                painter.end()

                api.show_message_box("Script Finished", f"{tile_type} tile created.")
            else:
                api.show_message_box("Script Error", "Could not create a new layer.")
        except ValueError as e:
            api.show_message_box("Script Error", f"Invalid size: {e}")
