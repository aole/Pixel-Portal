from __future__ import annotations

from bisect import bisect_right
from typing import Dict, Iterable, List, Optional, Set

from PySide6.QtGui import QImage

from portal.core.frame import Frame
from portal.core.layer import Layer
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
        self.frame_markers: Set[int] = {0} if self.frames else set()
        self.layer_keys: Dict[int, Set[int]] = {}
        self._initialize_layer_keys()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialize_layer_keys(self) -> None:
        if not self.frames:
            return
        base_manager = self.frames[0].layer_manager
        for frame in self.frames[1:]:
            manager = frame.layer_manager
            manager.layers = [layer.clone() for layer in base_manager.layers]
            if manager.active_layer_index >= len(manager.layers):
                manager.active_layer_index = len(manager.layers) - 1
        for layer in base_manager.layers:
            self.layer_keys.setdefault(layer.uid, {0})
        if not self.frame_markers and self.frames:
            self.frame_markers = {0}

    def _refresh_frame_markers(self) -> None:
        markers: Set[int] = set()
        for frames in self.layer_keys.values():
            markers.update(frames)
        if markers:
            self.frame_markers = markers
        elif self.frames:
            self.frame_markers = {0}
        else:
            self.frame_markers = set()

    @staticmethod
    def _find_layer_index(layer_manager: LayerManager, layer_uid: int) -> Optional[int]:
        for index, layer in enumerate(layer_manager.layers):
            if getattr(layer, "uid", None) == layer_uid:
                return index
        return None

    @staticmethod
    def _find_layer(layer_manager: LayerManager, layer_uid: int) -> Optional[Layer]:
        index = FrameManager._find_layer_index(layer_manager, layer_uid)
        if index is None:
            return None
        return layer_manager.layers[index]

    def _clone_layer_state(
        self, layer_uid: int, source_frame_index: int, target_frame_index: int
    ) -> None:
        if not (0 <= source_frame_index < len(self.frames)):
            return
        if not (0 <= target_frame_index < len(self.frames)):
            return
        source_manager = self.frames[source_frame_index].layer_manager
        target_manager = self.frames[target_frame_index].layer_manager
        source_layer = self._find_layer(source_manager, layer_uid)
        if source_layer is None:
            return
        target_layer = self._find_layer(target_manager, layer_uid)
        if target_layer is None:
            index = self._find_layer_index(source_manager, layer_uid)
            if index is None:
                return
            clone = source_layer.clone()
            target_manager.layers.insert(index, clone)
            target_layer = clone
        elif target_layer is source_layer:
            index = self._find_layer_index(source_manager, layer_uid)
            if index is None:
                return
            clone = source_layer.clone()
            target_manager.layers[index] = clone
            target_layer = clone
        if target_layer is source_layer:
            return
        target_layer.apply_key_state_from(source_layer)

    def _copy_layer_between_layers(
        self, source_uid: int, target_uid: int, frame_index: int
    ) -> None:
        if not (0 <= frame_index < len(self.frames)):
            return
        manager = self.frames[frame_index].layer_manager
        source_layer = self._find_layer(manager, source_uid)
        target_layer = self._find_layer(manager, target_uid)
        if source_layer is None or target_layer is None or source_layer is target_layer:
            return
        target_layer.apply_key_state_from(source_layer)

    @staticmethod
    def _resolve_layer_key_from_set(keys: List[int], frame_index: int) -> Optional[int]:
        if not keys:
            return None
        position = bisect_right(keys, frame_index)
        if position:
            return keys[position - 1]
        return keys[0]

    def _rebind_layer_fallbacks(self, layer_uid: int) -> None:
        if not self.frames:
            return
        keys = self.layer_keys.get(layer_uid)
        if not keys:
            return
        for frame_index, frame in enumerate(self.frames):
            fallback_index = self.resolve_layer_key_frame_index(layer_uid, frame_index)
            if fallback_index is None:
                continue
            if not (0 <= fallback_index < len(self.frames)):
                continue
            source_manager = self.frames[fallback_index].layer_manager
            target_manager = frame.layer_manager
            source_layer = self._find_layer(source_manager, layer_uid)
            if source_layer is None:
                continue
            source_index = self._find_layer_index(source_manager, layer_uid)
            if source_index is None:
                continue
            if frame_index == fallback_index:
                # Ensure the keyed frame hosts the layer entry.
                if self._find_layer(target_manager, layer_uid) is None:
                    clone = source_layer.clone()
                    target_manager.layers.insert(source_index, clone)
                continue
            target_layer = self._find_layer(target_manager, layer_uid)
            if target_layer is source_layer:
                continue
            if target_layer is None:
                target_manager.layers.insert(source_index, source_layer)
            else:
                target_manager.layers[source_index] = source_layer

    def _rebind_all_layers(self) -> None:
        for layer_uid in list(self.layer_keys.keys()):
            self._rebind_layer_fallbacks(layer_uid)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
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
            if not self.frame_markers:
                self.frame_markers = {0}
            self._initialize_layer_keys()

        while len(self.frames) <= index:
            source_index = self.resolve_key_frame_index(len(self.frames))
            if source_index is None or not (0 <= source_index < len(self.frames)):
                source_index = len(self.frames) - 1
            source_frame = self.frames[source_index]
            self.frames.append(source_frame.clone())
        self._rebind_all_layers()

    def add_frame(self, frame: Optional[Frame] = None) -> Frame:
        if frame is None:
            frame = Frame(self.width, self.height)
        else:
            frame.layer_manager.width = self.width
            frame.layer_manager.height = self.height
        self.frames.append(frame)
        self.active_frame_index = len(self.frames) - 1
        if not self.frame_markers:
            self.frame_markers.add(self.active_frame_index)
        self._rebind_all_layers()
        return frame

    def insert_frame(self, index: int) -> Frame:
        if index < 0:
            index = 0
        if not self.frames:
            frame = Frame(self.width, self.height)
            self.frames.insert(0, frame)
            self.active_frame_index = 0
            if not self.frame_markers:
                self.frame_markers = {0}
            self._initialize_layer_keys()
            return frame

        if index > len(self.frames):
            index = len(self.frames)

        source_index = index - 1 if index > 0 else 0
        if source_index >= len(self.frames):
            source_index = len(self.frames) - 1
        source_frame = self.frames[source_index]
        new_frame = source_frame.clone()
        self.frames.insert(index, new_frame)

        if self.active_frame_index >= index:
            self.active_frame_index += 1

        updated_keys: Dict[int, Set[int]] = {}
        for layer_uid, frames in self.layer_keys.items():
            shifted: Set[int] = set()
            for frame_index in frames:
                if frame_index >= index:
                    shifted.add(frame_index + 1)
                else:
                    shifted.add(frame_index)
            if not shifted and self.frames:
                shifted = {0}
            updated_keys[layer_uid] = shifted
        self.layer_keys = updated_keys

        self._refresh_frame_markers()
        self._rebind_all_layers()
        return new_frame

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

        updated_keys: Dict[int, Set[int]] = {}
        for layer_uid, frames in self.layer_keys.items():
            shifted: Set[int] = set()
            for frame_index in frames:
                if frame_index == index:
                    continue
                if frame_index > index:
                    shifted.add(frame_index - 1)
                else:
                    shifted.add(frame_index)
            if not shifted and self.frames:
                shifted = {0}
            updated_keys[layer_uid] = shifted
        self.layer_keys = updated_keys
        self._refresh_frame_markers()
        self._rebind_all_layers()

        resolved = self.resolve_key_frame_index(self.active_frame_index)
        if resolved is None and self.frame_markers:
            self.active_frame_index = min(self.frame_markers)

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
        cloned_manager.frame_markers = set(self.frame_markers)
        cloned_manager.layer_keys = {
            layer_uid: set(frames) for layer_uid, frames in self.layer_keys.items()
        }
        return cloned_manager

    # ------------------------------------------------------------------
    # Keyframe helpers
    # ------------------------------------------------------------------
    def layer_key_frames(self, layer_uid: int) -> List[int]:
        keys = self.layer_keys.get(layer_uid)
        if not keys:
            return [0]
        return sorted(keys)

    def set_layer_key_frames(self, layer_uid: int, frames: Iterable[int]) -> bool:
        if layer_uid not in self.layer_keys:
            return False
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
            normalized = {0}
        existing = self.layer_keys.get(layer_uid, {0})
        if normalized == existing:
            return False

        previous_keys = sorted(existing)
        self.layer_keys[layer_uid] = normalized
        for key in sorted(normalized):
            if key in previous_keys:
                continue
            fallback = self._resolve_layer_key_from_set(previous_keys, key)
            if fallback is None:
                fallback = key
            self._clone_layer_state(layer_uid, fallback, key)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(layer_uid)
        return True

    def add_layer_key(self, layer_uid: int, index: int) -> bool:
        if index < 0:
            return False
        self.ensure_frame(index)
        if not (0 <= index < len(self.frames)):
            return False
        keys = self.layer_keys.setdefault(layer_uid, {0})
        if index in keys:
            return False
        source_index = self.resolve_layer_key_frame_index(layer_uid, index)
        if source_index is None:
            source_index = 0
        self._clone_layer_state(layer_uid, source_index, index)
        keys.add(index)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(layer_uid)
        return True

    def remove_layer_key(self, layer_uid: int, index: int) -> bool:
        keys = self.layer_keys.get(layer_uid)
        if keys is None or index not in keys:
            return False
        if len(keys) == 1 or index == 0:
            return False
        remaining = sorted(frame for frame in keys if frame != index)
        fallback = self._resolve_layer_key_from_set(remaining, index)
        keys.remove(index)
        if fallback is not None:
            self._clone_layer_state(layer_uid, fallback, index)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(layer_uid)
        return True

    def duplicate_layer_key(
        self,
        layer_uid: int,
        source_index: Optional[int] = None,
        target_index: Optional[int] = None,
    ) -> Optional[int]:
        keys = self.layer_keys.get(layer_uid)
        if not keys:
            return None
        if source_index is None:
            source_index = max(keys)
        elif source_index not in keys:
            return None
        if source_index is None:
            return None
        if target_index is None:
            candidate = source_index + 1
            while candidate in keys:
                candidate += 1
            target_index = candidate
        if target_index is None or target_index < 0:
            return None
        self.ensure_frame(target_index)
        if not (0 <= target_index < len(self.frames)):
            return None
        if target_index in keys:
            return None
        self._clone_layer_state(layer_uid, source_index, target_index)
        keys.add(target_index)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(layer_uid)
        return target_index

    def clone_layer_key_state(self, layer_uid: int, frame_index: int) -> Optional[Layer]:
        keys = self.layer_keys.get(layer_uid)
        if not keys or frame_index not in keys:
            return None
        if not (0 <= frame_index < len(self.frames)):
            return None
        manager = self.frames[frame_index].layer_manager
        layer = self._find_layer(manager, layer_uid)
        if layer is None:
            return None
        return layer.clone(preserve_identity=False)

    def paste_layer_key(self, layer_uid: int, frame_index: int, key_state: Layer) -> bool:
        if frame_index < 0:
            return False
        self.ensure_frame(frame_index)
        if not (0 <= frame_index < len(self.frames)):
            return False
        keys = self.layer_keys.setdefault(layer_uid, {0})
        if frame_index not in keys:
            self.add_layer_key(layer_uid, frame_index)
        manager = self.frames[frame_index].layer_manager
        layer = self._find_layer(manager, layer_uid)
        if layer is None:
            return False
        layer.apply_key_state_from(key_state)
        self._rebind_layer_fallbacks(layer_uid)
        self._refresh_frame_markers()
        return True

    def register_new_layer(
        self,
        layer: Layer,
        index: Optional[int] = None,
        *,
        key_frames: Optional[Iterable[int]] = None,
    ) -> None:
        if not self.frames:
            self.frames.append(Frame(self.width, self.height))
            self.active_frame_index = 0
            self._initialize_layer_keys()
        base_frame_index = self.resolve_key_frame_index(self.active_frame_index)
        if base_frame_index is None:
            base_frame_index = 0
        base_manager = self.frames[base_frame_index].layer_manager
        if index is None:
            try:
                index = base_manager.layers.index(layer)
            except ValueError:
                index = len(base_manager.layers)
        target_active_index = max(0, index if index is not None else 0)
        for frame in self.frames:
            manager = frame.layer_manager
            insertion_index = index if index is not None else len(manager.layers)
            if insertion_index < 0:
                insertion_index = 0
            if insertion_index > len(manager.layers):
                insertion_index = len(manager.layers)
            if self._find_layer(manager, layer.uid) is None:
                clone = layer.clone()
                manager.layers.insert(insertion_index, clone)
            if manager.layers:
                manager.active_layer_index = min(
                    target_active_index, len(manager.layers) - 1
                )
        keys = {0} if key_frames is None else {max(0, int(value)) for value in key_frames}
        if not keys:
            keys = {0}
        self.layer_keys[layer.uid] = keys
        primary_key = min(keys)
        if 0 <= primary_key < len(self.frames):
            primary_manager = self.frames[primary_key].layer_manager
            base_index = self._find_layer_index(base_manager, layer.uid)
            if base_index is not None:
                if self._find_layer(primary_manager, layer.uid) is None:
                    primary_manager.layers.insert(base_index, layer)
                else:
                    primary_manager.layers[base_index] = layer
        for key in sorted(keys):
            self.ensure_frame(key)
            if key == primary_key:
                continue
            self._clone_layer_state(layer.uid, base_frame_index, key)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(layer.uid)

    def unregister_layer(self, layer_uid: int) -> None:
        for frame in self.frames:
            manager = frame.layer_manager
            index = self._find_layer_index(manager, layer_uid)
            if index is None:
                continue
            del manager.layers[index]
            if manager.active_layer_index >= len(manager.layers):
                manager.active_layer_index = max(0, len(manager.layers) - 1)
        self.layer_keys.pop(layer_uid, None)
        self._refresh_frame_markers()

    def duplicate_layer_keys(self, source_uid: int, new_layer: Layer) -> None:
        manager = self.current_layer_manager
        if manager is None:
            return
        try:
            index = manager.layers.index(new_layer)
        except ValueError:
            index = len(manager.layers) - 1
        source_keys = self.layer_keys.get(source_uid, {0})
        self.register_new_layer(new_layer, index=index, key_frames=source_keys)
        for frame_index in source_keys:
            self.ensure_frame(frame_index)
            self._copy_layer_between_layers(source_uid, new_layer.uid, frame_index)
        self._refresh_frame_markers()
        self._rebind_layer_fallbacks(new_layer.uid)

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------
    def resolve_key_frame_index(self, frame_index: Optional[int] = None) -> Optional[int]:
        if not self.frames or not self.frame_markers:
            return None
        if frame_index is None:
            frame_index = self.active_frame_index
        if frame_index < 0:
            frame_index = 0
        if frame_index >= len(self.frames):
            frame_index = len(self.frames) - 1

        sorted_keys = sorted(self.frame_markers)
        position = bisect_right(sorted_keys, frame_index)
        if position:
            return sorted_keys[position - 1]
        return sorted_keys[0]

    def resolve_layer_key_frame_index(
        self, layer_uid: int, frame_index: Optional[int] = None
    ) -> Optional[int]:
        keys = self.layer_keys.get(layer_uid)
        if not keys:
            return None
        if frame_index is None:
            frame_index = self.active_frame_index
        if frame_index < 0:
            frame_index = 0
        if frame_index >= len(self.frames):
            frame_index = len(self.frames) - 1
        sorted_keys = sorted(keys)
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
