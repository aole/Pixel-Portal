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

# Define the parameters for the script
params = [
    {'name': 'tile_type', 'type': 'choice', 'label': 'Tile Type', 'choices': ['Isometric', 'Hexagonal'], 'default': 'Isometric'},
    {'name': 'size', 'type': 'number', 'label': 'Tile Size', 'default': 32, 'min': 4, 'max': 256},
    {'name': 'fill_color', 'type': 'color', 'label': 'Fill Color', 'default': '#808080'},
    {'name': 'outline_color', 'type': 'color', 'label': 'Outline Color', 'default': '#000000'},
]

# Get user input using the new dialog
values = api.get_parameters(params)

if values:
    tile_type = values['tile_type']
    size = values['size']
    fill_color = values['fill_color']
    outline_color = values['outline_color']

    # Create a new layer
    new_layer = api.create_layer(f"{tile_type} Tile")

    if new_layer:
        # Draw the tile
        painter = QPainter(new_layer.image)
        painter.setBrush(fill_color)
        painter.setPen(outline_color)

        if tile_type == "Isometric":
            draw_isometric_tile(painter, size)
        elif tile_type == "Hexagonal":
            draw_hex_tile(painter, size)

        painter.end()

        api.show_message_box("Script Finished", f"{tile_type} tile created.")
    else:
        api.show_message_box("Script Error", "Could not create a new layer.")
