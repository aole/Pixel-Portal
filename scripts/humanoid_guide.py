import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPolygonF

POSE_CHOICES = ["T-Pose", "A-Pose"]

STRUCTURE_COLOR_HEX = "#FFC68C"

CONFIG_FILE_PATH = Path(__file__).with_name("humanoid.json")

TOP_MARGIN_RATIO = 0.10
BOTTOM_MARGIN_RATIO = 0.01

DEFAULT_CONFIG: Dict[str, Any] = {
    "layout": {
        "top_margin_ratio": TOP_MARGIN_RATIO,
        "bottom_margin_ratio": BOTTOM_MARGIN_RATIO,
    },
    "head": {
        "width_ratio": 0.75,
    },
    "neck": {
        "height_ratio": 0.25,
        "min_height": 1.0,
        "width_ratio_to_head": 0.45,
    },
    "torso": {
        "height_ratio": 2.0,
        "width_top_ratio": 1.9,
        "width_bottom_ratio": 1.5,
    },
    "pelvis": {
        "height_ratio": 1.0,
        "width_ratio": 1.5,
    },
    "shoulders": {
        "vertical_offset_ratio": 0.2,
        "horizontal_inset_ratio": 0.1,
    },
    "hips": {
        "vertical_ratio": 0.65,
        "horizontal_offset_ratio": 0.2,
    },
    "arms": {
        "upper_length_ratio": 1.5,
        "lower_length_ratio": 1.4,
        "upper_thickness_ratio": 0.35,
        "upper_min_thickness": 1.0,
        "lower_thickness_ratio": 0.3,
        "lower_min_thickness": 1.0,
    },
    "legs": {
        "upper_length_ratio": 2.0,
        "lower_length_ratio": 2.0,
        "upper_thickness_ratio": 0.7,
        "upper_min_thickness": 1.0,
        "lower_thickness_ratio": 0.4,
        "lower_min_thickness": 1.0,
        "foot_length_ratio": 0.65,
        "foot_thickness_ratio": 0.35,
        "foot_min_thickness": 2.0,
    },
    "pose_angles": {
        "T-Pose": {
            "arms": [0.0, 0.0],
            "legs": [90.0, 90.0],
        },
        "A-Pose": {
            "arms": [30.0, 30.0],
            "legs": [75.0, 85.0],
        },
    },
}

params = [
    {
        'name': 'pose',
        'type': 'choice',
        'label': 'Pose',
        'choices': POSE_CHOICES,
        'default': 'A-Pose',
    },
]


def _merge_config(default: Any, override: Any) -> Any:
    if isinstance(default, dict) and isinstance(override, dict):
        merged: Dict[str, Any] = {}
        for key in default:
            if key in override:
                merged[key] = _merge_config(default[key], override[key])
            else:
                merged[key] = default[key]
        for key, value in override.items():
            if key not in merged:
                merged[key] = value
        return merged
    return override if override is not None else default


def load_humanoid_config() -> Dict[str, Any]:
    config: Dict[str, Any]
    should_write = False
    if CONFIG_FILE_PATH.exists():
        try:
            with CONFIG_FILE_PATH.open("r", encoding="utf-8") as file:
                user_config = json.load(file)
            config = _merge_config(DEFAULT_CONFIG, user_config)
            should_write = config != user_config
        except (OSError, ValueError, TypeError):
            config = DEFAULT_CONFIG
            should_write = True
    else:
        config = DEFAULT_CONFIG
        should_write = True

    if should_write:
        with CONFIG_FILE_PATH.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)
            file.write("\n")

    return config


class HumanoidGeometry:
    """Stores the primitives that compose the figure."""

    def __init__(self) -> None:
        self.ellipses: List[QRectF] = []
        self.rectangles: List[QRectF] = []
        self.polygons: List[QPolygonF] = []
        self.segments: List[Tuple[QPointF, QPointF, float]] = []
        self.min_x: float = float('inf')
        self.max_x: float = float('-inf')
        self.min_y: float = float('inf')
        self.max_y: float = float('-inf')

    def add_rect(self, rect: QRectF) -> None:
        self.rectangles.append(rect)
        self._update_bounds(rect.left(), rect.top(), rect.right(), rect.bottom())

    def add_ellipse(self, rect: QRectF) -> None:
        self.ellipses.append(rect)
        self._update_bounds(rect.left(), rect.top(), rect.right(), rect.bottom())

    def add_segment(self, start: QPointF, end: QPointF, thickness: float) -> None:
        self.segments.append((start, end, thickness))
        half = thickness / 2.0
        self._update_bounds(
            min(start.x(), end.x()) - half,
            min(start.y(), end.y()) - half,
            max(start.x(), end.x()) + half,
            max(start.y(), end.y()) + half,
        )

    def add_polygon(self, polygon: QPolygonF) -> None:
        self.polygons.append(polygon)
        if polygon.isEmpty():
            return
        xs = [point.x() for point in polygon]
        ys = [point.y() for point in polygon]
        self._update_bounds(min(xs), min(ys), max(xs), max(ys))

    def _update_bounds(self, left: float, top: float, right: float, bottom: float) -> None:
        self.min_x = min(self.min_x, left)
        self.max_x = max(self.max_x, right)
        self.min_y = min(self.min_y, top)
        self.max_y = max(self.max_y, bottom)


