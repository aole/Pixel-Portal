from __future__ import annotations

from typing import Optional

from portal.core.command import Command
from portal.core.document import Document
from portal.core.frame_manager import FrameManager


class _KeyframeCommand(Command):
    """Base helper that snapshots keyframe state for undo/redo."""

    def __init__(self, document: Document):
        self.document = document
        self._previous_state: FrameManager | None = None

    def _capture_before(self) -> None:
        if self._previous_state is None:
            self._previous_state = self.document.frame_manager.clone()

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
