import math
from typing import Dict, List, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF

POSE_CHOICES = ["T-Pose", "A-Pose"]

STRUCTURE_COLOR_HEX = "#FFC68C"

TOP_MARGIN_RATIO = 0.10
BOTTOM_MARGIN_RATIO = 0.01

params = [
    {
        'name': 'pose',
        'type': 'choice',
        'label': 'Pose',
        'choices': POSE_CHOICES,
        'default': 'A-Pose',
    },
    {
        'name': 'joint_color',
        'type': 'color',
        'label': 'Joint Color',
        'default': '#F97316',
    },
    {
        'name': 'guide_color',
        'type': 'color',
        'label': 'Guide Color',
        'default': '#94A3B8',
    },
]


class HumanoidGeometry:
    """Stores the primitives that compose the figure."""

    def __init__(self) -> None:
        self.ellipses: List[QRectF] = []
        self.rectangles: List[QRectF] = []
        self.polygons: List[QPolygonF] = []
        self.segments: List[Tuple[QPointF, QPointF, float]] = []
        self.joints: List[Tuple[QPointF, float]] = []
        self.guides: List[QRectF] = []
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

    def add_joint(self, center: QPointF, diameter: float) -> None:
        radius = diameter / 2.0
        rect = QRectF(center.x() - radius, center.y() - radius, diameter, diameter)
        self.joints.append((center, diameter))
        self._update_bounds(rect.left(), rect.top(), rect.right(), rect.bottom())

    def add_guide(self, rect: QRectF) -> None:
        self.guides.append(rect)
        self._update_bounds(rect.left(), rect.top(), rect.right(), rect.bottom())

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


def build_humanoid_geometry(head_height: float, pose: str) -> HumanoidGeometry:
    geometry = HumanoidGeometry()
    figure_height = head_height * 8.0
    ground_y = figure_height

    head_width = head_height * 0.75
    neck_height = max(1.0, head_height * 0.25)
    neck_width = head_width * 0.45
    torso_height = head_height * 2.0
    torso_width_top = head_height * 1.9
    torso_width_bottom = head_height * 1.5
    pelvis_height = head_height * 1.0
    pelvis_width = head_height * 1.5

    joint_diameter = max(2.0, head_height * 0.35)
    arm_thickness = max(1.0, head_height * 0.35)
    forearm_thickness = max(1.0, head_height * 0.3)
    upper_arm_length = head_height * 1.5
    lower_arm_length = head_height * 1.4

    leg_thickness = max(1.0, head_height * 0.7)
    calf_thickness = max(1.0, head_height * 0.4)
    upper_leg_length = head_height * 2.0
    lower_leg_length = head_height * 2.0
    foot_length = head_height * 0.65
    foot_thickness = max(2.0, head_height * 0.35)

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

    shoulder_y = torso_top + head_height * 0.2
    shoulder_offset = torso_width_top / 2.0 - head_height * 0.1
    left_shoulder = QPointF(-shoulder_offset, shoulder_y)
    right_shoulder = QPointF(shoulder_offset, shoulder_y)

    hip_y = pelvis_rect.top() + pelvis_height * 0.65
    hip_offset = pelvis_width * 0.2
    left_hip = QPointF(-hip_offset, hip_y)
    right_hip = QPointF(hip_offset, hip_y)

    geometry.add_joint(left_shoulder, joint_diameter)
    geometry.add_joint(right_shoulder, joint_diameter)
    geometry.add_joint(left_hip, joint_diameter)
    geometry.add_joint(right_hip, joint_diameter)

    pose_settings: Dict[str, Dict[str, Tuple[float, float]]] = {
        "T-Pose": {
            'arms': (0.0, 0.0),
            'legs': (90.0, 90.0),
        },
        "A-Pose": {
            'arms': (30.0, 30.0),
            'legs': (75.0, 85.0),
        },
    }

    pose_angles = pose_settings.get(pose, pose_settings["T-Pose"])

    arm_angles = {
        'right': pose_angles['arms'],
        'left': tuple(mirror_angle(angle) for angle in pose_angles['arms']),
    }
    leg_angles = {
        'right': pose_angles['legs'],
        'left': tuple(mirror_angle(angle) for angle in pose_angles['legs']),
    }

    # Arms
    for side, shoulder_point in (('left', left_shoulder), ('right', right_shoulder)):
        upper_angle, lower_angle = arm_angles[side]
        elbow_point = polar_offset(shoulder_point, upper_arm_length, upper_angle)
        wrist_point = polar_offset(elbow_point, lower_arm_length, lower_angle)

        geometry.add_segment(shoulder_point, elbow_point, arm_thickness)
        geometry.add_segment(elbow_point, wrist_point, forearm_thickness)

        geometry.add_joint(elbow_point, joint_diameter)
        geometry.add_joint(wrist_point, joint_diameter * 0.9)

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

        geometry.add_joint(knee_point, joint_diameter)
        geometry.add_joint(ankle_point, joint_diameter * 0.6)

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

    # Horizontal 8-head proportion guides.
    guide_width = max(torso_width_top, torso_width_bottom, pelvis_width, head_width) * 1.4
    guide_thickness = max(1.0, head_height * 0.05)
    for i in range(1, 8):
        y = head_height * i
        guide_rect = QRectF(-guide_width / 2.0, y - guide_thickness / 2.0, guide_width, guide_thickness)
        geometry.add_guide(guide_rect)

    geometry.max_y = max(geometry.max_y, ground_y)
    geometry.min_y = min(geometry.min_y, 0.0)

    return geometry


def main(api, values):
    pose = values['pose']
    structure_color = QColor(STRUCTURE_COLOR_HEX)
    joint_color = QColor(values['joint_color'])
    guide_color = QColor(values['guide_color'])
    guide_color.setAlpha(160)

    guides_layer = api.create_layer("Humanoid Guides")
    if not guides_layer:
        api.show_message_box("Script Error", "Could not create the guides layer.")
        return

    structure_layer = api.create_layer("Humanoid Structure")
    if not structure_layer:
        api.show_message_box("Script Error", "Could not create the structure layer.")
        return

    def layout_geometry(image):
        doc_height = image.height()
        desired_top_margin = doc_height * TOP_MARGIN_RATIO
        desired_bottom_margin = doc_height * BOTTOM_MARGIN_RATIO
        available_height = max(0.0, doc_height - desired_top_margin - desired_bottom_margin)

        head_height = max(4.0, available_height / 8.0)

        geometry = build_humanoid_geometry(head_height, pose)
        figure_width = geometry.max_x - geometry.min_x
        figure_height = geometry.max_y - geometry.min_y

        while head_height > 4.0 and (
            figure_width > image.width() or figure_height > available_height
        ):
            head_height -= 1.0
            geometry = build_humanoid_geometry(head_height, pose)
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

    def draw_guides_and_joints(image):
        geometry, horizontal_offset, vertical_offset = layout_geometry(image)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.setPen(Qt.NoPen)
        painter.setBrush(guide_color)
        for rect in geometry.guides:
            painter.drawRect(rect.translated(horizontal_offset, vertical_offset))

        painter.setBrush(joint_color)
        for center, diameter in geometry.joints:
            radius = diameter / 2.0
            ellipse_rect = QRectF(
                center.x() - radius + horizontal_offset,
                center.y() - radius + vertical_offset,
                diameter,
                diameter,
            )
            painter.drawEllipse(ellipse_rect)

        painter.end()

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

    api.modify_layer(guides_layer, draw_guides_and_joints)
    api.modify_layer(structure_layer, draw_structure)
