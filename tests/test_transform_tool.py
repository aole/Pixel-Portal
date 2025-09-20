from __future__ import annotations

from types import SimpleNamespace
from typing import List

import pytest
from PySide6.QtCore import QPoint, Qt

from portal.tools.basetool import BaseTool
from portal.tools.transformtool import TransformTool


class DummySignal:
    def __init__(self) -> None:
        self._callbacks: List = []

    def connect(self, callback):  # pragma: no cover - trivial proxy
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):  # pragma: no cover - unused in tests
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _BaseStubTool(BaseTool):
    command_generated = DummySignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.command_generated = DummySignal()

    def activate(self):  # pragma: no cover - no-op
        pass

    def deactivate(self):  # pragma: no cover - no-op
        pass

    def mousePressEvent(self, event, doc_pos):  # pragma: no cover - no-op
        pass

    def mouseMoveEvent(self, event, doc_pos):  # pragma: no cover - no-op
        pass

    def mouseReleaseEvent(self, event, doc_pos):  # pragma: no cover - override in subclasses
        pass

    def mouseHoverEvent(self, event, doc_pos):  # pragma: no cover - no-op
        pass

    def draw_overlay(self, painter):  # pragma: no cover - no-op
        pass


class StubMoveTool(_BaseStubTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.release_calls: List[tuple] = []

    def mouseReleaseEvent(self, event, doc_pos):
        self.release_calls.append((event, doc_pos))


class StubRotateTool(_BaseStubTool):
    angle_changed = DummySignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.angle_changed = DummySignal()
        self.drag_mode: str | None = None
        self.manual_pivot = False
        self.release_calls: List[tuple] = []
        self.refresh_calls: int = 0
        self.offset_calls: List[QPoint] = []

    def mouseReleaseEvent(self, event, doc_pos):
        self.release_calls.append((event, doc_pos))
        self.drag_mode = None

    def refresh_pivot_from_document(self):
        self.refresh_calls += 1

    def pivot_is_manual(self) -> bool:
        return self.manual_pivot

    def offset_pivot(self, delta: QPoint):
        self.offset_calls.append(QPoint(delta))


class StubScaleTool(_BaseStubTool):
    scale_changed = DummySignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.scale_changed = DummySignal()
        self.drag_mode: str | None = None
        self.release_calls: List[tuple] = []
        self.refresh_calls: int = 0

    def mouseReleaseEvent(self, event, doc_pos):
        self.release_calls.append((event, doc_pos))
        self.drag_mode = None

    def refresh_handles_from_document(self):
        self.refresh_calls += 1


class _DummyEvent:
    def __init__(self, button=Qt.LeftButton):
        self._button = button

    def button(self):
        return self._button


@pytest.fixture
def transform_fixture(qapp):
    canvas = SimpleNamespace()
    move = StubMoveTool(canvas)
    rotate = StubRotateTool(canvas)
    scale = StubScaleTool(canvas)
    tool = TransformTool(
        canvas,
        move_tool=move,
        rotate_tool=rotate,
        scale_tool=scale,
    )
    return SimpleNamespace(tool=tool, move=move, rotate=rotate, scale=scale)


def test_move_release_offsets_manual_pivot(transform_fixture):
    fixture = transform_fixture
    fixture.tool._active_operation = "move"
    fixture.rotate.manual_pivot = True
    fixture.move.start_point = QPoint(2, 3)

    event = _DummyEvent()
    fixture.tool.mouseReleaseEvent(event, QPoint(5, 9))

    assert fixture.rotate.offset_calls == [QPoint(3, 6)]
    assert fixture.rotate.refresh_calls == 0
    assert fixture.scale.refresh_calls == 1
    assert fixture.tool._active_operation is None


def test_move_release_recenters_auto_pivot(transform_fixture):
    fixture = transform_fixture
    fixture.tool._active_operation = "move"
    fixture.rotate.manual_pivot = False
    fixture.move.start_point = QPoint(10, 10)

    fixture.tool.mouseReleaseEvent(_DummyEvent(), QPoint(12, 14))

    assert fixture.rotate.offset_calls == []
    assert fixture.rotate.refresh_calls == 1
    assert fixture.scale.refresh_calls == 1


def test_rotate_release_refreshes_gizmos(transform_fixture):
    fixture = transform_fixture
    fixture.tool._active_operation = "rotate"
    fixture.rotate.drag_mode = "rotate"

    fixture.tool.mouseReleaseEvent(_DummyEvent(), QPoint(0, 0))

    assert fixture.scale.refresh_calls == 1
    assert fixture.rotate.refresh_calls == 1


def test_scale_release_refreshes_gizmos(transform_fixture):
    fixture = transform_fixture
    fixture.tool._active_operation = "scale"
    fixture.scale.drag_mode = "scale"

    fixture.tool.mouseReleaseEvent(_DummyEvent(), QPoint(1, 1))

    assert fixture.scale.refresh_calls == 1
    assert fixture.rotate.refresh_calls == 1

