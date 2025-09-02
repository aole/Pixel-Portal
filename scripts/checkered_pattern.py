from PySide6.QtGui import QPainter

# Define the parameters for the script
params = [
    {'name': 'color1', 'type': 'color', 'label': 'First Color', 'default': '#ffffff'},
    {'name': 'color2', 'type': 'color', 'label': 'Second Color', 'default': '#000000'},
    {'name': 'size', 'type': 'number', 'label': 'Square Size', 'default': 16, 'min': 2, 'max': 128},
]

def main(api, values):
    color1 = values['color1']
    color2 = values['color2']
    size = values['size']

    # Create a new layer
    new_layer = api.create_layer("Checkered Pattern")

    if new_layer:
        # Define the drawing logic as a function
        def draw_checkers(image):
            painter = QPainter(image)
            for y in range(0, image.height(), size):
                for x in range(0, image.width(), size):
                    if (x // size) % 2 == (y // size) % 2:
                        painter.fillRect(x, y, size, size, color1)
                    else:
                        painter.fillRect(x, y, size, size, color2)
            painter.end()

        # Execute the drawing as an undoable command
        api.modify_layer(new_layer, draw_checkers)
    else:
        api.show_message_box("Script Error", "Could not create a new layer.")
