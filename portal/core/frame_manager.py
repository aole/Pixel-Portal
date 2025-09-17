from __future__ import annotations

from bisect import bisect_right
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
        key_index = self.resolve_key_frame_index(self.active_frame_index)
        if key_index is None:
            return None
        return self.frames[key_index]

    @property
    def current_layer_manager(self):
        frame = self.current_frame
        return frame.layer_manager if frame else None

    @property
    def active_layer_manager(self):
        """Alias for the active frame's layer manager."""
        return self.current_layer_manager

    # ------------------------------------------------------------------
    # Capacity helpers
    # ------------------------------------------------------------------
    def ensure_frame(self, index: int) -> None:
        """Ensure ``index`` is a valid frame position, extending the list if needed."""

        if index < 0:
            return

        if not self.frames:
            self.frames.append(Frame(self.width, self.height))
            self.active_frame_index = 0
            if not self.key_frames:
                self.key_frames = {0}

        while len(self.frames) <= index:
            source_index = self.resolve_key_frame_index(len(self.frames))
            if source_index is None or not (0 <= source_index < len(self.frames)):
                source_index = len(self.frames) - 1
            source_frame = self.frames[source_index]
            self.frames.append(source_frame.clone())

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

        resolved = self.resolve_key_frame_index(self.active_frame_index)
        if resolved is None and self.key_frames:
            self.active_frame_index = min(self.key_frames)

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

        normalized: Set[int] = set()
        for value in frames:
            try:
                frame = int(value)
            except (TypeError, ValueError):
                continue
            if frame < 0:
                continue
            self.ensure_frame(frame)
            if frame < len(self.frames):
                normalized.add(frame)
        if not normalized and self.frames:
            fallback = min(self.active_frame_index, len(self.frames) - 1)
            normalized = {max(0, fallback)}
        if normalized == self.key_frames:
            return False

        previous_keys = sorted(self.key_frames)
        self.key_frames = normalized

        # Ensure frames corresponding to the new key set contain data by
        # cloning from their nearest predecessors in the previous state.
        for key in sorted(self.key_frames):
            if key >= len(self.frames) or key in previous_keys:
                continue
            source_index: Optional[int] = None
            if previous_keys:
                position = bisect_right(previous_keys, key)
                if position:
                    source_index = previous_keys[position - 1]
                else:
                    source_index = previous_keys[0]
            else:
                source_index = key
            if source_index is None:
                continue
            if 0 <= source_index < len(self.frames):
                self.frames[key] = self.frames[source_index].clone()
        return True

    def add_key_frame(self, index: int) -> bool:
        if index < 0:
            return False
        self.ensure_frame(index)
        if not (0 <= index < len(self.frames)):
            return False
        if index in self.key_frames:
            return False
        source_index = self.resolve_key_frame_index(index)
        if source_index is None:
            source_index = 0
        self.frames[index] = self.frames[source_index].clone()
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
        fallback_index = self.resolve_key_frame_index(index)
        if fallback_index is None and self.key_frames:
            fallback_index = min(self.key_frames)
        if fallback_index is not None and 0 <= fallback_index < len(self.frames):
            self.frames[index] = self.frames[fallback_index].clone()
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

        if target_index is None or target_index < 0:
            return None
        self.ensure_frame(target_index)
        if not (0 <= target_index < len(self.frames)):
            return None
        if target_index in self.key_frames:
            return None

        self.frames[target_index] = self.frames[source_index].clone()
        self.key_frames.add(target_index)
        return target_index

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------
    def resolve_key_frame_index(self, frame_index: Optional[int] = None) -> Optional[int]:
        if not self.frames or not self.key_frames:
            return None
        if frame_index is None:
            frame_index = self.active_frame_index
        if frame_index < 0:
            frame_index = 0
        if frame_index >= len(self.frames):
            frame_index = len(self.frames) - 1

        sorted_keys = sorted(self.key_frames)
        position = bisect_right(sorted_keys, frame_index)
        if position:
            return sorted_keys[position - 1]
        return sorted_keys[0]


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
