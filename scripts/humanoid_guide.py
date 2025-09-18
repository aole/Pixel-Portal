import math
from typing import Dict, List, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter

POSE_CHOICES = ["T-Pose", "A-Pose"]

params = [
    {
        'name': 'pose',
        'type': 'choice',
        'label': 'Pose',
        'choices': POSE_CHOICES,
        'default': 'T-Pose',
    },
    {
        'name': 'head_height',
        'type': 'number',
        'label': 'Head Height (px)',
        'default': 20,
        'min': 8,
        'max': 96,
    },
    {
        'name': 'structure_color',
        'type': 'color',
        'label': 'Structure Color',
        'default': '#3B82F6',
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
    """Stores the rectangles and ellipses that compose the figure."""

    def __init__(self) -> None:
        self.ellipses: List[QRectF] = []
        self.rectangles: List[QRectF] = []
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


def build_humanoid_geometry(head_height: float, pose: str) -> HumanoidGeometry:
    geometry = HumanoidGeometry()
    figure_height = head_height * 8.0
    ground_y = figure_height

    head_width = head_height * 0.75
    neck_height = max(1.0, head_height * 0.25)
    neck_width = head_width * 0.45
    torso_height = head_height * 2.0
    torso_width = head_height * 1.9
    pelvis_height = head_height * 1.0
    pelvis_width = head_height * 1.6

    joint_diameter = max(2.0, head_height * 0.35)
    arm_thickness = max(1.0, head_height * 0.35)
    forearm_thickness = max(1.0, head_height * 0.3)
    upper_arm_length = head_height * 1.5
    lower_arm_length = head_height * 1.4

    leg_thickness = max(1.0, head_height * 0.45)
    calf_thickness = max(1.0, head_height * 0.38)
    upper_leg_length = head_height * 2.0
    lower_leg_length = head_height * 2.0
    foot_length = head_height * 1.1
    foot_thickness = max(2.0, head_height * 0.35)

    # Core body shapes (centered on the origin, figure grows downward).
    head_rect = QRectF(-head_width / 2.0, 0.0, head_width, head_height)
    geometry.add_ellipse(head_rect)

    neck_rect = QRectF(-neck_width / 2.0, head_rect.bottom(), neck_width, neck_height)
    geometry.add_rect(neck_rect)

    torso_rect = QRectF(-torso_width / 2.0, neck_rect.bottom(), torso_width, torso_height)
    geometry.add_rect(torso_rect)

    pelvis_rect = QRectF(-pelvis_width / 2.0, torso_rect.bottom(), pelvis_width, pelvis_height)
    geometry.add_rect(pelvis_rect)

    shoulder_y = neck_rect.bottom() + head_height * 0.2
    shoulder_offset = torso_width / 2.0 - head_height * 0.1
    left_shoulder = QPointF(-shoulder_offset, shoulder_y)
    right_shoulder = QPointF(shoulder_offset, shoulder_y)

    hip_y = pelvis_rect.top() + pelvis_height * 0.8
    hip_offset = pelvis_width * 0.35
    left_hip = QPointF(-hip_offset, hip_y)
    right_hip = QPointF(hip_offset, hip_y)

    geometry.add_joint(left_shoulder, joint_diameter)
    geometry.add_joint(right_shoulder, joint_diameter)
    geometry.add_joint(left_hip, joint_diameter)
    geometry.add_joint(right_hip, joint_diameter)

    pose_settings: Dict[str, Dict[str, Dict[str, Tuple[float, float]]]] = {
        "T-Pose": {
            'arms': {
                'left': (180.0, 180.0),
                'right': (0.0, 0.0),
            },
            'legs': {
                'left': (90.0, 90.0),
                'right': (90.0, 90.0),
            },
        },
        "A-Pose": {
            'arms': {
                'left': (150.0, 120.0),
                'right': (30.0, 60.0),
            },
            'legs': {
                'left': (105.0, 95.0),
                'right': (75.0, 85.0),
            },
        },
    }

    pose_angles = pose_settings.get(pose, pose_settings["T-Pose"])

    # Arms
    for side, shoulder_point in (('left', left_shoulder), ('right', right_shoulder)):
        upper_angle, lower_angle = pose_angles['arms'][side]
        elbow_point = polar_offset(shoulder_point, upper_arm_length, upper_angle)
        wrist_point = polar_offset(elbow_point, lower_arm_length, lower_angle)

        geometry.add_segment(shoulder_point, elbow_point, arm_thickness)
        geometry.add_segment(elbow_point, wrist_point, forearm_thickness)

        geometry.add_joint(elbow_point, joint_diameter)
        geometry.add_joint(wrist_point, joint_diameter * 0.9)

    # Legs
    for side, hip_point in (('left', left_hip), ('right', right_hip)):
        upper_angle, lower_angle = pose_angles['legs'][side]
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
        geometry.add_joint(ankle_point, joint_diameter * 0.9)

        foot_rect = QRectF(
            ankle_point.x() - foot_length / 2.0,
            desired_ankle_y,
            foot_length,
            foot_thickness,
        )
        geometry.add_rect(foot_rect)

    # Horizontal 8-head proportion guides.
    guide_width = max(torso_width, pelvis_width, head_width) * 1.4
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
    head_height = float(values['head_height'])
    structure_color = QColor(values['structure_color'])
    joint_color = QColor(values['joint_color'])
    guide_color = QColor(values['guide_color'])
    guide_color.setAlpha(160)

    new_layer = api.create_layer("Humanoid Guide")

    if not new_layer:
        api.show_message_box("Script Error", "Could not create a new layer.")
        return

    def draw_figure(image):
        nonlocal head_height
        canvas_width = image.width()
        canvas_height = image.height()

        max_head_height = max(4.0, canvas_height // 8)
        head_height = min(head_height, max_head_height)
        if head_height < 4.0:
            head_height = 4.0

        geometry = build_humanoid_geometry(head_height, pose)
        figure_width = geometry.max_x - geometry.min_x

        while head_height > 4.0 and figure_width > canvas_width:
            head_height -= 1.0
            geometry = build_humanoid_geometry(head_height, pose)
            figure_width = geometry.max_x - geometry.min_x

        figure_height = geometry.max_y - geometry.min_y
        vertical_offset = max(0.0, (canvas_height - figure_height) / 2.0 - geometry.min_y)
        horizontal_offset = canvas_width / 2.0 - (geometry.min_x + figure_width / 2.0)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Draw guides first so the figure sits on top.
        painter.setPen(Qt.NoPen)
        painter.setBrush(guide_color)
        for rect in geometry.guides:
            offset_rect = rect.translated(horizontal_offset, vertical_offset)
            painter.drawRect(offset_rect)

        painter.setPen(structure_color)
        painter.setBrush(structure_color)
        for rect in geometry.rectangles:
            painter.drawRect(rect.translated(horizontal_offset, vertical_offset))

        for start, end, thickness in geometry.segments:
            translated_start = QPointF(start.x() + horizontal_offset, start.y() + vertical_offset)
            translated_end = QPointF(end.x() + horizontal_offset, end.y() + vertical_offset)
            draw_segment(painter, translated_start, translated_end, thickness, structure_color)

        painter.setPen(structure_color)
        painter.setBrush(structure_color)
        for rect in geometry.ellipses:
            painter.drawEllipse(rect.translated(horizontal_offset, vertical_offset))

        painter.setPen(joint_color)
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

    api.modify_layer(new_layer, draw_figure)
