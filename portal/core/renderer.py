import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QTransform,
)

from portal.core.frame_manager import resolve_active_layer_manager
from portal.ui.background import BackgroundImageMode


@dataclass(frozen=True)
class _OnionSkinSettings:
    prev_count: int
    next_count: int
    prev_color: Optional[QColor]
    next_color: Optional[QColor]

    @property
    def has_previous(self) -> bool:
        return self.prev_count > 0 and self.prev_color is not None

    @property
    def has_next(self) -> bool:
        return self.next_count > 0 and self.next_color is not None


@dataclass(frozen=True)
class _OnionSkinContext:
    frames: Sequence
    active_index: int
    resolved_index: Optional[int]
    key_indices: Tuple[int, ...]

    @property
    def active_is_key(self) -> bool:
        return self.resolved_index is not None and self.resolved_index == self.active_index

    @property
    def should_overlay_previous_on_top(self) -> bool:
        return (
            self.resolved_index is not None
            and self.resolved_index != self.active_index
        )

    def iter_keys(self, direction: int) -> Iterable[int]:
        if direction < 0:
            for key in reversed(self.key_indices):
                if key >= self.active_index:
                    continue
                yield key
        else:
            for key in self.key_indices:
                if key <= self.active_index:
                    continue
                yield key


class CanvasRenderer:
    def __init__(self, canvas, drawing_context):
        self.canvas = canvas
        self.drawing_context = drawing_context

    def paint(self, painter, document):
        if not document:
            return

        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.canvas.rect(), self.canvas.palette().window())

        target_rect = self.canvas.get_target_rect()

        self._draw_background(painter, target_rect)

        # Explicitly handle rotation preview to override normal document drawing
        if (
            self.canvas.temp_image
            and self.canvas.temp_image_replaces_active_layer
            and self.drawing_context.tool in {"Rotate", "Scale", "Transform"}
        ):
            final_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            final_image.fill(QColor("transparent"))
            self._draw_onion_skin_background(final_image, document)
            image_painter = QPainter(final_image)
            layer_manager = resolve_active_layer_manager(document)
            if layer_manager is not None:
                active_layer = layer_manager.active_layer
                for layer in layer_manager.layers:
                    if layer.visible:
                        image_to_draw = layer.image
                        if layer is active_layer:
                            image_to_draw = self.canvas.temp_image
                        image_painter.setOpacity(layer.opacity)
                        image_painter.drawImage(0, 0, image_to_draw)
            image_painter.end()
            self._draw_onion_skin_foreground(final_image, document)
            painter.drawImage(target_rect, final_image)
            image_to_draw_on = final_image
        else:
            image_to_draw_on = self._draw_document(painter, target_rect, document)
            if self.canvas.tile_preview_enabled:
                self._draw_tile_preview(painter, target_rect, image_to_draw_on)

        self._draw_border(painter, target_rect)
        self._draw_mirror_guides(painter, target_rect, document)
        self.draw_grid(painter, target_rect)
        self.draw_cursor(painter, target_rect, image_to_draw_on)
        self.canvas.current_tool.draw_overlay(painter)
        if self.canvas.selection_shape and not getattr(
            self.canvas, "selection_overlay_hidden", False
        ):
            self.draw_selection_overlay(painter, target_rect)
        self._draw_ai_output_overlay(painter, target_rect)

        self._draw_document_dimensions(painter, target_rect, document)
        self._draw_ruler_helper(painter, target_rect)

    def _draw_tile_preview(self, painter, target_rect, image):
        rows = self.canvas.tile_preview_rows
        cols = self.canvas.tile_preview_cols
        center_row = rows // 2
        center_col = cols // 2
        for row in range(rows):
            for col in range(cols):
                if row == center_row and col == center_col:
                    continue
                dx = (col - center_col) * target_rect.width()
                dy = (row - center_row) * target_rect.height()
                tile_rect = QRect(
                    target_rect.x() + dx,
                    target_rect.y() + dy,
                    target_rect.width(),
                    target_rect.height(),
                )
                self._draw_background(painter, tile_rect)
                painter.drawImage(tile_rect, image)
                overlay = self.canvas.tile_preview_image
                if overlay is not None:
                    if self.canvas.is_erasing_preview:
                        painter.save()
                        painter.setCompositionMode(
                            QPainter.CompositionMode_DestinationOut
                        )
                        painter.drawImage(tile_rect, overlay)
                        painter.restore()
                    else:
                        painter.drawImage(tile_rect, overlay)

    def _draw_mirror_guides(self, painter, target_rect, document):
        if not self.drawing_context.mirror_x and not self.drawing_context.mirror_y:
            return

        painter.save()
        pen = QPen(QColor(255, 0, 0, 150))  # A semi-transparent red
        pen.setCosmetic(True)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        zoom = self.canvas.zoom

        if self.drawing_context.mirror_x:
            axis_x = self.canvas._resolve_mirror_x_position()
            if axis_x is not None:
                line_x = target_rect.x() + (axis_x + 0.5) * zoom
                painter.drawLine(
                    int(round(line_x)), 0, int(round(line_x)), self.canvas.height()
                )

        if self.drawing_context.mirror_y:
            axis_y = self.canvas._resolve_mirror_y_position()
            if axis_y is not None:
                line_y = target_rect.y() + (axis_y + 0.5) * zoom
                painter.drawLine(
                    0, int(round(line_y)), self.canvas.width(), int(round(line_y))
                )

        painter.restore()

        handle_rects = self.canvas._mirror_handle_rects()
        if handle_rects:
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0, 180))
            for rect in handle_rects.values():
                painter.drawEllipse(rect)
            painter.restore()

    def _draw_background(self, painter, target_rect):
        background_image = self.canvas.background_image
        if background_image and not background_image.isNull():
            mode = getattr(self.canvas, "background_mode", BackgroundImageMode.FIT)
            alpha = getattr(self.canvas, "background_image_alpha", 1.0)
            try:
                alpha = float(alpha)
            except (TypeError, ValueError):
                alpha = 1.0
            alpha = max(0.0, min(1.0, alpha))
            if alpha <= 0:
                return

            painter.save()
            painter.setOpacity(alpha)
            try:
                if mode == BackgroundImageMode.STRETCH:
                    painter.drawPixmap(target_rect, background_image)
                elif mode == BackgroundImageMode.FIT:
                    scaled = background_image.scaled(
                        target_rect.size(), Qt.KeepAspectRatio, Qt.FastTransformation
                    )
                    if scaled.isNull():
                        return
                    dest_x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
                    dest_y = target_rect.y() + (target_rect.height() - scaled.height()) / 2
                    dest_rect = QRect(
                        int(round(dest_x)),
                        int(round(dest_y)),
                        scaled.width(),
                        scaled.height(),
                    )
                    painter.drawPixmap(dest_rect, scaled)
                elif mode == BackgroundImageMode.FILL:
                    scaled = background_image.scaled(
                        target_rect.size(),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.FastTransformation,
                    )
                    if scaled.isNull():
                        return
                    source_x = max(0, (scaled.width() - target_rect.width()) // 2)
                    source_y = max(0, (scaled.height() - target_rect.height()) // 2)
                    source_rect = QRect(
                        source_x,
                        source_y,
                        target_rect.width(),
                        target_rect.height(),
                    )
                    painter.drawPixmap(target_rect, scaled, source_rect)
                elif mode == BackgroundImageMode.CENTER:
                    scaled_width = max(
                        1, int(round(background_image.width() * self.canvas.zoom))
                    )
                    scaled_height = max(
                        1, int(round(background_image.height() * self.canvas.zoom))
                    )
                    if (
                        scaled_width != background_image.width()
                        or scaled_height != background_image.height()
                    ):
                        scaled = background_image.scaled(
                            scaled_width,
                            scaled_height,
                            Qt.IgnoreAspectRatio,
                            Qt.FastTransformation,
                        )
                    else:
                        scaled = background_image
                    if scaled.isNull():
                        return

                    dest_x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
                    dest_y = target_rect.y() + (target_rect.height() - scaled.height()) / 2

                    painter.save()
                    painter.setClipRect(target_rect)
                    painter.drawPixmap(int(round(dest_x)), int(round(dest_y)), scaled)
                    painter.restore()
                else:
                    # Fallback to stretch if an unknown mode is set.
                    painter.drawPixmap(target_rect, background_image)
            finally:
                painter.restore()
            return
        elif self.canvas.background.is_checkered:
            brush = QBrush(self.canvas.background_pixmap)
            transform = QTransform()
            transform.translate(target_rect.x(), target_rect.y())
            transform.scale(self.canvas.zoom, self.canvas.zoom)
            brush.setTransform(transform)
            painter.fillRect(target_rect, brush)
        else:
            painter.fillRect(target_rect, self.canvas.background.color)

    def _draw_document(self, painter, target_rect, document):
        layer_manager = resolve_active_layer_manager(document)
        if layer_manager is None:
            empty_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            empty_image.fill(Qt.transparent)
            self._draw_onion_skin_background(empty_image, document)
            self._draw_onion_skin_foreground(empty_image, document)
            painter.drawImage(target_rect, empty_image)
            return empty_image

        if self.canvas.temp_image and self.canvas.temp_image_replaces_active_layer:
            # This path is for tools like the Eraser, which operate on a copy of the active layer.
            # The `temp_image` is a full replacement for the active layer's image.
            # We need to reconstruct the entire document image, substituting the original active
            # layer with the temporary one.
            final_image = QImage(
                document.width,
                document.height,
                QImage.Format_ARGB32,
            )
            final_image.fill(QColor("transparent"))
            self._draw_onion_skin_background(final_image, document)
            image_painter = QPainter(final_image)

            active_layer = layer_manager.active_layer
            for layer in layer_manager.layers:
                if layer.visible:
                    image_to_draw = layer.image
                    if layer is active_layer:
                        image_to_draw = self.canvas.temp_image

                    image_painter.setOpacity(layer.opacity)
                    image_painter.drawImage(0, 0, image_to_draw)

            image_painter.end()
            self._draw_onion_skin_foreground(final_image, document)
            painter.drawImage(target_rect, final_image)
            return final_image
        else:
            # This path handles the standard document rendering and optional tool previews.
            final_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            final_image.fill(Qt.transparent)
            self._draw_onion_skin_background(final_image, document)
            p = QPainter(final_image)

            active_layer = layer_manager.active_layer
            for layer in layer_manager.layers:
                if not layer.visible:
                    continue

                p.setOpacity(layer.opacity)

                if (
                    self.canvas.temp_image
                    and self.canvas.is_erasing_preview
                    and layer is active_layer
                ):
                    # Punch a hole in a copy of the active layer using the erase mask.
                    erased_active_layer = active_layer.image.copy()
                    p_temp = QPainter(erased_active_layer)
                    p_temp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                    p_temp.drawImage(0, 0, self.canvas.temp_image)
                    p_temp.end()
                    p.drawImage(0, 0, erased_active_layer)
                else:
                    p.drawImage(0, 0, layer.image)
                    if self.canvas.temp_image and layer is active_layer:
                        # Draw the temporary tool preview at the correct layer depth
                        p.drawImage(0, 0, self.canvas.temp_image)

            p.end()
            self._draw_onion_skin_foreground(final_image, document)
            painter.drawImage(target_rect, final_image)
            return final_image

    def _draw_onion_skin_background(self, target: QImage, document) -> None:
        state = self._resolve_onion_skin_state(document)
        if state is None:
            return
        settings, context = state
        include_previous = settings.has_previous and not context.should_overlay_previous_on_top
        include_next = settings.has_next
        if not include_previous and not include_next:
            return
        self._apply_onion_skin(
            target,
            document,
            include_previous=include_previous,
            include_next=include_next,
            settings=settings,
            context=context,
        )

    def _draw_onion_skin_foreground(self, target: QImage, document) -> None:
        state = self._resolve_onion_skin_state(document)
        if state is None:
            return
        settings, context = state
        if not context.should_overlay_previous_on_top or not settings.has_previous:
            return
        self._apply_onion_skin(
            target,
            document,
            include_previous=True,
            include_next=False,
            settings=settings,
            context=context,
        )

    def _apply_onion_skin(
        self,
        target: QImage,
        document,
        *,
        include_previous: bool = True,
        include_next: bool = True,
        settings: Optional[_OnionSkinSettings] = None,
        context: Optional[_OnionSkinContext] = None,
    ) -> None:
        if not include_previous and not include_next:
            return

        if settings is None:
            settings = self._resolve_onion_skin_settings()
        if settings is None:
            return

        include_previous = include_previous and settings.has_previous
        include_next = include_next and settings.has_next
        if not include_previous and not include_next:
            return

        if context is None:
            context = self._build_onion_skin_context(document)
        if context is None:
            return

        drawn_indices: set[int] = set()
        if context.active_is_key:
            drawn_indices.add(context.active_index)

        previous_images: List[Tuple[int, QImage]] = []
        next_images: List[Tuple[int, QImage]] = []

        if include_previous and settings.prev_color is not None:
            previous_images = self._collect_onion_images(
                context,
                direction=-1,
                drawn_indices=drawn_indices,
                frame_limit=settings.prev_count,
                tint_color=settings.prev_color,
            )

        if include_next and settings.next_color is not None:
            next_images = self._collect_onion_images(
                context,
                direction=1,
                drawn_indices=drawn_indices,
                frame_limit=settings.next_count,
                tint_color=settings.next_color,
            )

        if not previous_images and not next_images:
            return

        painter = QPainter(target)
        try:
            for _, image in previous_images:
                painter.drawImage(0, 0, image)
            for _, image in next_images:
                painter.drawImage(0, 0, image)
        finally:
            painter.end()

    def _resolve_onion_skin_state(
        self, document
    ) -> Optional[Tuple[_OnionSkinSettings, _OnionSkinContext]]:
        settings = self._resolve_onion_skin_settings()
        if settings is None:
            return None

        context = self._build_onion_skin_context(document)
        if context is None:
            return None

        return settings, context

    def _resolve_onion_skin_settings(self) -> Optional[_OnionSkinSettings]:
        if not getattr(self.canvas, "onion_skin_enabled", False):
            return None

        prev_count = self._normalize_onion_count(
            getattr(self.canvas, "onion_skin_prev_frames", 0)
        )
        next_count = self._normalize_onion_count(
            getattr(self.canvas, "onion_skin_next_frames", 0)
        )

        prev_color: Optional[QColor] = None
        if prev_count > 0:
            prev_color = self._normalize_onion_color(
                getattr(self.canvas, "onion_skin_prev_color", None)
            )
            if prev_color is None:
                prev_count = 0

        next_color: Optional[QColor] = None
        if next_count > 0:
            next_color = self._normalize_onion_color(
                getattr(self.canvas, "onion_skin_next_color", None)
            )
            if next_color is None:
                next_count = 0

        if prev_count <= 0 and next_count <= 0:
            return None

        return _OnionSkinSettings(prev_count, next_count, prev_color, next_color)

    def _build_onion_skin_context(
        self, document
    ) -> Optional[_OnionSkinContext]:
        frame_manager = getattr(document, "frame_manager", None)
        if frame_manager is None:
            return None

        frames = getattr(frame_manager, "frames", None)
        if not frames:
            return None

        total_frames = len(frames)
        if total_frames <= 0:
            return None

        active_raw = getattr(frame_manager, "active_frame_index", 0)
        try:
            active_index = int(active_raw)
        except (TypeError, ValueError):
            active_index = 0
        active_index = max(0, min(active_index, total_frames - 1))

        resolved_index: Optional[int] = None
        if hasattr(frame_manager, "resolve_key_frame_index"):
            try:
                resolved_candidate = frame_manager.resolve_key_frame_index(active_index)
            except (TypeError, ValueError):
                resolved_candidate = None
            if resolved_candidate is not None:
                try:
                    resolved_index = int(resolved_candidate)
                except (TypeError, ValueError):
                    resolved_index = None
                else:
                    if resolved_index < 0 or resolved_index >= total_frames:
                        resolved_index = None

        markers_raw = getattr(frame_manager, "frame_markers", None)
        normalized_markers: List[int] = []
        if markers_raw:
            for marker in markers_raw:
                try:
                    normalized = int(marker)
                except (TypeError, ValueError):
                    continue
                if 0 <= normalized < total_frames:
                    normalized_markers.append(normalized)

        if not normalized_markers:
            normalized_markers = list(range(total_frames))

        if (
            resolved_index is not None
            and 0 <= resolved_index < total_frames
            and resolved_index not in normalized_markers
        ):
            normalized_markers.append(resolved_index)

        normalized_markers = sorted(set(normalized_markers))

        return _OnionSkinContext(
            frames=frames,
            active_index=active_index,
            resolved_index=resolved_index,
            key_indices=tuple(normalized_markers),
        )

    @staticmethod
    def _normalize_onion_count(raw_value) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return 0
        return max(0, value)

    @staticmethod
    def _normalize_onion_color(raw_color) -> Optional[QColor]:
        if raw_color is None:
            return None

        if isinstance(raw_color, QColor):
            color = QColor(raw_color)
        else:
            try:
                color = QColor(raw_color)
            except TypeError:
                return None

        if not color.isValid():
            return None

        return color

    def _collect_onion_images(
        self,
        context: _OnionSkinContext,
        *,
        direction: int,
        drawn_indices: set[int],
        frame_limit: int,
        tint_color: QColor,
    ) -> List[Tuple[int, QImage]]:
        if frame_limit <= 0:
            return []

        if tint_color.alpha() <= 0:
            return []

        frames = context.frames
        total_frames = len(frames)
        if total_frames <= 0:
            return []

        images: List[Tuple[int, QImage]] = []
        step = 0
        for key_index in context.iter_keys(direction):
            if key_index in drawn_indices:
                continue
            if key_index < 0 or key_index >= total_frames:
                continue

            frame = frames[key_index]
            if frame is None:
                continue

            render_fn = getattr(frame, "render", None)
            if render_fn is None:
                continue

            try:
                source = render_fn()
            except Exception:
                continue

            if source is None or source.isNull():
                continue

            tentative_step = step + 1
            tint_step_color = self._scaled_onion_color(tint_color, tentative_step)
            if tint_step_color.alpha() <= 0:
                continue

            tinted = self._create_tinted_onion_image(source, tint_step_color)
            if tinted is None or tinted.isNull():
                continue

            step = tentative_step
            drawn_indices.add(key_index)
            images.append((step, tinted))
            if step >= frame_limit:
                break

        images.sort(key=lambda item: item[0], reverse=True)
        return images

    @staticmethod
    def _create_tinted_onion_image(source: QImage, tint_color: QColor) -> QImage | None:
        if source is None or source.isNull():
            return None

        tinted = QImage(source.size(), QImage.Format_ARGB32_Premultiplied)
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        try:
            painter.drawImage(0, 0, source)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(source.rect(), tint_color)
        finally:
            painter.end()
        return tinted

    @staticmethod
    def _scaled_onion_color(color: QColor, step: int) -> QColor:
        scaled = QColor(color)
        if step <= 1:
            return scaled
        alpha = scaled.alphaF()
        alpha /= float(step)
        alpha = max(0.0, min(1.0, alpha))
        scaled.setAlphaF(alpha)
        return scaled

    def _draw_border(self, painter, target_rect):
        border_color = self.canvas.palette().color(QPalette.ColorRole.Text)
        border_pen = QPen(border_color, 1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRect(target_rect.adjusted(0, 0, -1, -1))

    def draw_selection_overlay(self, painter, target_rect):
        painter.save()

        transform = QTransform()
        transform.translate(target_rect.x(), target_rect.y())
        transform.scale(self.canvas.zoom, self.canvas.zoom)
        painter.setTransform(transform)

        pen1 = QPen(self.canvas.palette().color(QPalette.ColorRole.Highlight), 2)
        pen1.setCosmetic(True)
        pen1.setDashPattern([4, 4])
        painter.setPen(pen1)
        painter.drawPath(self.canvas.selection_shape)

        pen2 = QPen(self.canvas.palette().color(QPalette.ColorRole.HighlightedText), 2)
        pen2.setCosmetic(True)
        pen2.setDashPattern([4, 4])
        pen2.setDashOffset(4)
        painter.setPen(pen2)
        painter.drawPath(self.canvas.selection_shape)

        painter.restore()

    def _draw_ai_output_overlay(self, painter, target_rect):
        if not getattr(self.canvas, "ai_output_edit_enabled", False):
            return

        overlay_rect = self.canvas._ai_output_overlay_rect()
        if overlay_rect is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        border_pen = QPen(QColor(220, 0, 0))
        border_pen.setCosmetic(True)
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(overlay_rect)

        handle_pen = QPen(QColor(0, 0, 0, 200))
        handle_pen.setCosmetic(True)
        handle_pen.setWidth(1)
        painter.setPen(handle_pen)

        handle_rects = self.canvas._ai_output_handle_rects()
        for name, rect in handle_rects.items():
            if name == self.canvas._ai_output_active_handle:
                brush = QColor(255, 200, 0)
            elif name == self.canvas._ai_output_hover_handle:
                brush = QColor(220, 220, 220)
            else:
                brush = QColor(255, 255, 255)
            painter.setBrush(brush)
            painter.drawRect(rect)

        painter.restore()

    def _draw_document_dimensions(self, painter, target_rect, document):
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(self.canvas.palette().color(QPalette.ColorRole.Text))

        width_text = f"{document.width}px"
        height_text = f"{document.height}px"

        width_rect = painter.fontMetrics().boundingRect(width_text)
        width_x = target_rect.right() + 5
        width_y = target_rect.top() + width_rect.height()
        painter.drawText(width_x, width_y, width_text)

        height_rect = painter.fontMetrics().boundingRect(height_text)
        height_x = target_rect.left() - height_rect.width() - 5
        height_y = target_rect.bottom()
        painter.drawText(height_x, height_y, height_text)

    def _draw_ruler_helper(self, painter: QPainter, target_rect: QRect) -> None:
        if not getattr(self.canvas, "ruler_enabled", False):
            return

        start_doc = getattr(self.canvas, "_ruler_start", None)
        end_doc = getattr(self.canvas, "_ruler_end", None)
        if start_doc is None or end_doc is None:
            return

        centers = self.canvas._ruler_handle_centers()
        start_center = centers.get("start")
        end_center = centers.get("end")
        if start_center is None or end_center is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        handle_radius = max(2.0, float(getattr(self.canvas, "_ruler_handle_radius", 8)))
        hover_name = getattr(self.canvas, "_ruler_handle_hover", None)
        drag_name = getattr(self.canvas, "_ruler_handle_drag", None)

        dark_pen = QPen(QColor(0, 0, 0, 200))
        dark_pen.setWidth(4)
        dark_pen.setCapStyle(Qt.RoundCap)
        dark_pen.setJoinStyle(Qt.RoundJoin)
        dark_pen.setCosmetic(True)
        painter.setPen(dark_pen)
        painter.drawLine(start_center, end_center)

        light_pen = QPen(QColor(255, 255, 255, 220))
        light_pen.setWidth(2)
        light_pen.setCapStyle(Qt.RoundCap)
        light_pen.setJoinStyle(Qt.RoundJoin)
        light_pen.setCosmetic(True)
        painter.setPen(light_pen)
        painter.drawLine(start_center, end_center)

        dx_doc = end_doc.x() - start_doc.x()
        dy_doc = end_doc.y() - start_doc.y()
        distance = math.hypot(dx_doc, dy_doc)

        delta_x = end_center.x() - start_center.x()
        delta_y = end_center.y() - start_center.y()
        screen_length = math.hypot(delta_x, delta_y)
        if screen_length <= 0:
            normal_x, normal_y = 0.0, -1.0
        else:
            normal_x = -delta_y / screen_length
            normal_y = delta_x / screen_length

        def draw_tick_line(center_point: QPointF, length: float) -> None:
            if length <= 0 or screen_length <= 0:
                return
            half = length / 2.0
            start_tick = QPointF(
                center_point.x() + normal_x * half,
                center_point.y() + normal_y * half,
            )
            end_tick = QPointF(
                center_point.x() - normal_x * half,
                center_point.y() - normal_y * half,
            )
            painter.setPen(dark_pen)
            painter.drawLine(start_tick, end_tick)
            painter.setPen(light_pen)
            painter.drawLine(start_tick, end_tick)

        major_tick_length = max(handle_radius * 2.5, 12.0)
        draw_tick_line(start_center, major_tick_length)
        draw_tick_line(end_center, major_tick_length)

        interval_value = float(max(1, getattr(self.canvas, "_ruler_interval", 8)))
        minor_tick_length = max(handle_radius * 1.4, 8.0)
        if distance > 0 and interval_value > 0 and screen_length > 0:
            steps = int(distance // interval_value)
            for step_index in range(1, steps + 1):
                distance_along = step_index * interval_value
                if distance_along >= distance:
                    break
                ratio = distance_along / distance
                doc_point = QPointF(
                    start_doc.x() + dx_doc * ratio,
                    start_doc.y() + dy_doc * ratio,
                )
                interval_center = self.canvas._doc_point_to_canvas(doc_point)
                draw_tick_line(interval_center, minor_tick_length)

        for name, center in centers.items():
            rect = QRectF(
                center.x() - handle_radius,
                center.y() - handle_radius,
                handle_radius * 2,
                handle_radius * 2,
            )
            border_pen = QPen(QColor(0, 0, 0, 220))
            border_pen.setWidth(2)
            border_pen.setCosmetic(True)
            painter.setPen(border_pen)

            is_active = name == hover_name or name == drag_name
            fill_color = QColor(255, 255, 255, 235)
            if is_active:
                fill_color = QColor(255, 214, 170, 235)
            painter.setBrush(fill_color)
            painter.drawEllipse(rect)

        if math.isfinite(distance):
            if math.isclose(distance, round(distance), abs_tol=0.05):
                distance_text = f"{int(round(distance))} px"
            else:
                distance_text = f"{distance:.1f} px"
        else:
            distance_text = "0 px"

        mid_point = QPointF(
            (start_center.x() + end_center.x()) / 2.0,
            (start_center.y() + end_center.y()) / 2.0,
        )

        metrics = painter.fontMetrics()
        text_bounds = metrics.boundingRect(distance_text)
        padding_x = 8
        padding_y = 4
        label_rect = QRectF(
            0,
            0,
            text_bounds.width() + padding_x * 2,
            text_bounds.height() + padding_y * 2,
        )
        offset = handle_radius + label_rect.height() / 2.0 + 6
        label_center = QPointF(
            mid_point.x() + normal_x * offset,
            mid_point.y() + normal_y * offset,
        )
        label_rect.moveCenter(label_center)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 190))
        painter.drawRoundedRect(label_rect, 4, 4)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignCenter, distance_text)

        painter.restore()

    def draw_grid(self, painter, target_rect):
        if (
            self.canvas.zoom < 2
            or not self.canvas.grid_visible
            or target_rect.isNull()
        ):
            return

        major_visible = (
            self.canvas.grid_major_visible
            and self.canvas.grid_major_spacing > 0
        )
        minor_visible = (
            self.canvas.grid_minor_visible
            and self.canvas.grid_minor_spacing > 0
        )

        if not major_visible and not minor_visible:
            return

        doc_width = self.canvas._document_size.width()
        doc_height = self.canvas._document_size.height()

        if doc_width <= 0 or doc_height <= 0:
            return

        zoom = float(self.canvas.zoom)

        doc_top_left = self.canvas.get_doc_coords(QPoint(0, 0))
        doc_bottom_right = self.canvas.get_doc_coords(
            QPoint(self.canvas.width(), self.canvas.height())
        )

        start_x = max(0, int(math.floor(doc_top_left.x())))
        end_x = min(doc_width, int(math.ceil(doc_bottom_right.x())))
        start_y = max(0, int(math.floor(doc_top_left.y())))
        end_y = min(doc_height, int(math.ceil(doc_bottom_right.y())))

        if start_x > end_x or start_y > end_y:
            return

        major_spacing = max(1, int(self.canvas.grid_major_spacing))
        minor_spacing = max(1, int(self.canvas.grid_minor_spacing))

        def create_pen(color_value):
            color = QColor(color_value)
            if not color.isValid():
                return None
            pen = QPen(color)
            pen.setCosmetic(True)
            pen.setWidth(0)
            return pen

        major_pen = create_pen(self.canvas.grid_major_color) if major_visible else None
        minor_pen = create_pen(self.canvas.grid_minor_color) if minor_visible else None

        major_visible = major_visible and major_pen is not None
        minor_visible = minor_visible and minor_pen is not None

        if not major_visible and not minor_visible:
            return

        left = target_rect.left()
        right = target_rect.right()
        top = target_rect.top()
        bottom = target_rect.bottom()

        def first_multiple(start: int, spacing: int) -> int:
            remainder = start % spacing
            return start if remainder == 0 else start + (spacing - remainder)

        if major_visible:
            first_major_x = first_multiple(start_x, major_spacing)
            if first_major_x <= end_x:
                painter.setPen(major_pen)
                for dx in range(first_major_x, end_x + 1, major_spacing):
                    canvas_x = left + dx * zoom
                    painter.drawLine(
                        int(round(canvas_x)),
                        top,
                        int(round(canvas_x)),
                        bottom,
                    )

        if minor_visible:
            first_minor_x = first_multiple(start_x, minor_spacing)
            if first_minor_x <= end_x:
                painter.setPen(minor_pen)
                for dx in range(first_minor_x, end_x + 1, minor_spacing):
                    if major_visible and dx % major_spacing == 0:
                        continue
                    canvas_x = left + dx * zoom
                    painter.drawLine(
                        int(round(canvas_x)),
                        top,
                        int(round(canvas_x)),
                        bottom,
                    )

        if major_visible:
            first_major_y = first_multiple(start_y, major_spacing)
            if first_major_y <= end_y:
                painter.setPen(major_pen)
                for dy in range(first_major_y, end_y + 1, major_spacing):
                    canvas_y = top + dy * zoom
                    painter.drawLine(
                        left,
                        int(round(canvas_y)),
                        right,
                        int(round(canvas_y)),
                    )

        if minor_visible:
            first_minor_y = first_multiple(start_y, minor_spacing)
            if first_minor_y <= end_y:
                painter.setPen(minor_pen)
                for dy in range(first_minor_y, end_y + 1, minor_spacing):
                    if major_visible and dy % major_spacing == 0:
                        continue
                    canvas_y = top + dy * zoom
                    painter.drawLine(
                        left,
                        int(round(canvas_y)),
                        right,
                        int(round(canvas_y)),
                    )

    def draw_cursor(self, painter, target_rect, doc_image):
        layer_manager = resolve_active_layer_manager(self.canvas.document)
        active_layer = layer_manager.active_layer if layer_manager else None
        if (
            not self.canvas.mouse_over_canvas
            or (active_layer and not active_layer.visible)
            or self.canvas.drawing_context.tool
            in ["Bucket", "Picker", "Move", "Rotate", "Scale", "Transform"]
            or self.canvas.drawing_context.tool.startswith("Select")
            or self.canvas.ctrl_pressed
        ):
            return

        brush_type = self.canvas.drawing_context.brush_type
        is_eraser = self.canvas.drawing_context.tool == "Eraser"
        pattern_image = self.canvas.drawing_context.pattern_brush
        use_pattern_cursor = (
            brush_type == "Pattern"
            and pattern_image is not None
            and not pattern_image.isNull()
            and pattern_image.width() > 0
            and pattern_image.height() > 0
        )

        # Use the application's brush size
        brush_size = self.canvas.drawing_context.pen_width

        # Center the brush cursor around the mouse position
        doc_pos = self.canvas.cursor_doc_pos

        if use_pattern_cursor:
            pattern_width = pattern_image.width()
            pattern_height = pattern_image.height()
            doc_rect = QRect(
                doc_pos.x() - pattern_width // 2,
                doc_pos.y() - pattern_height // 2,
                pattern_width,
                pattern_height,
            )
        else:
            offset = brush_size / 2
            doc_rect = QRect(
                doc_pos.x() - int(math.floor(offset)),
                doc_pos.y() - int(math.floor(offset)),
                brush_size,
                brush_size,
            )

        # Convert document rectangle to screen coordinates for drawing
        screen_x = target_rect.x() + doc_rect.x() * self.canvas.zoom
        screen_y = target_rect.y() + doc_rect.y() * self.canvas.zoom
        screen_width = doc_rect.width() * self.canvas.zoom
        screen_height = doc_rect.height() * self.canvas.zoom

        cursor_screen_rect = QRect(
            int(screen_x),
            int(screen_y),
            max(1, int(screen_width)),
            max(1, int(screen_height)),
        )

        # Sample the color from the document image instead of grabbing the screen
        total_r, total_g, total_b = 0, 0, 0
        pixel_count = 0

        # Clamp the doc_rect to the image boundaries
        clamped_doc_rect = doc_rect.intersected(doc_image.rect())

        if not clamped_doc_rect.isEmpty():
            for x in range(clamped_doc_rect.left(), clamped_doc_rect.right() + 1):
                for y in range(clamped_doc_rect.top(), clamped_doc_rect.bottom() + 1):
                    # Clamp coordinates to be within the image bounds
                    if 0 <= x < doc_image.width() and 0 <= y < doc_image.height():
                        color = doc_image.pixelColor(x, y)
                        # Only consider visible pixels for the average
                        if color.alpha() > 0:
                            total_r += color.red()
                            total_g += color.green()
                            total_b += color.blue()
                            pixel_count += 1

        if pixel_count > 0:
            avg_r = total_r / pixel_count
            avg_g = total_g / pixel_count
            avg_b = total_b / pixel_count
            # Invert the average color
            inverted_color = QColor(255 - avg_r, 255 - avg_g, 255 - avg_b)
        else:
            # Fallback for transparent areas or if off-canvas: use the cached background color
            bg_color = self.canvas.background_color
            inverted_color = QColor(
                255 - bg_color.red(), 255 - bg_color.green(), 255 - bg_color.blue()
            )

        if use_pattern_cursor:
            painter.save()
            painter.setOpacity(0.7)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)
            source_rect = QRectF(0, 0, pattern_width, pattern_height)
            painter.drawImage(QRectF(cursor_screen_rect), pattern_image, source_rect)
            painter.restore()
        else:
            if not is_eraser:
                # Fill the cursor rectangle with the brush color when drawing.
                painter.setBrush(self.canvas.drawing_context.pen_color)
                painter.setPen(Qt.NoPen)  # No outline for the fill

                if brush_type == "Circular":
                    painter.drawEllipse(cursor_screen_rect)
                else:
                    painter.drawRect(cursor_screen_rect)

        if not use_pattern_cursor:
            # Draw the inverted outline on top for solid brushes
            painter.setPen(inverted_color)
            painter.setBrush(Qt.NoBrush)

            if brush_type == "Circular":
                painter.drawEllipse(cursor_screen_rect)
            else:
                painter.drawRect(cursor_screen_rect)
