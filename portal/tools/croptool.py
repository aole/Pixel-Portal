"""Interactive crop tool with draggable side handles."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPen

from portal.core.command import CropCommand
from portal.tools.basetool import BaseTool
from portal.ui.crop_dialog import CropDialog


@dataclass
class _CropEdges:
    left: int
    top: int
    right: int
    bottom: int

    def width(self) -> int:
        return max(1, self.right - self.left + 1)

    def height(self) -> int:
        return max(1, self.bottom - self.top + 1)

    def to_rect(self) -> QRect:
        return QRect(self.left, self.top, self.width(), self.height())


class CropTool(BaseTool):
    """Crop or expand the document by dragging side handles."""

    name = "Crop"
    icon = "icons/resize.png"
    category = "utility"
    requires_visible_layer = False

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)

        self._dialog: CropDialog | None = None
        self._edges = _CropEdges(0, 0, -1, -1)
        self._active_handle: str | None = None
        self._hover_handle: str | None = None
        self._handle_size = 14.0

    # ------------------------------------------------------------------
    def activate(self):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return

        self._sync_edges_to_document()
        self._show_dialog()
        self.canvas.update()

    # ------------------------------------------------------------------
    def deactivate(self):
        self._active_handle = None
        self._hover_handle = None
        self._close_dialog()
        self.canvas.setCursor(self.cursor)
        self.canvas.update()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        handle = self._hit_test_handles(event.position())
        if handle is None:
            return

        self._active_handle = handle
        self._hover_handle = handle
        self._set_handle_cursor(handle)

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event: QMouseEvent, doc_pos):
        if not (event.buttons() & Qt.LeftButton):
            return

        if self._active_handle is None:
            return

        self._update_edges_from_position(self._active_handle, doc_pos)
        self._update_dialog_rect()
        self._set_handle_cursor(self._active_handle)
        self.canvas.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        if self._active_handle is None:
            return

        self._update_edges_from_position(self._active_handle, doc_pos)
        self._update_dialog_rect()
        self._active_handle = None
        self._update_hover_from_position(event.position())
        self.canvas.update()

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event: QMouseEvent, doc_pos):
        self._update_hover_from_position(event.position())

    # ------------------------------------------------------------------
    def draw_overlay(self, painter: QPainter):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return

        if self._edges.right < self._edges.left or self._edges.bottom < self._edges.top:
            return

        overlay_rect = self._current_overlay_rect()
        if overlay_rect is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        self._draw_dimming_overlay(painter, overlay_rect)

        border_pen = QPen(QColor(255, 255, 255))
        border_pen.setWidth(1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(overlay_rect)

        handle_pen = QPen(QColor(0, 0, 0, 200))
        handle_pen.setWidth(1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)

        for name, rect in self._handle_rects().items():
            if name == self._active_handle:
                brush = QColor(255, 200, 0)
            elif name == self._hover_handle:
                brush = QColor(220, 220, 220)
            else:
                brush = QColor(255, 255, 255)
            painter.setBrush(brush)
            painter.drawRect(rect)

        painter.restore()

    # ------------------------------------------------------------------
    def _show_dialog(self):
        if self._dialog is None:
            parent = self.canvas.window()
            self._dialog = CropDialog(parent)
            self._dialog.rect_changed.connect(self._on_dialog_rect_changed)
            self._dialog.accepted.connect(self._on_dialog_accepted)
            self._dialog.rejected.connect(self._on_dialog_rejected)

        self._dialog.set_rect(self._edges.to_rect())
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    # ------------------------------------------------------------------
    def _close_dialog(self):
        if self._dialog is None:
            return

        try:
            self._dialog.rect_changed.disconnect(self._on_dialog_rect_changed)
        except (RuntimeError, TypeError):
            pass
        try:
            self._dialog.accepted.disconnect(self._on_dialog_accepted)
        except (RuntimeError, TypeError):
            pass
        try:
            self._dialog.rejected.disconnect(self._on_dialog_rejected)
        except (RuntimeError, TypeError):
            pass

        self._dialog.close()
        self._dialog.deleteLater()
        self._dialog = None

    # ------------------------------------------------------------------
    def _on_dialog_rect_changed(self, rect: QRect):
        width = max(1, rect.width())
        height = max(1, rect.height())

        self._edges.left = rect.x()
        self._edges.top = rect.y()
        self._edges.right = rect.x() + width - 1
        self._edges.bottom = rect.y() + height - 1
        self.canvas.update()

    # ------------------------------------------------------------------
    def _on_dialog_accepted(self):
        self._apply_crop()
        self._dialog = None

    # ------------------------------------------------------------------
    def _on_dialog_rejected(self):
        self._dialog = None
        self._sync_edges_to_document()
        self.canvas.update()

    # ------------------------------------------------------------------
    def _apply_crop(self):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return

        rect = self._edges.to_rect()
        if (
            rect.x() == 0
            and rect.y() == 0
            and rect.width() == document.width
            and rect.height() == document.height
        ):
            return

        command = CropCommand(document, rect)
        self.command_generated.emit(command)

        # The document now has the new bounds; update internal state to match.
        self._sync_edges_to_document()
        self.canvas.update()

    # ------------------------------------------------------------------
    def _sync_edges_to_document(self):
        document = getattr(self.canvas, "document", None)
        if document is None:
            self._edges = _CropEdges(0, 0, -1, -1)
            return

        width = max(1, int(document.width))
        height = max(1, int(document.height))
        self._edges = _CropEdges(0, 0, width - 1, height - 1)
        self._update_dialog_rect()

    # ------------------------------------------------------------------
    def _update_dialog_rect(self):
        if self._dialog is None:
            return
        self._dialog.set_rect(self._edges.to_rect())

    # ------------------------------------------------------------------
    def _update_edges_from_position(self, handle: str, doc_pos):
        x = int(doc_pos.x())
        y = int(doc_pos.y())

        if handle == "left":
            self._edges.left = min(x, self._edges.right)
        elif handle == "right":
            self._edges.right = max(x, self._edges.left)
        elif handle == "top":
            self._edges.top = min(y, self._edges.bottom)
        elif handle == "bottom":
            self._edges.bottom = max(y, self._edges.top)

    # ------------------------------------------------------------------
    def _current_overlay_rect(self) -> QRectF | None:
        if self._edges.right < self._edges.left or self._edges.bottom < self._edges.top:
            return None

        width = self._edges.width()
        height = self._edges.height()
        if width <= 0 or height <= 0:
            return None

        top_left_point = QPoint(self._edges.left, self._edges.top)
        bottom_right_point = QPoint(self._edges.right + 1, self._edges.bottom + 1)

        top_left = self.canvas.get_canvas_coords(top_left_point)
        bottom_right = self.canvas.get_canvas_coords(bottom_right_point)
        return QRectF(QPointF(top_left), QPointF(bottom_right)).normalized()

    # ------------------------------------------------------------------
    def _handle_rects(self) -> dict[str, QRectF]:
        overlay_rect = self._current_overlay_rect()
        if overlay_rect is None:
            return {}

        center = overlay_rect.center()
        points = {
            "left": QPointF(overlay_rect.left(), center.y()),
            "right": QPointF(overlay_rect.right(), center.y()),
            "top": QPointF(center.x(), overlay_rect.top()),
            "bottom": QPointF(center.x(), overlay_rect.bottom()),
        }

        half = self._handle_size / 2.0
        rects: dict[str, QRectF] = {}
        for name, point in points.items():
            rects[name] = QRectF(
                point.x() - half,
                point.y() - half,
                self._handle_size,
                self._handle_size,
            )
        return rects

    # ------------------------------------------------------------------
    def _hit_test_handles(self, pos: QPointF) -> str | None:
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    # ------------------------------------------------------------------
    def _update_hover_from_position(self, pos: QPointF):
        if self._active_handle:
            return

        handle = self._hit_test_handles(pos)
        if handle != self._hover_handle:
            self._hover_handle = handle
            self.canvas.update()

        if handle is None:
            self.canvas.setCursor(self.cursor)
        else:
            self._set_handle_cursor(handle)

    # ------------------------------------------------------------------
    def _set_handle_cursor(self, handle: str):
        if handle in {"left", "right"}:
            self.canvas.setCursor(Qt.SizeHorCursor)
        else:
            self.canvas.setCursor(Qt.SizeVerCursor)

    # ------------------------------------------------------------------
    def _draw_dimming_overlay(self, painter: QPainter, overlay_rect: QRectF):
        canvas_rect = QRectF(self.canvas.rect())

        canvas_left = canvas_rect.left()
        canvas_top = canvas_rect.top()
        canvas_right = canvas_left + canvas_rect.width()
        canvas_bottom = canvas_top + canvas_rect.height()

        overlay_left = overlay_rect.left()
        overlay_top = overlay_rect.top()
        overlay_right = overlay_left + overlay_rect.width()
        overlay_bottom = overlay_top + overlay_rect.height()

        dim_color = QColor(0, 0, 0, 120)

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(dim_color)

        # Top band
        top_height = max(0.0, min(canvas_bottom, overlay_top) - canvas_top)
        if top_height > 0:
            painter.drawRect(
                QRectF(canvas_left, canvas_top, canvas_rect.width(), top_height)
            )

        # Bottom band
        bottom_start = max(canvas_top, overlay_bottom)
        bottom_height = max(0.0, canvas_bottom - bottom_start)
        if bottom_height > 0:
            painter.drawRect(
                QRectF(canvas_left, bottom_start, canvas_rect.width(), bottom_height)
            )

        # Side bands (within the visible vertical span)
        vertical_start = max(canvas_top, overlay_top)
        vertical_end = min(canvas_bottom, overlay_bottom)
        vertical_height = max(0.0, vertical_end - vertical_start)

        if vertical_height > 0:
            left_end = min(overlay_left, canvas_right)
            left_width = max(0.0, left_end - canvas_left)
            if left_width > 0:
                painter.drawRect(
                    QRectF(canvas_left, vertical_start, left_width, vertical_height)
                )

            right_start = max(canvas_left, overlay_right)
            right_width = max(0.0, canvas_right - right_start)
            if right_width > 0:
                painter.drawRect(
                    QRectF(right_start, vertical_start, right_width, vertical_height)
                )

        painter.restore()


__all__ = ["CropTool"]
