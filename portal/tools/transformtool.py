from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from .basetool import BaseTool
from .movetool import MoveTool
from .rotatetool import RotateTool
from .scaletool import ScaleTool


class TransformTool(BaseTool):
    """Combined move/rotate/scale tool that exposes all gizmos together."""

    name = "Transform"
    icon = "icons/toolmove.png"
    shortcut = "m"
    category = "draw"

    angle_changed = Signal(float)
    scale_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.OpenHandCursor)

        self._move_tool = MoveTool(canvas)
        self._rotate_tool = RotateTool(canvas)
        self._scale_tool = ScaleTool(canvas)

        self._move_tool.command_generated.connect(self.command_generated.emit)
        self._rotate_tool.command_generated.connect(self.command_generated.emit)
        self._scale_tool.command_generated.connect(self.command_generated.emit)

        self._rotate_tool.angle_changed.connect(self.angle_changed.emit)
        self._scale_tool.scale_changed.connect(self.scale_changed.emit)

        self._active_operation: str | None = None

    # ------------------------------------------------------------------
    def activate(self):
        self._active_operation = None
        # Reset cached state for the composed tools so their gizmos reflect
        # the newly selected layer/selection.
        self._move_tool.deactivate()
        self._rotate_tool.activate()
        self._scale_tool.activate()
        self.angle_changed.emit(0.0)

    # ------------------------------------------------------------------
    def deactivate(self):
        self._active_operation = None
        self._move_tool.deactivate()
        self._rotate_tool.deactivate()
        self._scale_tool.deactivate()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._active_operation = None

        self._rotate_tool.mousePressEvent(event, doc_pos)
        if self._rotate_tool.drag_mode in {"rotate", "pivot"}:
            self._active_operation = "rotate"
            return

        self._scale_tool.mousePressEvent(event, doc_pos)
        if self._scale_tool.drag_mode == "scale":
            self._active_operation = "scale"
            return

        self._move_tool.mousePressEvent(event, doc_pos)
        self._active_operation = "move"

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        if self._active_operation == "rotate":
            self._rotate_tool.mouseMoveEvent(event, doc_pos)
        elif self._active_operation == "scale":
            self._scale_tool.mouseMoveEvent(event, doc_pos)
        else:
            self._move_tool.mouseMoveEvent(event, doc_pos)

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        if self._active_operation == "rotate":
            self._rotate_tool.mouseReleaseEvent(event, doc_pos)
        elif self._active_operation == "scale":
            self._scale_tool.mouseReleaseEvent(event, doc_pos)
        else:
            self._move_tool.mouseReleaseEvent(event, doc_pos)

        self._active_operation = None

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        self._rotate_tool.mouseHoverEvent(event, doc_pos)
        self._scale_tool.mouseHoverEvent(event, doc_pos)

    # ------------------------------------------------------------------
    def draw_overlay(self, painter):
        self._scale_tool.draw_overlay(painter)
        self._rotate_tool.draw_overlay(painter)

