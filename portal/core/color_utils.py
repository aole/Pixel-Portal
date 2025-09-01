import math

def find_closest_color(rgb_color, palette):
    """
    Finds the closest color in the palette to the given RGB color.
    """
    r1, g1, b1, _ = rgb_color
    closest_distance = float('inf')
    closest_color = None

    for palette_color in palette:
        r2, g2, b2, _ = palette_color
        distance = math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)

        if distance < closest_distance:
            closest_distance = distance
            closest_color = palette_color

    return closest_color