def polar_offset(start: QPointF, length: float, angle_degrees: float) -> QPointF:
    radians = math.radians(angle_degrees)
    dx = math.cos(radians) * length
    dy = math.sin(radians) * length
    return QPointF(start.x() + dx, start.y() + dy)


def draw_segment(painter: QPainter, start: QPointF, end: QPointF, thickness: float, color: QColor) -> None:
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = math.hypot(dx, dy)
    if length == 0:
        return
    painter.save()
    painter.translate(start.x(), start.y())
    angle = math.degrees(math.atan2(dy, dx))
    painter.rotate(angle)
    painter.setPen(color)
    painter.setBrush(color)
    painter.drawRect(QRectF(0, -thickness / 2.0, length, thickness))
    painter.restore()


def mirror_angle(angle: float) -> float:
    return (180.0 - angle) % 360.0


def build_humanoid_geometry(head_height: float, pose: str, config: Dict[str, Any]) -> HumanoidGeometry:
    geometry = HumanoidGeometry()
    figure_height = head_height * 8.0
    ground_y = figure_height

    head_width = head_height * config["head"]["width_ratio"]
    neck_settings = config["neck"]
    neck_height = max(neck_settings.get("min_height", 0.0), head_height * neck_settings["height_ratio"])
    neck_width = head_width * neck_settings["width_ratio_to_head"]

    torso_settings = config["torso"]
    torso_height = head_height * torso_settings["height_ratio"]
    torso_width_top = head_height * torso_settings["width_top_ratio"]
    torso_width_bottom = head_height * torso_settings["width_bottom_ratio"]

    pelvis_settings = config["pelvis"]
    pelvis_height = head_height * pelvis_settings["height_ratio"]
    pelvis_width = head_height * pelvis_settings["width_ratio"]

    arm_settings = config["arms"]
    upper_arm_length = head_height * arm_settings["upper_length_ratio"]
    lower_arm_length = head_height * arm_settings["lower_length_ratio"]
    arm_thickness = max(
        arm_settings.get("upper_min_thickness", 0.0),
        head_height * arm_settings["upper_thickness_ratio"],
    )
    forearm_thickness = max(
        arm_settings.get("lower_min_thickness", 0.0),
        head_height * arm_settings["lower_thickness_ratio"],
    )

    leg_settings = config["legs"]
    upper_leg_length = head_height * leg_settings["upper_length_ratio"]
    lower_leg_length = head_height * leg_settings["lower_length_ratio"]
    leg_thickness = max(
        leg_settings.get("upper_min_thickness", 0.0),
        head_height * leg_settings["upper_thickness_ratio"],
    )
    calf_thickness = max(
        leg_settings.get("lower_min_thickness", 0.0),
        head_height * leg_settings["lower_thickness_ratio"],
    )
    foot_length = head_height * leg_settings["foot_length_ratio"]
    foot_thickness = max(
        leg_settings.get("foot_min_thickness", 0.0),
        head_height * leg_settings["foot_thickness_ratio"],
    )

    # Core body shapes (centered on the origin, figure grows downward).
    head_rect = QRectF(-head_width / 2.0, 0.0, head_width, head_height)
    geometry.add_ellipse(head_rect)

    neck_rect = QRectF(-neck_width / 2.0, head_rect.bottom(), neck_width, neck_height)
    geometry.add_rect(neck_rect)

    torso_top = neck_rect.bottom()
    torso_bottom = torso_top + torso_height
    torso_polygon = QPolygonF([
        QPointF(-torso_width_top / 2.0, torso_top),
        QPointF(torso_width_top / 2.0, torso_top),
        QPointF(torso_width_bottom / 2.0, torso_bottom),
        QPointF(-torso_width_bottom / 2.0, torso_bottom),
    ])
    geometry.add_polygon(torso_polygon)

    pelvis_rect = QRectF(-pelvis_width / 2.0, torso_bottom, pelvis_width, pelvis_height)
    geometry.add_rect(pelvis_rect)

    shoulder_settings = config["shoulders"]
    shoulder_y = torso_top + head_height * shoulder_settings["vertical_offset_ratio"]
    shoulder_offset = torso_width_top / 2.0 - head_height * shoulder_settings["horizontal_inset_ratio"]
    left_shoulder = QPointF(-shoulder_offset, shoulder_y)
    right_shoulder = QPointF(shoulder_offset, shoulder_y)

    hip_settings = config["hips"]
    hip_y = pelvis_rect.top() + pelvis_height * hip_settings["vertical_ratio"]
    hip_offset = pelvis_width * hip_settings["horizontal_offset_ratio"]
    left_hip = QPointF(-hip_offset, hip_y)
    right_hip = QPointF(hip_offset, hip_y)

    pose_settings = config["pose_angles"]
    pose_angles = pose_settings.get(pose, pose_settings["T-Pose"])

    arm_angles = {
        'right': tuple(pose_angles['arms']),
        'left': tuple(mirror_angle(angle) for angle in pose_angles['arms']),
    }
    leg_angles = {
        'right': tuple(pose_angles['legs']),
        'left': tuple(mirror_angle(angle) for angle in pose_angles['legs']),
    }

    # Arms
    for side, shoulder_point in (('left', left_shoulder), ('right', right_shoulder)):
        upper_angle, lower_angle = arm_angles[side]
        elbow_point = polar_offset(shoulder_point, upper_arm_length, upper_angle)
        wrist_point = polar_offset(elbow_point, lower_arm_length, lower_angle)

        geometry.add_segment(shoulder_point, elbow_point, arm_thickness)
        geometry.add_segment(elbow_point, wrist_point, forearm_thickness)

    # Legs
    for side, hip_point in (('left', left_hip), ('right', right_hip)):
        upper_angle, lower_angle = leg_angles[side]
        knee_point = polar_offset(hip_point, upper_leg_length, upper_angle)
        ankle_point = polar_offset(knee_point, lower_leg_length, lower_angle)

        desired_ankle_y = ground_y - foot_thickness
        if abs(math.sin(math.radians(lower_angle))) > 1e-4:
            adjustment = (desired_ankle_y - ankle_point.y()) / math.sin(math.radians(lower_angle))
            adjusted_length = max(0.1, lower_leg_length + adjustment)
            ankle_point = polar_offset(knee_point, adjusted_length, lower_angle)

        geometry.add_segment(hip_point, knee_point, leg_thickness)
        geometry.add_segment(knee_point, ankle_point, calf_thickness)

        if side == 'left':
            foot_rect = QRectF(
                ankle_point.x() - foot_length,
                desired_ankle_y,
                foot_length,
                foot_thickness,
            )
        else:
            foot_rect = QRectF(
                ankle_point.x(),
                desired_ankle_y,
                foot_length,
                foot_thickness,
            )
        geometry.add_rect(foot_rect)

    geometry.max_y = max(geometry.max_y, ground_y)
    geometry.min_y = min(geometry.min_y, 0.0)

    return geometry


