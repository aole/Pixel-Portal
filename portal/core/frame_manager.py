from __future__ import annotations

from typing import List, Optional

from PySide6.QtGui import QImage

from portal.core.frame import Frame
from portal.core.layer_manager import LayerManager


class FrameManager:
    """Manage a sequence of frames and track the active one."""

    def __init__(self, width: int, height: int, frame_count: int = 1):
        if frame_count < 0:
            raise ValueError("frame_count must be non-negative")

        self.width = width
        self.height = height
        self.frames: List[Frame] = [Frame(width, height) for _ in range(frame_count)]
        self.active_frame_index = 0 if self.frames else -1

    @property
    def current_frame(self) -> Optional[Frame]:
        if 0 <= self.active_frame_index < len(self.frames):
            return self.frames[self.active_frame_index]
        return None

    @property
    def current_layer_manager(self):
        frame = self.current_frame
        return frame.layer_manager if frame else None

    @property
    def active_layer_manager(self):
        """Alias for the active frame's layer manager."""
        return self.current_layer_manager

    def add_frame(self, frame: Optional[Frame] = None) -> Frame:
        if frame is None:
            frame = Frame(self.width, self.height)
        else:
            frame.layer_manager.width = self.width
            frame.layer_manager.height = self.height
        self.frames.append(frame)
        self.active_frame_index = len(self.frames) - 1
        return frame

    def remove_frame(self, index: int) -> None:
        if not (0 <= index < len(self.frames)):
            raise IndexError("Frame index out of range.")
        if len(self.frames) == 1:
            raise ValueError("Cannot remove the last frame.")

        del self.frames[index]

        if not self.frames:
            self.active_frame_index = -1
        elif self.active_frame_index >= len(self.frames):
            self.active_frame_index = len(self.frames) - 1
        elif self.active_frame_index > index:
            self.active_frame_index -= 1

    def duplicate_frame(self, index: Optional[int] = None) -> Frame:
        if not self.frames:
            raise ValueError("No frames available to duplicate.")

        if index is None:
            index = self.active_frame_index

        if not (0 <= index < len(self.frames)):
            raise IndexError("Frame index out of range.")

        duplicated = self.frames[index].clone()
        self.frames.insert(index + 1, duplicated)
        self.active_frame_index = index + 1
        return duplicated

    def select_frame(self, index: int) -> None:
        if not (0 <= index < len(self.frames)):
            raise IndexError("Frame index out of range.")
        self.active_frame_index = index

    def render_current_frame(self) -> QImage:
        frame = self.current_frame
        if frame is None:
            raise ValueError("No active frame to render.")
        return frame.render()

    def clone(self) -> "FrameManager":
        cloned_manager = FrameManager(self.width, self.height, frame_count=0)
        cloned_manager.frames = [frame.clone() for frame in self.frames]
        cloned_manager.active_frame_index = self.active_frame_index
        return cloned_manager


def resolve_active_layer_manager(document) -> LayerManager | None:
    """Return the active layer manager for ``document`` with compatibility fallbacks."""

    frame_manager = getattr(document, "frame_manager", None)
    if isinstance(frame_manager, FrameManager):
        manager = frame_manager.active_layer_manager
        if manager is not None:
            return manager

    try:
        return document.layer_manager
    except Exception:
        return getattr(document, "layer_manager", None)
