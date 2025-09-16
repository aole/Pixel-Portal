"""Script to threshold partially transparent pixels to either full opacity or transparency."""

# Define the parameters for the script
params = [
    {
        'name': 'transparency_threshold',
        'type': 'slider',
        'label': 'Transparency threshold (%)',
        'default': 25,
        'min': 0,
        'max': 100,
    }
]


def main(api, values):
    """Entry point for the script."""
    threshold_percent = values.get('transparency_threshold', 25)
    try:
        threshold_percent = int(threshold_percent)
    except (TypeError, ValueError):
        threshold_percent = 25
    threshold_percent = max(0, min(100, threshold_percent))

    active_layer = api.get_active_layer()
    if active_layer is None:
        api.show_message_box("Script Error", "No active layer is selected.")
        return

    def promote_pixels(image):
        if not image.hasAlphaChannel():
            return

        width = image.width()
        height = image.height()
        threshold_scaled = threshold_percent * 255

        for y in range(height):
            for x in range(width):
                color = image.pixelColor(x, y)
                alpha = color.alpha()
                new_alpha = 255 if alpha * 100 >= threshold_scaled else 0
                if new_alpha == alpha:
                    continue
                color.setAlpha(new_alpha)
                image.setPixelColor(x, y, color)

    api.modify_layer(active_layer, promote_pixels)
