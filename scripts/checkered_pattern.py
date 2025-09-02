from PySide6.QtGui import QPainter

# Get user input
color1 = api.get_color("Choose the first color")
if color1:
    color2 = api.get_color("Choose the second color")
    if color2:
        size_text = api.get_text("Enter size", "Enter the size of the squares:")
        if size_text:
            try:
                size = int(size_text)
                if size <= 0:
                    raise ValueError("Size must be a positive integer.")

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
            except ValueError as e:
                api.show_message_box("Script Error", f"Invalid size: {e}")
