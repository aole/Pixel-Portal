from __future__ import annotations

from typing import Iterable, Mapping, Optional

from portal.core.command import Command
from portal.core.document import Document
from portal.core.frame_manager import FrameManager
from portal.core.layer import Layer


class _KeyframeCommand(Command):
    """Base helper that snapshots keyframe state for undo/redo."""

    def __init__(self, document: Document):
        self.document = document
        self._previous_state: FrameManager | None = None

    def _capture_before(self) -> None:
        if self._previous_state is None:
            self._previous_state = self.document.frame_manager.clone(deep_copy=True)

    def undo(self) -> None:
        if self._previous_state is None:
            return
        self.document.apply_frame_manager_snapshot(self._previous_state)


class AddKeyframeCommand(_KeyframeCommand):
    """Add a keyframe at ``frame_index``."""

    def __init__(self, document: Document, frame_index: int):
        super().__init__(document)
        self.frame_index = frame_index

    def execute(self) -> None:
        self._capture_before()
        self.document.add_key_frame(self.frame_index)


class RemoveKeyframeCommand(_KeyframeCommand):
    """Remove a keyframe at ``frame_index`` if possible."""

    def __init__(self, document: Document, frame_index: int):
        super().__init__(document)
        self.frame_index = frame_index

    def execute(self) -> None:
        self._capture_before()
        self.document.remove_key_frame(self.frame_index)


class SetKeyframesCommand(_KeyframeCommand):
    """Replace the active layer's keyframes with ``frames``."""

    def __init__(self, document: Document, frames: Iterable[int]):
        super().__init__(document)
        normalized: set[int] = set()
        for value in frames:
            try:
                frame = int(value)
            except (TypeError, ValueError):
                continue
            if frame < 0:
                continue
            normalized.add(frame)
        if not normalized:
            normalized = {0}
        self.frames = sorted(normalized)

    def execute(self) -> None:
        self._capture_before()
        self.document.set_key_frames(self.frames)


class MoveKeyframesCommand(_KeyframeCommand):
    """Move existing keyframes according to ``moves`` mapping."""

    def __init__(self, document: Document, moves: Mapping[int, int]):
        super().__init__(document)
        normalized: dict[int, int] = {}
        for source, target in moves.items():
            try:
                source_index = int(source)
                target_index = int(target)
            except (TypeError, ValueError):
                continue
            if source_index < 0 or target_index < 0:
                continue
            normalized[source_index] = target_index
        self.moves = normalized

    def execute(self) -> None:
        if not self.moves:
            return
        self._capture_before()
        self.document.move_key_frames(self.moves)


class InsertFrameCommand(_KeyframeCommand):
    """Insert a new frame at ``frame_index``."""

    def __init__(self, document: Document, frame_index: int):
        super().__init__(document)
        self.frame_index = frame_index

    def execute(self) -> None:
        self._capture_before()
        self.document.insert_frame(self.frame_index)


class DeleteFrameCommand(_KeyframeCommand):
    """Delete the frame at ``frame_index`` if allowed."""

    def __init__(self, document: Document, frame_index: int):
        super().__init__(document)
        self.frame_index = frame_index

    def execute(self) -> None:
        self._capture_before()
        self.document.remove_frame(self.frame_index)


class DuplicateKeyframeCommand(_KeyframeCommand):
    """Duplicate an existing keyframe to another frame index."""

    def __init__(
        self,
        document: Document,
        source_frame: Optional[int] = None,
        target_frame: Optional[int] = None,
    ) -> None:
        super().__init__(document)
        self.source_frame = source_frame
        self.target_frame = target_frame
        self.created_frame: Optional[int] = None

    def execute(self) -> None:
        self._capture_before()
        target = self.target_frame if self.target_frame is not None else self.created_frame
        result = self.document.duplicate_key_frame(self.source_frame, target)
        if result is not None:
            self.created_frame = result


class DuplicateKeyframesCommand(_KeyframeCommand):
    """Duplicate multiple keyframes by ``offset``."""

    def __init__(self, document: Document, frames: Iterable[int], offset: int) -> None:
        super().__init__(document)
        normalized: list[int] = []
        for value in frames:
            try:
                frame = int(value)
            except (TypeError, ValueError):
                continue
            normalized.append(frame)
        self.frames = sorted(set(normalized))
        try:
            self.offset = int(offset)
        except (TypeError, ValueError):
            self.offset = 0

    def execute(self) -> None:
        if not self.frames or not self.offset:
            return
        self._capture_before()
        self.document.duplicate_key_frames_with_offset(self.frames, self.offset)


class PasteKeyframeCommand(_KeyframeCommand):
    """Paste copied keyframe data onto ``frame_index``."""

    def __init__(self, document: Document, frame_index: int, key_state: Layer) -> None:
        super().__init__(document)
        self.frame_index = frame_index
        self.key_state = key_state
        self.applied = False

    def execute(self) -> None:
        self._capture_before()
        self.applied = self.document.paste_key_frame(self.frame_index, self.key_state)
