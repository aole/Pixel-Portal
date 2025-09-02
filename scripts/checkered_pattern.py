from PySide6.QtGui import QPainter, QColor

# Define the parameters for the script
params = [
    {'name': 'color1', 'type': 'color', 'label': 'First Color', 'default': '#ff0000'},
    {'name': 'color2', 'type': 'color', 'label': 'Second Color', 'default': '#0000ff'},
    {'name': 'size', 'type': 'number', 'label': 'Square Size', 'default': 10, 'min': 1, 'max': 100},
]

# Get user input using the new dialog
values = api.get_parameters(params)

if values:
    color1 = values['color1']
    color2 = values['color2']
    size = values['size']

    # Create a new layer
    new_layer = api.create_layer("Checkered Pattern")

    if new_layer:
        # Draw the checkered pattern
        painter = QPainter(new_layer.image)
        for y in range(0, new_layer.image.height(), size):
            for x in range(0, new_layer.image.width(), size):
                if (x // size) % 2 == (y // size) % 2:
                    painter.fillRect(x, y, size, size, color1)
                else:
                    painter.fillRect(x, y, size, size, color2)
        painter.end()

        api.show_message_box("Script Finished", "Checkered pattern created.")
    else:
        api.show_message_box("Script Error", "Could not create a new layer.")
