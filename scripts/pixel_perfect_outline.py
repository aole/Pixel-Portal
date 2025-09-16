from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# Define the parameters for the script
params = [
    {
        'name': 'outline_width',
        'type': 'number',
        'label': 'Outline Width',
        'default': 1,
        'min': 1,
        'max': 16,
    },
    {
        'name': 'outline_color',
        'type': 'color',
        'label': 'Outline Color',
        'default': '#000000',
    },
    {
        'name': 'remove_background',
        'type': 'checkbox',
        'label': 'Remove Background',
        'default': False,
    },
]


def _coerce_color(value):
    if isinstance(value, QColor):
        return QColor(value)
    color = QColor(value)
    if not color.isValid():
        return QColor('black')
    return color


def _has_visible_pixels(image):
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                return True
    return False


def main(api, values):
    get_active_layer = getattr(api, 'get_active_layer', None)
    layer = get_active_layer() if callable(get_active_layer) else None
    if layer is None:
        layers = api.get_all_layers()
        layer = layers[-1] if layers else None

    if layer is None:
        api.show_message_box('Script Error', 'No active layer is available.')
        return

    outline_width = values.get('outline_width', 1)
    try:
        outline_width = int(outline_width)
    except (TypeError, ValueError):
        outline_width = 1
    outline_width = max(1, outline_width)

    outline_color = _coerce_color(values.get('outline_color', QColor('black')))
    remove_background = bool(values.get('remove_background', False))

    if not _has_visible_pixels(layer.image):
        api.show_message_box(
            'Pixel Perfect Outline',
            'The active layer does not contain any visible pixels to outline.',
        )
        return

    neighbor_offsets = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]

    target_rgba = outline_color.rgba()

    def draw_outline(image):
        original = image.copy()
        width = original.width()
        height = original.height()

        content_mask = set()
        for y in range(height):
            for x in range(width):
                if original.pixelColor(x, y).alpha() > 0:
                    content_mask.add((x, y))

        if not content_mask:
            return

        existing_outline_pixels = set()
        for (x, y) in content_mask:
            color = original.pixelColor(x, y)
            if color.rgba() != target_rgba:
                continue
            for dx, dy in neighbor_offsets:
                nx = x + dx
                ny = y + dy
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    existing_outline_pixels.add((x, y))
                    break
                if (nx, ny) not in content_mask:
                    existing_outline_pixels.add((x, y))
                    break

        core_pixels = content_mask.difference(existing_outline_pixels)
        if not core_pixels:
            core_pixels = content_mask

        new_outline_pixels = set()
        for (x, y) in core_pixels:
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx == 0 and dy == 0:
                        continue
                    if max(abs(dx), abs(dy)) > outline_width:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if (nx, ny) not in content_mask:
                            new_outline_pixels.add((nx, ny))

        if remove_background:
            image.fill(Qt.transparent)

        for (x, y) in new_outline_pixels:
            image.setPixelColor(x, y, outline_color)

        for (x, y) in existing_outline_pixels:
            image.setPixelColor(x, y, outline_color)

    api.modify_layer(layer, draw_outline)
