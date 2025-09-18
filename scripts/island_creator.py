import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from PySide6.QtGui import QColor

# Define the parameters for the script
params = [
    {
        'name': 'large_islands',
        'type': 'number',
        'label': 'Number of Large Islands',
        'default': 2,
        'min': 1,
        'max': 4,
    },
    {
        'name': 'water_percentage',
        'type': 'number',
        'label': 'Water Coverage (%)',
        'default': 60,
        'min': 20,
        'max': 90,
    },
    {
        'name': 'include_beaches',
        'type': 'checkbox',
        'label': 'Include Beaches',
        'default': True,
    },
    {
        'name': 'include_forest',
        'type': 'checkbox',
        'label': 'Include Forests',
        'default': True,
    },
    {
        'name': 'include_desert',
        'type': 'checkbox',
        'label': 'Include Deserts',
        'default': False,
    },
    {
        'name': 'random_seed',
        'type': 'number',
        'label': 'Random Seed (0 = random)',
        'default': 0,
        'min': 0,
        'max': 999_999,
    },
]


@dataclass
class IslandSeed:
    x: float
    y: float
    radius: float
    cos_angle: float
    sin_angle: float
    scale_x: float
    scale_y: float
    weight: float


def _coerce_int(value, default, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _coerce_bool(value, default):
    if isinstance(value, bool):
        return value
    if value in {"true", "True", "1", 1}:
        return True
    if value in {"false", "False", "0", 0}:
        return False
    return default


def _parse_seed(value):
    seed = _coerce_int(value, 0, minimum=0)
    return None if seed == 0 else seed


def _build_island_seeds(rng: random.Random, width: int, height: int, large_islands: int) -> Sequence[IslandSeed]:
    seeds: List[IslandSeed] = []
    margin_x = width * 0.15
    margin_y = height * 0.15
    base_radius = min(width, height)

    for _ in range(large_islands):
        cx = rng.uniform(margin_x, width - margin_x)
        cy = rng.uniform(margin_y, height - margin_y)
        radius = base_radius * rng.uniform(0.22, 0.32)
        angle = rng.uniform(0.0, math.tau)
        seeds.append(
            IslandSeed(
                x=cx,
                y=cy,
                radius=radius,
                cos_angle=math.cos(angle),
                sin_angle=math.sin(angle),
                scale_x=rng.uniform(0.85, 1.25),
                scale_y=rng.uniform(0.85, 1.25),
                weight=1.0,
            )
        )

    small_count = rng.randint(3, 6) + large_islands
    for _ in range(small_count):
        cx = rng.uniform(0, width)
        cy = rng.uniform(0, height)
        radius = base_radius * rng.uniform(0.06, 0.13)
        angle = rng.uniform(0.0, math.tau)
        seeds.append(
            IslandSeed(
                x=cx,
                y=cy,
                radius=radius,
                cos_angle=math.cos(angle),
                sin_angle=math.sin(angle),
                scale_x=rng.uniform(0.6, 1.35),
                scale_y=rng.uniform(0.6, 1.35),
                weight=rng.uniform(0.45, 0.75),
            )
        )

    return seeds


def _seed_influence(x: float, y: float, seed: IslandSeed) -> float:
    dx = x - seed.x
    dy = y - seed.y
    rot_x = dx * seed.cos_angle - dy * seed.sin_angle
    rot_y = dx * seed.sin_angle + dy * seed.cos_angle
    if seed.radius <= 0:
        return 0.0
    nx = rot_x / (seed.radius * seed.scale_x)
    ny = rot_y / (seed.radius * seed.scale_y)
    distance = math.hypot(nx, ny)
    if distance >= 1.2:
        return 0.0
    falloff = 1.0 - min(1.0, distance) ** 2
    return falloff * seed.weight


def _generate_height_maps(
    rng: random.Random,
    width: int,
    height: int,
    seeds: Sequence[IslandSeed],
) -> Tuple[List[List[float]], List[List[float]], List[float]]:
    score_rows: List[List[float]] = []
    feature_noise: List[List[float]] = []
    flat_scores: List[float] = []

    max_distance = math.hypot(width / 2.0, height / 2.0)
    freq_base = 2.0 * math.pi / max(width, height)
    freq_secondary = 2.0 * math.pi / (max(width, height) / 2.0)
    freq_detail = 2.0 * math.pi / (max(width, height) / 3.0)

    offset_a = rng.uniform(0.0, math.tau)
    offset_b = rng.uniform(0.0, math.tau)
    offset_c = rng.uniform(0.0, math.tau)

    for y in range(height):
        row: List[float] = []
        noise_row: List[float] = []
        for x in range(width):
            base = -0.9
            for seed in seeds:
                influence = _seed_influence(x, y, seed)
                if influence > base:
                    base = influence

            cx = x - width / 2.0
            cy = y - height / 2.0
            distance_from_center = math.hypot(cx, cy)
            edge_falloff = 1.0 - (distance_from_center / max_distance)

            swirl = (
                0.25 * math.sin((x * freq_base) + offset_a)
                + 0.18 * math.cos((y * freq_base * 1.2) + offset_b)
                + 0.12 * math.sin(((x + y) * freq_secondary) * 0.6 + offset_c)
                + 0.08 * math.cos((x - y) * freq_detail)
            )

            jitter = rng.uniform(-0.12, 0.12)
            score = (base * 0.65) + (edge_falloff * 0.35) + swirl + jitter
            score = max(-1.5, min(1.5, score))

            row.append(score)
            noise_row.append(rng.random())
            flat_scores.append(score)
        score_rows.append(row)
        feature_noise.append(noise_row)

    return score_rows, feature_noise, flat_scores


def _compute_thresholds(flat_scores: Sequence[float], water_percentage: int):
    if not flat_scores:
        return {
            'water': 0.0,
            'deep_water': -0.5,
            'coast': 0.1,
            'plains': 0.25,
            'feature': 0.55,
        }

    sorted_scores = sorted(flat_scores)
    total = len(sorted_scores)
    water_ratio = max(0.05, min(0.95, water_percentage / 100.0))
    water_index = max(1, min(int(total * water_ratio), total - 1))
    water_threshold = sorted_scores[water_index]

    deep_index = max(0, int(water_index * 0.45))
    deep_water_threshold = sorted_scores[deep_index]

    land_scores = sorted_scores[water_index:]
    if not land_scores:
        land_scores = [sorted_scores[-1]]

    land_total = len(land_scores)
    coast_index = max(0, min(int(land_total * 0.18), land_total - 1))
    plains_index = max(coast_index + 1, min(int(land_total * 0.52), land_total - 1))
    feature_index = max(plains_index + 1, min(int(land_total * 0.82), land_total - 1))

    coast_threshold = land_scores[coast_index]
    plains_threshold = land_scores[plains_index]
    feature_threshold = land_scores[feature_index]

    return {
        'water': water_threshold,
        'deep_water': deep_water_threshold,
        'coast': coast_threshold,
        'plains': plains_threshold,
        'feature': feature_threshold,
    }


def _pick_colors(include_beaches: bool, include_forest: bool, include_desert: bool):
    deep_water = QColor('#0B3954')
    shallow_water = QColor('#087E8B')
    single_water = QColor('#1E6091')
    coast = QColor('#F5D58D') if include_beaches else QColor('#828A95')
    plains = QColor('#88C057')
    forest = QColor('#2F5D50') if include_forest else QColor('#6B8F57')
    desert = QColor('#D8B26E') if include_desert else QColor('#A68A64')
    hills = QColor('#A68A64')
    mountains = QColor('#6F4C3E')

    palette = {
        'deep_water': deep_water,
        'shallow_water': shallow_water,
        'single_water': single_water,
        'coast': coast,
        'plains': plains,
        'forest': forest,
        'desert': desert,
        'hills': hills,
        'mountain': mountains,
    }
    return palette


def _render_islands(
    image,
    scores: Sequence[Sequence[float]],
    noise: Sequence[Sequence[float]],
    thresholds,
    palette,
    include_forest: bool,
    include_desert: bool,
):
    height = len(scores)
    width = len(scores[0]) if scores else 0

    use_dual_water = not (include_desert and include_forest)
    water_threshold = thresholds['water']
    deep_threshold = thresholds['deep_water'] if use_dual_water else None
    coast_threshold = thresholds['coast']
    plains_threshold = thresholds['plains']
    feature_threshold = thresholds['feature']

    for y in range(height):
        row_scores = scores[y]
        noise_row = noise[y]
        for x in range(width):
            value = row_scores[x]
            noise_value = noise_row[x]

            if value < water_threshold:
                if use_dual_water and deep_threshold is not None and value < deep_threshold:
                    color = palette['deep_water']
                else:
                    color = palette['shallow_water'] if use_dual_water else palette['single_water']
            elif value < coast_threshold:
                color = palette['coast']
            elif value < plains_threshold:
                if include_desert and include_forest:
                    color = palette['forest'] if noise_value > 0.55 else palette['plains']
                elif include_forest:
                    color = palette['forest'] if noise_value > 0.45 else palette['plains']
                elif include_desert:
                    color = palette['desert'] if noise_value > 0.6 else palette['plains']
                else:
                    color = palette['plains']
            elif value < feature_threshold:
                if include_desert and include_forest:
                    color = palette['desert'] if noise_value > 0.5 else palette['forest']
                elif include_desert:
                    color = palette['desert']
                elif include_forest:
                    color = palette['forest']
                else:
                    color = palette['hills']
            else:
                color = palette['mountain']

            image.setPixelColor(x, y, color)


def main(api, values):
    large_islands = _coerce_int(values.get('large_islands'), 2, minimum=1, maximum=4)
    water_percentage = _coerce_int(values.get('water_percentage'), 60, minimum=20, maximum=90)
    include_beaches = _coerce_bool(values.get('include_beaches'), True)
    include_forest = _coerce_bool(values.get('include_forest'), True)
    include_desert = _coerce_bool(values.get('include_desert'), False)
    seed = _parse_seed(values.get('random_seed'))

    new_layer = api.create_layer('Generated Islands')
    if not new_layer:
        api.show_message_box('Script Error', 'Could not create a new layer.')
        return

    def draw(image):
        rng = random.Random(seed) if seed is not None else random.Random()
        seeds = _build_island_seeds(rng, image.width(), image.height(), large_islands)
        scores, noise, flat_scores = _generate_height_maps(rng, image.width(), image.height(), seeds)
        thresholds = _compute_thresholds(flat_scores, water_percentage)
        palette = _pick_colors(include_beaches, include_forest, include_desert)

        if include_desert and include_forest:
            image.fill(palette['single_water'])
        else:
            base_water = palette['deep_water'] if thresholds['deep_water'] < thresholds['water'] else palette['shallow_water']
            image.fill(base_water)

        _render_islands(
            image,
            scores,
            noise,
            thresholds,
            palette,
            include_forest=include_forest,
            include_desert=include_desert,
        )

    api.modify_layer(new_layer, draw)
