from __future__ import annotations

from typing import Collection

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter

from portal.core.layer_manager import LayerManager


class Frame:
    """A single animation frame composed of a layer stack."""

    def __init__(self, width: int, height: int, create_background: bool = True):
        self.layer_manager = LayerManager(width, height, create_background=create_background)

    @property
    def width(self) -> int:
        return self.layer_manager.width

    @property
    def height(self) -> int:
        return self.layer_manager.height

    def render(self, allowed_layer_uids: Collection[int] | None = None) -> QImage:
        """Composite the frame's visible layers into a single image.

        When *allowed_layer_uids* is provided, only layers whose UID appears in
        the collection contribute to the composited result.
        """
        final_image = QImage(QSize(self.width, self.height), QImage.Format_ARGB32)
        final_image.fill("transparent")

        allowed: set[int] | None = None
        if allowed_layer_uids is not None:
            allowed = set()
            for uid in allowed_layer_uids:
                try:
                    allowed.add(int(uid))
                except (TypeError, ValueError):
                    continue

        painter = QPainter(final_image)
        for layer in self.layer_manager.layers:
            if allowed is not None and layer.uid not in allowed:
                continue
            if layer.visible:
                painter.setOpacity(layer.opacity)
                painter.drawImage(0, 0, layer.image)
        painter.end()

        return final_image

    def clone(self) -> "Frame":
        """Create a deep copy of the frame and its layers."""
        cloned_frame = Frame(self.width, self.height, create_background=False)
        cloned_frame.layer_manager = self.layer_manager.clone()
        return cloned_frame
