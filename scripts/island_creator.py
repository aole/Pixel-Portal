"""Island layer generator script for Pixel-Portal."""

import math
import random
from typing import Dict, List, Tuple

from PySide6.QtGui import QColor

# Define the parameters for the script
params = [
    {
        'name': 'seed',
        'type': 'number',
        'label': 'Random Seed',
        'default': 42,
        'min': 0,
        'max': 999999,
    },
    {
        'name': 'large_islands',
        'type': 'number',
        'label': 'Large Islands',
        'default': 2,
        'min': 1,
        'max': 4,
    },
    {
        'name': 'water_percentage',
        'type': 'number',
        'label': 'Water Coverage %',
        'default': 45,
        'min': 20,
        'max': 80,
    },
    {
        'name': 'include_beach',
        'type': 'checkbox',
        'label': 'Include Beaches',
        'default': True,
    },
    {
        'name': 'include_desert',
        'type': 'checkbox',
        'label': 'Include Desert Regions',
        'default': False,
    },
    {
        'name': 'include_mountains',
        'type': 'checkbox',
        'label': 'Include Mountain Peaks',
        'default': True,
    },
]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _make_noise_grid(rng: random.Random, size: int) -> List[List[float]]:
    return [[rng.random() for _ in range(size + 1)] for _ in range(size + 1)]


def _sample_noise(grid: List[List[float]], x_norm: float, y_norm: float) -> float:
    rows = len(grid)
    if rows == 0:
        return 0.0
    cols = len(grid[0])
    if cols == 0:
        return 0.0

    max_x = cols - 1
    max_y = rows - 1

    fx = _clamp(x_norm, 0.0, 0.9999) * max_x
    fy = _clamp(y_norm, 0.0, 0.9999) * max_y

    x0 = int(fx)
    y0 = int(fy)
    x1 = min(x0 + 1, max_x)
    y1 = min(y0 + 1, max_y)

    sx = fx - x0
    sy = fy - y0

    top = grid[y0][x0] * (1.0 - sx) + grid[y0][x1] * sx
    bottom = grid[y1][x0] * (1.0 - sx) + grid[y1][x1] * sx
    return top * (1.0 - sy) + bottom * sy


def _prepare_colors(include_beach: bool, include_mountains: bool) -> Dict[str, QColor]:
    return {
        'deep_water': QColor('#0b3954'),
        'shallow_water': QColor('#1f78c1'),
        'shore': QColor('#f3d9b1') if include_beach else QColor('#93d3b1'),
        'lowland': QColor('#79c267'),
        'midland': QColor('#3f7c4a'),
        'desert': QColor('#d9a066'),
        'peaks': QColor('#b8a57a') if include_mountains else QColor('#567d68'),
    }


def _compute_thresholds(land_fraction: float) -> Tuple[float, float, float, float, float]:
    base = 0.42 - (land_fraction - 0.5) * 0.25
    base = _clamp(base, 0.25, 0.6)
    deep = base * 0.55
    shallow = base
    shore = min(0.85, base + 0.08)
    lowland = min(0.93, base + 0.26)
    feature = min(0.98, base + 0.45)
    return deep, shallow, shore, lowland, feature


def _generate_island_shapes(
    width: int,
    height: int,
    rng: random.Random,
    count: int,
    land_fraction: float,
    include_desert: bool,
):
    shapes = []
    margin_x = width * 0.15
    margin_y = height * 0.15
    base_radius = min(width, height) * (0.28 + land_fraction * 0.4)

    for _ in range(count):
        cx = rng.uniform(margin_x, width - margin_x)
        cy = rng.uniform(margin_y, height - margin_y)
        radius = base_radius * rng.uniform(0.85, 1.25)
        aspect = rng.uniform(0.75, 1.35)
        dryness = rng.uniform(0.65, 1.0) if include_desert and rng.random() < 0.6 else rng.uniform(0.2, 0.6)

        shapes.append(
            {
                'x': cx,
                'y': cy,
                'radius': max(4.0, radius),
                'aspect': aspect,
                'weight': rng.uniform(0.85, 1.0),
                'dryness': dryness,
                'power': rng.uniform(1.6, 1.9),
            }
        )

        for _ in range(rng.randint(1, 3)):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            distance = radius * rng.uniform(0.45, 0.95)
            sub_radius = radius * rng.uniform(0.28, 0.5)
            sub_cx = _clamp(cx + math.cos(angle) * distance, 0.0, width - 1.0)
            sub_cy = _clamp(cy + math.sin(angle) * distance, 0.0, height - 1.0)
            sub_dryness = _clamp(dryness * 0.6 + rng.uniform(0.0, 0.4), 0.0, 1.0)

            shapes.append(
                {
                    'x': sub_cx,
                    'y': sub_cy,
                    'radius': max(3.0, sub_radius),
                    'aspect': rng.uniform(0.7, 1.4),
                    'weight': rng.uniform(0.45, 0.75),
                    'dryness': sub_dryness,
                    'power': rng.uniform(1.2, 1.5),
                }
            )

    return shapes