def main(api, values):
    config = load_humanoid_config()
    pose = values['pose']
    structure_color = QColor(STRUCTURE_COLOR_HEX)

    structure_layer = api.create_layer("Humanoid Structure")
    if not structure_layer:
        api.show_message_box("Script Error", "Could not create the structure layer.")
        return

    layout_config = config.get("layout", {})
    top_margin_ratio = layout_config.get("top_margin_ratio", TOP_MARGIN_RATIO)
    bottom_margin_ratio = layout_config.get("bottom_margin_ratio", BOTTOM_MARGIN_RATIO)

    def layout_geometry(image):
        doc_height = image.height()
        desired_top_margin = doc_height * top_margin_ratio
        desired_bottom_margin = doc_height * bottom_margin_ratio
        available_height = max(0.0, doc_height - desired_top_margin - desired_bottom_margin)

        head_height = max(4.0, available_height / 8.0)

        geometry = build_humanoid_geometry(head_height, pose, config)
        figure_width = geometry.max_x - geometry.min_x
        figure_height = geometry.max_y - geometry.min_y

        while head_height > 4.0 and (
            figure_width > image.width() or figure_height > available_height
        ):
            head_height -= 1.0
            geometry = build_humanoid_geometry(head_height, pose, config)
            figure_width = geometry.max_x - geometry.min_x
            figure_height = geometry.max_y - geometry.min_y

        extra_space = max(0.0, doc_height - figure_height)
        bottom_margin = min(desired_bottom_margin, extra_space)
        top_margin = min(desired_top_margin, max(0.0, extra_space - bottom_margin))

        vertical_offset = top_margin - geometry.min_y
        bottom_edge = geometry.max_y + vertical_offset
        limit = doc_height - bottom_margin
        if bottom_edge > limit:
            vertical_offset -= bottom_edge - limit

        horizontal_offset = image.width() / 2.0 - (geometry.min_x + figure_width / 2.0)

        return geometry, horizontal_offset, vertical_offset

    def draw_structure(image):
        geometry, horizontal_offset, vertical_offset = layout_geometry(image)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.setPen(structure_color)
        painter.setBrush(structure_color)
        for rect in geometry.rectangles:
            painter.drawRect(rect.translated(horizontal_offset, vertical_offset))

        for start, end, thickness in geometry.segments:
            translated_start = QPointF(start.x() + horizontal_offset, start.y() + vertical_offset)
            translated_end = QPointF(end.x() + horizontal_offset, end.y() + vertical_offset)
            draw_segment(painter, translated_start, translated_end, thickness, structure_color)

        for polygon in geometry.polygons:
            painter.drawPolygon(polygon.translated(horizontal_offset, vertical_offset))

        for rect in geometry.ellipses:
            painter.drawEllipse(rect.translated(horizontal_offset, vertical_offset))

        painter.end()

    api.modify_layer(structure_layer, draw_structure)
