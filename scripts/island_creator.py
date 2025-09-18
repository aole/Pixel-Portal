"""Generate stylised island maps on a fresh layer.

This script procedurally creates an "island" layer using a handful of user
controls exposed through the scripting dialog.  It keeps the palette to six
readable colours (deep water, shallow water, beaches, grasslands, highlands,
and optional deserts) while shaping large landmasses, coastal shelves, and small
islets.  The result is a quick starting point for overworld mock-ups or tile-set
experiments.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List

from PySide6.QtGui import QColor

# Define script parameters for the dialog UI
params = [
    {
        "name": "large_islands",
        "type": "number",
        "label": "Large islands",
        "default": 2,
        "min": 1,
        "max": 4,
    },
    {
        "name": "water_percentage",
        "type": "slider",
        "label": "Water coverage (%)",
        "default": 55,
        "min": 30,
        "max": 80,
    },
    {
        "name": "beach_size",
        "type": "slider",
        "label": "Beach size",
        "default": 12,
        "min": 1,
        "max": 30,
    },
    {
        "name": "desert_density",
        "type": "slider",
        "label": "Desert density",
        "default": 30,
        "min": 0,
        "max": 100,
    },
    {
        "name": "random_seed",
        "type": "number",
        "label": "Random seed (0 = random)",
        "default": 0,
        "min": 0,
        "max": 999_999,
    },
]


@dataclass
class IslandBlob:
    """Simple container describing an island influence zone."""

    cx: float
    cy: float
    rx: float
    ry: float
    strength: float


def _normalise_parameter(value: float, minimum: float, maximum: float, fallback: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))


def _prepare_islands(rng: random.Random, count: int) -> List[IslandBlob]:
    """Create a collection of large and small island blobs."""

    islands: List[IslandBlob] = []

    # Large landmasses – these carry the majority of the terrain height.
    for _ in range(count):
        rx = rng.uniform(0.18, 0.3)
        ry = rng.uniform(0.18, 0.3)
        cx = rng.uniform(rx, 1.0 - rx)
        cy = rng.uniform(ry, 1.0 - ry)
        strength = rng.uniform(0.9, 1.25)
        islands.append(IslandBlob(cx, cy, rx, ry, strength))

    # Sprinkle a handful of smaller islets to break up the silhouette.
    small_count = max(3, count * 3)
    for _ in range(small_count):
        rx = rng.uniform(0.05, 0.12)
        ry = rx * rng.uniform(0.6, 1.4)
        cx = rng.uniform(rx, 1.0 - rx)
        cy = rng.uniform(ry, 1.0 - ry)
        strength = rng.uniform(0.45, 0.75)
        islands.append(IslandBlob(cx, cy, rx, ry, strength))

    # A final pass of micro-atolls hugs the coastlines for visual interest.
    reef_count = max(6, count * 6)
    for _ in range(reef_count):
        rx = rng.uniform(0.02, 0.05)
        ry = rx * rng.uniform(0.7, 1.3)
        cx = rng.uniform(rx, 1.0 - rx)
        cy = rng.uniform(ry, 1.0 - ry)
        strength = rng.uniform(0.2, 0.35)
        islands.append(IslandBlob(cx, cy, rx, ry, strength))

    return islands


def _generate_height(
    islands: List[IslandBlob],
    nx: float,
    ny: float,
    rng_offsets: tuple[float, float, float, float, float, float],
    water_bias: float,
) -> float:
    """Compute a pseudo-height value for the given normalised coordinate."""

    low_freq_offset_x, low_freq_offset_y, hi_freq_offset_a, hi_freq_offset_b, *_ = rng_offsets

    # Base influence from island blobs (radial falloff creates coastlines).
    height_value = -0.35
    for blob in islands:
        dx = (nx - blob.cx) / blob.rx
        dy = (ny - blob.cy) / blob.ry
        distance = math.hypot(dx, dy)
        if distance < 1.0:
            contribution = (1.0 - distance * distance) * blob.strength
            if contribution > height_value:
                height_value = contribution

    # Layer a couple of sine waves for smooth continental undulation.
    low_frequency = (
        math.sin((nx + low_freq_offset_x) * 3.2)
        + math.cos((ny + low_freq_offset_y) * 3.2)
    ) * 0.12
    high_frequency = (
        math.sin(((nx - ny) + hi_freq_offset_a) * 7.4)
        + math.cos(((nx + ny) + hi_freq_offset_b) * 7.4)
    ) * 0.05

    height_value += low_frequency + high_frequency

    # Encourage water around the very edges of the canvas.
    edge_distance = min(nx, 1.0 - nx, ny, 1.0 - ny)
    height_value += (edge_distance - 0.22) * 0.55

    # Apply user-controlled water bias (higher percentage pushes the sea level up).
    height_value -= water_bias

    return max(-0.6, min(1.2, height_value))


def _compute_dryness(
    nx: float,
    ny: float,
    height_value: float,
    rng_offsets: tuple[float, float, float, float, float, float],
) -> float:
    """Approximate a dryness value used for desert placement."""

    *_, dryness_offset_x, dryness_offset_y = rng_offsets

    latitude = abs(ny - 0.5)
    dryness = 0.45
    dryness += (math.sin((nx + dryness_offset_x) * 4.1) + math.cos((ny + dryness_offset_y) * 4.1)) * 0.12
    dryness += max(0.0, height_value - 0.6) * 0.55
    dryness += (0.5 - latitude) * 0.22

    return max(0.0, min(1.0, dryness))


def main(api, values):
    large_islands = int(_normalise_parameter(values.get("large_islands"), 1, 4, 2))
    water_percentage = _normalise_parameter(values.get("water_percentage"), 30, 80, 55)
    beach_size = _normalise_parameter(values.get("beach_size"), 1, 30, 12)
    desert_density = _normalise_parameter(values.get("desert_density"), 0, 100, 30)

    seed_value = values.get("random_seed", 0)
    try:
        seed_value = int(seed_value)
    except (TypeError, ValueError):
        seed_value = 0

    rng = random.Random()
    if seed_value != 0:
        rng.seed(seed_value)
    else:
        rng.seed()

    new_layer = api.create_layer("Generated Islands")
    if not new_layer:
        api.show_message_box("Script Error", "Could not create a new layer.")
        return

    beach_band = 0.04 + (beach_size / 200.0)
    desert_threshold = max(0.25, min(0.85, 0.75 - desert_density / 220.0))
    desert_active = desert_density > 0.0
    water_bias = (water_percentage / 100.0) - 0.5

    # Palette (5 to 6 colours total depending on desert activation).
    deep_water = QColor("#12355b")
    shallow_water = QColor("#3a86ff")
    beach_color = QColor("#f5deb3")
    grass_color = QColor("#7bc96f")
    highland_color = QColor("#8f6a4f")
    desert_color = QColor("#edc16b")

    islands = _prepare_islands(rng, large_islands)
    rng_offsets = tuple(rng.uniform(0.0, 1000.0) for _ in range(6))

    def draw_islands(image):
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return

        width_divisor = max(1, width - 1)
        height_divisor = max(1, height - 1)

        for y in range(height):
            ny = y / height_divisor
            for x in range(width):
                nx = x / width_divisor
                height_value = _generate_height(islands, nx, ny, rng_offsets, water_bias)
                dryness = _compute_dryness(nx, ny, height_value, rng_offsets)

                if height_value < 0.0:
                    color = deep_water
                elif height_value < 0.18:
                    color = shallow_water
                elif height_value < 0.18 + beach_band:
                    color = beach_color
                elif height_value < 0.62:
                    color = grass_color
                else:
                    if desert_active and dryness > desert_threshold:
                        color = desert_color
                    else:
                        color = highland_color

                image.setPixelColor(x, y, color)

    api.modify_layer(new_layer, draw_islands)