def _sample_elevation_and_dryness(x: int, y: int, shapes) -> Tuple[float, float]:
    elevation = 0.0
    dryness = 0.0
    for shape in shapes:
        radius = shape['radius']
        if radius <= 0.0:
            continue
        dx = (x - shape['x']) / radius
        dy = (y - shape['y']) / (radius * shape['aspect'])
        dist = math.hypot(dx, dy)
        if dist >= 1.2:
            continue
        base = (1.2 - dist) / 1.2
        base = max(0.0, base) ** shape['power']
        contribution = base * shape['weight']
        elevation = max(elevation, contribution)
        dryness = max(dryness, contribution * shape['dryness'])
    return _clamp(elevation, 0.0, 1.0), _clamp(dryness, 0.0, 1.0)


def _pick_color(
    elevation: float,
    dryness: float,
    thresholds: Tuple[float, float, float, float, float],
    colors: Dict[str, QColor],
    include_desert: bool,
) -> QColor:
    deep, shallow, shore, lowland, feature = thresholds

    if elevation <= deep:
        return colors['deep_water']
    if elevation <= shallow:
        return colors['shallow_water']
    if elevation <= shore:
        return colors['shore']
    if elevation <= lowland:
        return colors['lowland']
    if elevation <= feature:
        if include_desert and dryness > 0.55:
            return colors['desert']
        return colors['midland']
    return colors['peaks']


def _draw_islands(
    image,
    island_count: int,
    water_percentage: float,
    include_beach: bool,
    include_desert: bool,
    include_mountains: bool,
    seed: int,
):
    width = image.width()
    height = image.height()
    if width == 0 or height == 0:
        return

    rng = random.Random(seed)
    land_fraction = _clamp(1.0 - water_percentage / 100.0, 0.1, 0.9)
    shapes = _generate_island_shapes(width, height, rng, island_count, land_fraction, include_desert)

    base_noise = _make_noise_grid(rng, 48)
    detail_noise = _make_noise_grid(rng, 32)
    dryness_noise = _make_noise_grid(rng, 32)

    thresholds = _compute_thresholds(land_fraction)
    colors = _prepare_colors(include_beach, include_mountains)

    max_x = max(width - 1, 1)
    max_y = max(height - 1, 1)

    for y in range(height):
        y_norm = y / max_y
        for x in range(width):
            x_norm = x / max_x
            elevation, dryness_strength = _sample_elevation_and_dryness(x, y, shapes)

            edge_dx = x_norm - 0.5
            edge_dy = y_norm - 0.5
            edge_distance = math.hypot(edge_dx, edge_dy)
            elevation *= 1.0 - 0.35 * edge_distance
            elevation -= edge_distance * 0.12
            elevation = _clamp(elevation, 0.0, 1.0)

            scale = 0.7 + land_fraction * 0.6
            bias = (0.5 - land_fraction) * 0.35
            elevation = _clamp(elevation * scale - bias, 0.0, 1.0)

            noise = (_sample_noise(base_noise, x_norm, y_norm) - 0.5) * (0.25 + land_fraction * 0.1)
            detail = (
                _sample_noise(detail_noise, x_norm * 0.75 + y_norm * 0.25, y_norm * 0.75 + x_norm * 0.25) - 0.5
            ) * 0.18
            elevation = _clamp(elevation + noise + detail, 0.0, 1.0)

            dryness_noise_value = _sample_noise(dryness_noise, x_norm, y_norm)

            dryness = dryness_strength
            if include_desert:
                dryness *= 1.0 - elevation * 0.4
                dryness = _clamp(dryness + (dryness_noise_value - 0.45) * 0.7, 0.0, 1.0)
            else:
                dryness = _clamp(dryness * 0.3 + dryness_noise_value * 0.25, 0.0, 0.6)

            color = _pick_color(elevation, dryness, thresholds, colors, include_desert)
            image.setPixelColor(x, y, color)


def main(api, values):
    island_count = int(values.get('large_islands', 2))
    island_count = int(_clamp(island_count, 1, 4))

    water_percentage = float(values.get('water_percentage', 45))
    water_percentage = _clamp(water_percentage, 0, 100)

    include_beach = bool(values.get('include_beach', True))
    include_desert = bool(values.get('include_desert', False))
    include_mountains = bool(values.get('include_mountains', True))

    seed = values.get('seed', 42)
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        seed = 42

    new_layer = api.create_layer('Island Map')
    if not new_layer:
        api.show_message_box('Script Error', 'Could not create a new layer.')
        return

    def draw(image):
        _draw_islands(
            image,
            island_count=island_count,
            water_percentage=water_percentage,
            include_beach=include_beach,
            include_desert=include_desert,
            include_mountains=include_mountains,
            seed=seed,
        )

    api.modify_layer(new_layer, draw)
