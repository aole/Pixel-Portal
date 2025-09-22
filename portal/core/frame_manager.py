"""Minimal frame manager stub used after removing animation support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Set

from PySide6.QtGui import QImage

from portal.core.frame import Frame
from portal.core.layer import Layer
from portal.core.layer_manager import LayerManager


@dataclass
class _LayerState:
    """Track a layer's key frames in the non-animated environment."""

    layer_uid: int
    keys: Set[int]


class FrameManager:
    """Simplified frame manager that always exposes a single frame."""

    def __init__(self, width: int, height: int) -> None:
        self.width = int(width)
        self.height = int(height)
        self.frames: list[Frame] = [Frame(self.width, self.height)]
        self.active_frame_index: int = 0
        self.frame_markers: Set[int] = {0}
        self.layer_keys: dict[int, Set[int]] = {}
        self._ensure_default_keys()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_default_keys(self) -> None:
        manager = self.current_layer_manager
        if manager is None:
            return
        for layer in manager.layers:
            self.layer_keys.setdefault(layer.uid, {0})

    def _layer_state(self, layer_uid: int) -> _LayerState | None:
        keys = self.layer_keys.get(layer_uid)
        if keys is None:
            return None
        return _LayerState(layer_uid=layer_uid, keys=keys)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def current_frame(self) -> Frame | None:
        if not self.frames:
            return None
        return self.frames[0]

    @property
    def current_layer_manager(self) -> LayerManager | None:
        frame = self.current_frame
        return frame.layer_manager if frame is not None else None

    @property
    def active_layer_manager(self) -> LayerManager | None:
        return self.current_layer_manager

    # ------------------------------------------------------------------
    # Frame operations (no-ops beyond the primary frame)
    # ------------------------------------------------------------------
    def ensure_frame(self, index: int) -> None:
        if index < 0:
            return
        if not self.frames:
            self.frames.append(Frame(self.width, self.height))
            self.active_frame_index = 0
            self._ensure_default_keys()

    def add_frame(self, frame: Frame | None = None) -> Frame | None:
        return self.current_frame

    def insert_frame(self, index: int, frame: Frame | None = None) -> Frame | None:
        return self.current_frame

    def remove_frame(self, index: int) -> None:
        return

    def select_frame(self, index: int) -> None:
        if not self.frames:
            self.active_frame_index = -1
        else:
            self.active_frame_index = 0

    def render_current_frame(self) -> QImage:
        frame = self.current_frame
        if frame is None:
            image = QImage(self.width, self.height, QImage.Format_ARGB32)
            image.fill(0)
            return image
        return frame.render()

    # ------------------------------------------------------------------
    # Key-frame helpers (constrained to frame 0)
    # ------------------------------------------------------------------
    def layer_key_frames(self, layer_uid: int) -> list[int]:
        state = self._layer_state(layer_uid)
        if state is None:
            return [0]
        return sorted(state.keys)

    def set_layer_key_frames(self, layer_uid: int, frames: Iterable[int]) -> bool:
        normalized = {0}
        state = self._layer_state(layer_uid)
        if state is None or state.keys != normalized:
            self.layer_keys[layer_uid] = normalized
            return True
        return False

    def move_layer_keys(self, layer_uid: int, moves: dict[int, int]) -> bool:
        return False

    def duplicate_layer_keys_with_offset(
        self, layer_uid: int, frames: Iterable[int], offset: int
    ) -> bool:
        return False

    def add_layer_key(self, layer_uid: int, frame_index: int) -> bool:
        keys = self.layer_keys.setdefault(layer_uid, set())
        if 0 not in keys:
            keys.add(0)
            return True
        return False

    def remove_layer_key(self, layer_uid: int, frame_index: int) -> bool:
        keys = self.layer_keys.get(layer_uid)
        if not keys or frame_index == 0:
            return False
        if frame_index in keys:
            keys.remove(frame_index)
            return True
        return False

    def duplicate_layer_key(
        self, layer_uid: int, source_frame: int | None = None, target_frame: int | None = None
    ) -> Optional[int]:
        return None

    def clone_layer_key_state(self, layer_uid: int, frame_index: int) -> Layer | None:
        layer = self.layer_for_frame(frame_index, layer_uid)
        if layer is None:
            return None
        return layer.clone(deep_copy=True)

    def paste_layer_key(self, layer_uid: int, frame_index: int, key_state: Layer) -> bool:
        layer = self.layer_for_frame(frame_index, layer_uid)
        if layer is None:
            return False
        layer.apply_key_state_from(key_state, deep_copy=True)
        return True

    def register_new_layer(
        self, layer: Layer, index: int | None = None, *, key_frames: Iterable[int] | None = None
    ) -> None:
        self.layer_keys.setdefault(layer.uid, {0})

    def unregister_layer(self, layer_uid: int) -> None:
        self.layer_keys.pop(layer_uid, None)

    def duplicate_layer_keys(self, source_layer_uid: int, new_layer: Layer) -> None:
        keys = self.layer_keys.get(source_layer_uid, {0})
        self.layer_keys[new_layer.uid] = set(keys)

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    def resolve_key_frame_index(self, index: int | None = None) -> Optional[int]:
        if not self.frames:
            return None
        return 0

    def resolve_layer_key_frame_index(self, layer_uid: int, frame_index: int) -> Optional[int]:
        if layer_uid not in self.layer_keys:
            return None
        return 0

    def layer_manager_for_frame(self, frame_index: int) -> LayerManager | None:
        if frame_index != 0:
            return None
        return self.current_layer_manager

    def layer_for_frame(self, frame_index: int, layer_uid: int) -> Layer | None:
        manager = self.layer_manager_for_frame(frame_index)
        if manager is None:
            return None
        return manager.find_layer_by_uid(layer_uid)

    def iter_layer_instances(
        self, layer_uid: int, frame_indices: Iterable[int], *, ensure_frames: bool = False
    ) -> Iterator[Layer]:
        layer = self.layer_for_frame(0, layer_uid)
        if layer is not None:
            yield layer

    # ------------------------------------------------------------------
    # Cloning
    # ------------------------------------------------------------------
    def clone(self, *, deep_copy: bool = False) -> "FrameManager":
        clone = FrameManager(self.width, self.height)
        manager = self.current_layer_manager
        clone_manager = clone.current_layer_manager
        if manager is not None and clone_manager is not None:
            clone.frames[0].layer_manager = manager.clone(deep_copy=deep_copy)
            clone._ensure_default_keys()
            clone.current_layer_manager.active_layer_index = manager.active_layer_index
        clone.layer_keys = {uid: set(keys) for uid, keys in self.layer_keys.items()}
        clone.frame_markers = set(self.frame_markers)
        clone.active_frame_index = 0 if clone.frames else -1
        return clone


def resolve_active_layer_manager(document) -> LayerManager | None:
    """Compatibility helper used by tools and renderer code."""

    if document is None:
        return None
    manager = getattr(document, "layer_manager", None)
    if isinstance(manager, LayerManager):
        return manager
    try:
        return document.layer_manager
    except Exception:  # pragma: no cover - best effort fallback
        return None
