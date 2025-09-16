"""Script to promote partially transparent pixels to full opacity."""

# Define the parameters for the script
params = [
    {
        'name': 'include_fully_transparent',
        'type': 'checkbox',
        'label': 'Affect fully transparent pixels',
        'default': False,
    }
]


def main(api, values):
    """Entry point for the script."""
    include_all = values.get('include_fully_transparent', False)

    active_layer = api.get_active_layer()
    if active_layer is None:
        api.show_message_box("Script Error", "No active layer is selected.")
        return

    def promote_pixels(image):
        if not image.hasAlphaChannel():
            return

        width = image.width()
        height = image.height()

        for y in range(height):
            for x in range(width):
                color = image.pixelColor(x, y)
                alpha = color.alpha()

                if alpha == 255:
                    continue
                if alpha == 0 and not include_all:
                    continue

                color.setAlpha(255)
                image.setPixelColor(x, y, color)

    api.modify_layer(active_layer, promote_pixels)
