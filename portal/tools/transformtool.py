from __future__ import annotations
from typing import Literal, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCursor

from .basetool import BaseTool
from .movetool import MoveTool
from .rotatetool import RotateTool
from .scaletool import ScaleTool


Operation = Literal["move", "rotate", "scale"]


class TransformTool(BaseTool):
    """Combined move/rotate/scale tool that exposes all gizmos together."""

    name = "Transform"
    icon = "icons/toolmove.png"
    shortcut = "m"
    category = "draw"

    angle_changed = Signal(float)
    scale_changed = Signal(float)

    def __init__(
        self,
        canvas,
        *,
        move_tool: Optional[BaseTool] = None,
        rotate_tool: Optional[BaseTool] = None,
        scale_tool: Optional[BaseTool] = None,
    ):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.OpenHandCursor)

        self._move_tool = move_tool or MoveTool(canvas)
        self._rotate_tool = rotate_tool or RotateTool(canvas)
        self._scale_tool = scale_tool or ScaleTool(canvas)

        self._connect_signal(self._move_tool, "command_generated", self.command_generated.emit)
        self._connect_signal(self._rotate_tool, "command_generated", self.command_generated.emit)
        self._connect_signal(self._scale_tool, "command_generated", self.command_generated.emit)

        self._connect_signal(self._rotate_tool, "angle_changed", self.angle_changed.emit)
        self._connect_signal(self._scale_tool, "scale_changed", self.scale_changed.emit)

        self._active_operation: Operation | None = None

    # ------------------------------------------------------------------
    @staticmethod
    def _connect_signal(tool, signal_name: str, slot):
        signal = getattr(tool, signal_name, None)
        connect = getattr(signal, "connect", None)
        if callable(connect):
            connect(slot)

    # ------------------------------------------------------------------
    @staticmethod
    def _invoke(tool, method_name: str, *args, **kwargs):
        method = getattr(tool, method_name, None)
        if callable(method):
            return method(*args, **kwargs)
        return None

    # ------------------------------------------------------------------
    def activate(self):
        self._active_operation = None
        # Reset cached state for the composed tools so their gizmos reflect
        # the newly selected layer/selection.
        self._invoke(self._move_tool, "deactivate")
        self._invoke(self._rotate_tool, "activate")
        self._invoke(self._scale_tool, "activate")
        self.angle_changed.emit(0.0)

    # ------------------------------------------------------------------
    def deactivate(self):
        self._active_operation = None
        self._invoke(self._move_tool, "deactivate")
        self._invoke(self._rotate_tool, "deactivate")
        self._invoke(self._scale_tool, "deactivate")

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._active_operation = None

        self._invoke(self._rotate_tool, "mousePressEvent", event, doc_pos)
        if getattr(self._rotate_tool, "drag_mode", None) in {"rotate", "pivot"}:
            self._active_operation = "rotate"
            return

        self._invoke(self._scale_tool, "mousePressEvent", event, doc_pos)
        if getattr(self._scale_tool, "drag_mode", None) == "scale":
            self._active_operation = "scale"
            return

        self._invoke(self._move_tool, "mousePressEvent", event, doc_pos)
        self._active_operation = "move"

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        if self._active_operation == "rotate":
            self._invoke(self._rotate_tool, "mouseMoveEvent", event, doc_pos)
        elif self._active_operation == "scale":
            self._invoke(self._scale_tool, "mouseMoveEvent", event, doc_pos)
        else:
            self._invoke(self._move_tool, "mouseMoveEvent", event, doc_pos)

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        operation = self._active_operation

        if operation == "rotate":
            previous_mode = getattr(self._rotate_tool, "drag_mode", None)
            self._invoke(self._rotate_tool, "mouseReleaseEvent", event, doc_pos)
            self._handle_rotation_finished(previous_mode == "rotate")
        elif operation == "scale":
            self._invoke(self._scale_tool, "mouseReleaseEvent", event, doc_pos)
            self._handle_scale_finished()
        elif operation == "move":
            start_point = QPoint(getattr(self._move_tool, "start_point", QPoint()))
            self._invoke(self._move_tool, "mouseReleaseEvent", event, doc_pos)
            delta = doc_pos - start_point
            self._handle_move_finished(delta)
        else:
            self._invoke(self._move_tool, "mouseReleaseEvent", event, doc_pos)
            self._refresh_scale_handles()
            self._refresh_pivot()

        self._active_operation = None

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        self._invoke(self._rotate_tool, "mouseHoverEvent", event, doc_pos)
        self._invoke(self._scale_tool, "mouseHoverEvent", event, doc_pos)

    # ------------------------------------------------------------------
    def draw_overlay(self, painter):
        self._invoke(self._scale_tool, "draw_overlay", painter)
        self._invoke(self._rotate_tool, "draw_overlay", painter)

    # ------------------------------------------------------------------
    def _handle_rotation_finished(self, did_rotate: bool) -> None:
        if did_rotate:
            self._refresh_scale_handles()
        self._refresh_pivot()

    # ------------------------------------------------------------------
    def _handle_scale_finished(self) -> None:
        self._refresh_scale_handles()
        self._refresh_pivot()

    # ------------------------------------------------------------------
    def _handle_move_finished(self, delta: QPoint) -> None:
        pivot_is_manual = getattr(self._rotate_tool, "pivot_is_manual", None)
        pivot_manual = callable(pivot_is_manual) and pivot_is_manual()
        if pivot_manual and not delta.isNull():
            self._invoke(self._rotate_tool, "offset_pivot", delta)
        elif not pivot_manual:
            self._refresh_pivot()
        self._refresh_scale_handles()

    # ------------------------------------------------------------------
    def _refresh_scale_handles(self) -> None:
        self._invoke(self._scale_tool, "refresh_handles_from_document")

    # ------------------------------------------------------------------
    def _refresh_pivot(self) -> None:
        self._invoke(self._rotate_tool, "refresh_pivot_from_document")

