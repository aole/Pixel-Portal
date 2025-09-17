from __future__ import annotations

from typing import Iterable, List, Optional, Set

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
        self.key_frames: Set[int] = {0} if self.frames else set()

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
        if not self.key_frames:
            self.key_frames.add(self.active_frame_index)
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

        if index in self.key_frames:
            self.key_frames.remove(index)
        remaining_keys = {
            frame_index if frame_index < index else frame_index - 1
            for frame_index in self.key_frames
            if frame_index != index
        }
        self.key_frames = remaining_keys
        if not self.key_frames and self.frames:
            fallback = min(self.active_frame_index, len(self.frames) - 1)
            fallback = max(0, fallback)
            self.key_frames.add(fallback)

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
        cloned_manager.key_frames = set(self.key_frames)
        return cloned_manager

    # ------------------------------------------------------------------
    # Keyframe helpers
    # ------------------------------------------------------------------
    def set_key_frames(self, frames: Iterable[int]) -> bool:
        """Replace the tracked keyframes with ``frames``.

        Returns ``True`` if the set changed.
        """

        normalized = {
            frame for frame in (int(value) for value in frames)
            if 0 <= frame < len(self.frames)
        }
        if not normalized and self.frames:
            fallback = min(self.active_frame_index, len(self.frames) - 1)
            normalized = {max(0, fallback)}
        if normalized == self.key_frames:
            return False
        self.key_frames = normalized
        return True

    def add_key_frame(self, index: int) -> bool:
        if not (0 <= index < len(self.frames)):
            return False
        if index in self.key_frames:
            return False
        self.key_frames.add(index)
        return True

    def remove_key_frame(self, index: int) -> bool:
        if not (0 <= index < len(self.frames)):
            return False
        if index not in self.key_frames:
            return False
        if len(self.key_frames) == 1:
            return False
        self.key_frames.remove(index)
        if not self.key_frames and self.frames:
            fallback = min(self.active_frame_index, len(self.frames) - 1)
            self.key_frames.add(max(0, fallback))
        return True

    def duplicate_key_frame(
        self, source_index: Optional[int] = None, target_index: Optional[int] = None
    ) -> Optional[int]:
        if not self.frames:
            return None

        if source_index is None:
            if self.key_frames:
                source_index = max(self.key_frames)
            else:
                source_index = min(self.active_frame_index, len(self.frames) - 1)
        elif source_index not in self.key_frames:
            return None

        if source_index is None or not (0 <= source_index < len(self.frames)):
            return None

        if target_index is None:
            candidate = source_index + 1
            while candidate < len(self.frames) and candidate in self.key_frames:
                candidate += 1
            target_index = candidate

        if target_index is None or not (0 <= target_index < len(self.frames)):
            return None
        if target_index in self.key_frames:
            return None

        self.key_frames.add(target_index)
        return target_index


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
