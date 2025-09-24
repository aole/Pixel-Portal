from __future__ import annotations

from PySide6.QtCore import QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter


class Key(QObject):
    """Represents the drawable state for a :class:`Layer`."""

    image_changed = Signal()

    def __init__(
        self,
        width: int,
        height: int,
        *,
        image: QImage | None = None,
    ) -> None:
        super().__init__()
        if image is None:
            image = QImage(QSize(width, height), QImage.Format_ARGB32)
            image.fill(QColor(0, 0, 0, 0))
        self._image = image
        self._non_transparent_bounds: QRect | None = None
        self._non_transparent_bounds_dirty = False

    @property
    def image(self) -> QImage:
        return self._image

    @image.setter
    def image(self, value: QImage) -> None:
        self._image = value
        self.mark_non_transparent_bounds_dirty()

    def clear(self, selection=None) -> None:
        """Fills the key with transparent pixels."""

        if selection and not selection.isEmpty():
            painter = QPainter(self._image)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(selection, QColor(0, 0, 0, 0))
            painter.end()
        else:
            self._image.fill(QColor(0, 0, 0, 0))

        self.image_changed.emit()
        self._set_non_transparent_bounds(None)

    def clone(self, *, deep_copy: bool = False) -> "Key":
        """Return a copy of this key."""

        image = self._image.copy() if deep_copy else QImage(self._image)
        cloned_key = Key(image.width(), image.height(), image=image)
        cloned_key._copy_non_transparent_bounds_from(self)
        return cloned_key

    def apply_state_from(
        self,
        other: "Key",
        *,
        deep_copy: bool = False,
        emit_change: bool = True,
    ) -> None:
        if deep_copy:
            self._image = other.image.copy()
        else:
            self._image = QImage(other.image)
        self._copy_non_transparent_bounds_from(other)
        if emit_change:
            self.image_changed.emit()

    @classmethod
    def from_qimage(cls, qimage: QImage) -> "Key":
        key = cls(qimage.width(), qimage.height(), image=qimage)
        key._non_transparent_bounds = None
        key._non_transparent_bounds_dirty = True
        return key

    def flip_horizontal(self) -> None:
        self._image = self._image.flipped(Qt.Horizontal)
        self.image_changed.emit()

    def flip_vertical(self) -> None:
        self._image = self._image.flipped(Qt.Vertical)
        self.image_changed.emit()

    def mark_non_transparent_bounds_dirty(self) -> None:
        self._non_transparent_bounds_dirty = True

    @property
    def non_transparent_bounds(self) -> QRect | None:
        if self._non_transparent_bounds_dirty:
            self._recalculate_non_transparent_bounds()
        if self._non_transparent_bounds is None:
            return None
        return QRect(self._non_transparent_bounds)

    def _set_non_transparent_bounds(self, bounds: QRect | None) -> None:
        if bounds is None:
            self._non_transparent_bounds = QRect()
        else:
            self._non_transparent_bounds = QRect(bounds)
        self._non_transparent_bounds_dirty = False

    def _copy_non_transparent_bounds_from(self, other: "Key") -> None:
        if other._non_transparent_bounds_dirty:
            self._non_transparent_bounds = None
            self._non_transparent_bounds_dirty = True
        else:
            self._set_non_transparent_bounds(other._non_transparent_bounds)

    def _recalculate_non_transparent_bounds(self) -> None:
        bounds = self._calculate_non_transparent_bounds()
        if bounds is None or not bounds.isValid() or bounds.isEmpty():
            self._non_transparent_bounds = None
        else:
            self._non_transparent_bounds = bounds
        self._non_transparent_bounds_dirty = False

    def _calculate_non_transparent_bounds(self) -> QRect | None:
        image = getattr(self, "_image", None)
        if image is None or image.isNull():
            return None

        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return None

        left = width
        right = -1
        top = height
        bottom = -1

        for y in range(height):
            row_left = None
            row_right = None

            for x in range(width):
                if image.pixelColor(x, y).alpha() > 0:
                    row_left = x
                    break

            if row_left is None:
                continue

            for x in range(width - 1, -1, -1):
                if image.pixelColor(x, y).alpha() > 0:
                    row_right = x
                    break

            if row_right is None:
                continue

            if row_left < left:
                left = row_left
            if row_right > right:
                right = row_right
            if top == height:
                top = y
            bottom = y

        if right < left or bottom < top:
            return None

        return QRect(left, top, right - left + 1, bottom - top + 1)
