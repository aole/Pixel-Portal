import math
from PySide6.QtGui import QPainter, QPolygonF, QColor
from PySide6.QtCore import QPointF

# Define the parameters for the script
params = [
    {'name': 'tile_type', 'type': 'choice', 'label': 'Tile Type', 'choices': ['Isometric', 'Hexagonal'], 'default': 'Isometric'},
    {'name': 'size', 'type': 'number', 'label': 'Tile Size', 'default': 32, 'min': 4, 'max': 256},
    {'name': 'fill_color', 'type': 'color', 'label': 'Fill Color', 'default': '#808080'},
    {'name': 'outline_color', 'type': 'color', 'label': 'Outline Color', 'default': '#000000'},
]

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

def main(api, values):
    tile_type = values['tile_type']
    size = values['size']
    fill_color = values['fill_color']
    outline_color = values['outline_color']

    # Create a new layer
    new_layer = api.create_layer(f"{tile_type} Tile")

    if new_layer:
        # Define the drawing logic as a function
        def draw_tile(image):
            painter = QPainter(image)
            painter.setBrush(fill_color)
            painter.setPen(outline_color)

            if tile_type == "Isometric":
                draw_isometric_tile(painter, size)
            elif tile_type == "Hexagonal":
                draw_hex_tile(painter, size)

            painter.end()

        # Execute the drawing as an undoable command
        api.modify_layer(new_layer, draw_tile)
    else:
        api.show_message_box("Script Error", "Could not create a new layer.")
