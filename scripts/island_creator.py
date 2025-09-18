"""Procedural island generator script for Pixel-Portal.

This script creates a brand-new layer and fills it with an island map that uses
between five and six terrain colors. The composition is controlled through
user-provided parameters exposed in the script dialog.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtGui import QColor


params = [
    {
        "name": "random_seed",
        "type": "number",
        "label": "Random Seed (0 = random)",
        "default": 0,
        "min": 0,
        "max": 999_999,
    },
    {
        "name": "large_islands",
        "type": "number",
        "label": "Number of Large Islands",
        "default": 2,
        "min": 1,
        "max": 4,
    },
    {
        "name": "water_percentage",
        "type": "number",
        "label": "Water Coverage (%)",
        "default": 65,
        "min": 30,
        "max": 90,
    },
    {
        "name": "include_beaches",
        "type": "checkbox",
        "label": "Include Beaches",
        "default": True,
    },
    {
        "name": "include_forests",
        "type": "checkbox",
        "label": "Include Forests",
        "default": True,
    },
    {
        "name": "include_desert",
        "type": "checkbox",
        "label": "Include Desert Regions",
        "default": True,
    },
]


# Palette limited to six distinct colors.
DEEP_WATER_COLOR = QColor("#1f3b73")
SHALLOW_WATER_COLOR = QColor("#4dbbe5")
BEACH_COLOR = QColor("#f4d58d")
GRASS_COLOR = QColor("#7ecb6f")
FOREST_COLOR = QColor("#2d6a4f")
DESERT_COLOR = QColor("#d9a441")
ROCK_COLOR = QColor("#b7c0d4")


@dataclass(slots=True)
class _IslandSpec:
    cx: float
    cy: float
    radius_x: float
    radius_y: float
    weight: float
    falloff: float
    influence: float
    cos_angle: float
    sin_angle: float


def _clamp_int(value, minimum, maximum, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _clamp_float(value, minimum, maximum, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
        return default
    if value is None:
        return default
    return bool(value)


def _random_position(limit: int, margin: float, rng: random.Random) -> float:
    if limit <= 0:
        return 0.0
    capped_margin = min(margin, limit / 2)
    low = capped_margin
    high = limit - capped_margin
    if high <= low:
        return limit / 2
    return rng.uniform(low, high)


def _generate_island_specs(
    rng: random.Random,
    count: int,
    width: int,
    height: int,
    land_ratio: float,
) -> list[_IslandSpec]:
    specs: list[_IslandSpec] = []
    size_bias = 0.22 + land_ratio * 0.45
    base_radius = max(12.0, min(width, height) * size_bias)

    margin_x = base_radius * 0.6
    margin_y = base_radius * 0.6

    for _ in range(count):
        radius_x = max(12.0, base_radius * rng.uniform(0.75, 1.25))
        radius_y = max(12.0, base_radius * rng.uniform(0.6, 1.3))
        angle = rng.random() * math.tau
        specs.append(
            _IslandSpec(
                cx=_random_position(width, margin_x, rng),
                cy=_random_position(height, margin_y, rng),
                radius_x=radius_x,
                radius_y=radius_y,
                weight=rng.uniform(0.9, 1.35),
                falloff=rng.uniform(1.6, 2.6),
                influence=rng.uniform(1.15, 1.45),
                cos_angle=math.cos(angle),
                sin_angle=math.sin(angle),
            )
        )

    # Sprinkle a few smaller islands for variety when space allows.
    if width > 32 and height > 32:
        extra_count = rng.randint(0, count * 2)
        for _ in range(extra_count):
            radius_scale = rng.uniform(0.2, 0.45)
            radius_x = max(8.0, base_radius * radius_scale)
            radius_y = max(8.0, base_radius * radius_scale * rng.uniform(0.7, 1.4))
            angle = rng.random() * math.tau
            specs.append(
                _IslandSpec(
                    cx=_random_position(width, radius_x * 1.2, rng),
                    cy=_random_position(height, radius_y * 1.2, rng),
                    radius_x=radius_x,
                    radius_y=radius_y,
                    weight=rng.uniform(0.6, 0.95),
                    falloff=rng.uniform(1.8, 3.0),
                    influence=rng.uniform(1.0, 1.35),
                    cos_angle=math.cos(angle),
                    sin_angle=math.sin(angle),
                )
            )

    return specs


def _island_contribution(x: int, y: int, spec: _IslandSpec) -> float:
    dx = x - spec.cx
    dy = y - spec.cy
    rotated_x = dx * spec.cos_angle + dy * spec.sin_angle
    rotated_y = -dx * spec.sin_angle + dy * spec.cos_angle
    nx = rotated_x / spec.radius_x
    ny = rotated_y / spec.radius_y
    distance = math.hypot(nx, ny)

    if distance >= spec.influence:
        return 0.0

    scaled = 1.0 - (distance / spec.influence)
    return spec.weight * (scaled ** spec.falloff)


def _build_height_map(
    width: int,
    height: int,
    specs: list[_IslandSpec],
    rng: random.Random,
) -> tuple[list[list[float]], list[float], float, float]:
    height_map: list[list[float]] = [[0.0] * width for _ in range(height)]
    values: list[float] = []
    min_value = float("inf")
    max_value = float("-inf")

    diag = max(1.0, math.hypot(width, height))
    freq_base = rng.uniform(1.8, 2.9) / diag
    freq_alt = rng.uniform(2.4, 3.6) / diag
    phase_one = rng.random() * math.tau
    phase_two = rng.random() * math.tau
    noise_amplitude = rng.uniform(0.08, 0.16)

    width_norm = width - 1 if width > 1 else 1
    height_norm = height - 1 if height > 1 else 1

    for y in range(height):
        row = height_map[y]
        y_norm = (y / height_norm) * 2.0 - 1.0
        for x in range(width):
            x_norm = (x / width_norm) * 2.0 - 1.0

            total = -0.3 * (x_norm * x_norm + y_norm * y_norm)
            for spec in specs:
                total += _island_contribution(x, y, spec)

            noise_term = (
                math.sin(x * freq_base + phase_one)
                + math.cos(y * freq_base + phase_two)
                + 0.5 * math.sin((x + y) * freq_alt - phase_two * 0.7)
            )
            total += noise_amplitude * noise_term

            row[x] = total
            values.append(total)
            if total < min_value:
                min_value = total
            if total > max_value:
                max_value = total

    return height_map, values, min_value, max_value


def _assign_colors(
    image,
    height_map: list[list[float]],
    values: list[float],
    min_value: float,
    max_value: float,
    water_ratio: float,
    include_beaches: bool,
    include_forests: bool,
    include_desert: bool,
    rng: random.Random,
) -> None:
    if not values:
        return

    values_sorted = sorted(values)
    threshold_index = int(water_ratio * (len(values_sorted) - 1))
    threshold_index = max(0, min(len(values_sorted) - 1, threshold_index))
    water_level = values_sorted[threshold_index]

    water_depth_range = max(1e-5, water_level - min_value)
    land_height_range = max(1e-5, max_value - water_level)

    width = len(height_map[0]) if height_map else 0
    height = len(height_map)

    desert_phase = rng.random() * math.tau
    forest_phase = rng.random() * math.tau

    # Precompute simple waveforms to vary biome placement without exceeding
    # the five-to-six color palette.
    desert_wave_x = [
        math.sin((x / max(1, width)) * math.tau * 2.2 + desert_phase)
        for x in range(width)
    ]
    desert_wave_y = [
        math.cos((y / max(1, height)) * math.tau * 2.6 + desert_phase * 0.7)
        for y in range(height)
    ]
    forest_wave_x = [
        math.cos((x / max(1, width)) * math.tau * 3.4 + forest_phase)
        for x in range(width)
    ]
    forest_wave_y = [
        math.sin((y / max(1, height)) * math.tau * 3.0 + forest_phase * 1.3)
        for y in range(height)
    ]

    highland_color = DESERT_COLOR if include_desert else ROCK_COLOR

    for y in range(height):
        row = height_map[y]
        for x in range(width):
            value = row[x]
            if value <= water_level:
                depth_ratio = (water_level - value) / water_depth_range
                color = SHALLOW_WATER_COLOR if depth_ratio < 0.45 else DEEP_WATER_COLOR
            else:
                land_ratio_value = (value - water_level) / land_height_range
                land_ratio_value = max(0.0, min(1.0, land_ratio_value))

                # Determine if this pixel touches water to place beaches.
                coastal = False
                if include_beaches and land_ratio_value < 0.35:
                    for ny in range(max(0, y - 1), min(height, y + 2)):
                        neighbor_row = height_map[ny]
                        for nx in range(max(0, x - 1), min(width, x + 2)):
                            if neighbor_row[nx] <= water_level:
                                coastal = True
                                break
                        if coastal:
                            break

                if include_beaches and coastal and land_ratio_value < 0.35:
                    color = BEACH_COLOR
                else:
                    highland_threshold = 0.82
                    desert_band_low = 0.3
                    desert_band_high = 0.72
                    forest_band = 0.5

                    if land_ratio_value >= highland_threshold:
                        color = highland_color
                    elif (
                        include_desert
                        and desert_band_low <= land_ratio_value <= desert_band_high
                        and 0.5
                        + 0.5 * desert_wave_x[x] * desert_wave_y[y]
                        > 0.68
                    ):
                        color = highland_color
                    elif (
                        include_forests
                        and land_ratio_value >= forest_band
                        and 0.5
                        + 0.5 * forest_wave_x[x] * forest_wave_y[y]
                        > 0.55
                    ):
                        color = FOREST_COLOR
                    else:
                        color = GRASS_COLOR

            image.setPixelColor(x, y, color)


def main(api, values):
    seed_value = _clamp_int(values.get("random_seed", 0), 0, 999_999, 0)
    rng = random.Random()
    if seed_value:
        rng.seed(seed_value)

    large_islands = _clamp_int(values.get("large_islands", 2), 1, 4, 2)
    water_percentage = _clamp_float(values.get("water_percentage", 65), 30, 90, 65)
    include_beaches = _coerce_bool(values.get("include_beaches"), True)
    include_forests = _coerce_bool(values.get("include_forests"), True)
    include_desert = _coerce_bool(values.get("include_desert"), True)

    water_ratio = water_percentage / 100.0
    water_ratio = max(0.15, min(0.9, water_ratio))
    land_ratio = 1.0 - water_ratio

    new_layer = api.create_layer("Procedural Islands")

    if not new_layer:
        api.show_message_box("Island Creator", "Could not create a new layer.")
        return

    def draw_islands(image):
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return

        specs = _generate_island_specs(rng, large_islands, width, height, land_ratio)
        height_map, values, min_value, max_value = _build_height_map(
            width, height, specs, rng
        )
        _assign_colors(
            image,
            height_map,
            values,
            min_value,
            max_value,
            water_ratio,
            include_beaches,
            include_forests,
            include_desert,
            rng,
        )

    api.modify_layer(new_layer, draw_islands)
