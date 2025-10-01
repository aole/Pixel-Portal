"""Unit tests for :mod:`portal.commands.canvas_input_handler`."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from PySide6.QtCore import Qt

from portal.commands.canvas_input_handler import CanvasInputHandler


class FakeKeyEvent:
    """Minimal stand-in for :class:`QKeyEvent`."""

    def __init__(self, key: int, text: str = ""):
        self._key = key
        self._text = text

    def key(self) -> int:
        return self._key

    def text(self) -> str:
        return self._text


@dataclass
class DummyTool:
    name: str
    category: str | None = None
    shortcut: str | None = None

    cursor = None
    requires_visible_layer = True


class FakeDrawingContext:
    def __init__(self, tool: str):
        self.tool = tool
        self.previous_tool: str | None = None

    def set_tool(self, tool: str):
        if self.tool == tool:
            return
        self.previous_tool = self.tool
        self.tool = tool


class DummyCanvas:
    def __init__(self, drawing_context: FakeDrawingContext, current_tool):
        self.drawing_context = drawing_context
        self.current_tool = current_tool
        self.tools: dict[str, DummyTool] = {}


@pytest.fixture
def non_selection_canvas() -> DummyCanvas:
    drawing_context = FakeDrawingContext("Pen")
    current_tool = DummyTool(name="Pen", category="draw")
    return DummyCanvas(drawing_context, current_tool)


@pytest.fixture
def selection_canvas() -> DummyCanvas:
    drawing_context = FakeDrawingContext("Select Rectangle")
    current_tool = DummyTool(name="Select Rectangle", category="select")
    return DummyCanvas(drawing_context, current_tool)


def test_alt_forces_picker_temporarily(non_selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(non_selection_canvas)
    event = FakeKeyEvent(Qt.Key_Alt)

    handler.keyPressEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Picker"

    handler.keyReleaseEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Pen"


def test_ctrl_does_not_force_tool_temporarily(non_selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(non_selection_canvas)
    event = FakeKeyEvent(Qt.Key_Control)

    handler.keyPressEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Pen"

    handler.keyReleaseEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Pen"


def test_alt_does_not_override_selection_tool(selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(selection_canvas)
    event = FakeKeyEvent(Qt.Key_Alt)

    handler.keyPressEvent(event)
    assert selection_canvas.drawing_context.tool == "Select Rectangle"

    handler.keyReleaseEvent(event)
    assert selection_canvas.drawing_context.tool == "Select Rectangle"


def test_ctrl_does_not_override_selection_tool(selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(selection_canvas)
    event = FakeKeyEvent(Qt.Key_Control)

    handler.keyPressEvent(event)
    assert selection_canvas.drawing_context.tool == "Select Rectangle"

    handler.keyReleaseEvent(event)
    assert selection_canvas.drawing_context.tool == "Select Rectangle"


def test_manual_tool_switch_during_modifier_press_is_respected(non_selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(non_selection_canvas)
    event = FakeKeyEvent(Qt.Key_Alt)

    handler.keyPressEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Picker"

    # Simulate the user choosing a different tool while still holding Alt.
    non_selection_canvas.drawing_context.set_tool("Eraser")

    handler.keyReleaseEvent(event)
    assert non_selection_canvas.drawing_context.tool == "Eraser"


def test_group_shortcut_cycles_tools(non_selection_canvas: DummyCanvas):
    handler = CanvasInputHandler(non_selection_canvas)
    non_selection_canvas.tools = {
        "Pen": DummyTool(name="Pen", shortcut="b"),
        "Rectangle": DummyTool(name="Rectangle", shortcut="s"),
        "Ellipse": DummyTool(name="Ellipse", shortcut="s"),
    }
    non_selection_canvas.drawing_context.set_tool("Rectangle")

    handler.set_tool_shortcut_groups({"s": ["Rectangle", "Ellipse"]})

    handler.keyPressEvent(FakeKeyEvent(Qt.Key_S, "s"))
    assert non_selection_canvas.drawing_context.tool == "Ellipse"

    handler.keyPressEvent(FakeKeyEvent(Qt.Key_S, "s"))
    assert non_selection_canvas.drawing_context.tool == "Rectangle"
