from __future__ import annotations

import types

from PySide6.QtWidgets import QMainWindow

from portal.commands.tool_bar_builder import ToolBarBuilder
from portal.core.drawing_context import DrawingContext
from portal.tools.basetool import BaseTool


def test_toolbar_layout_config_drives_tool_buttons(qapp, monkeypatch):
    main_window = QMainWindow()
    main_window.action_manager = types.SimpleNamespace()
    main_window.add_color_to_palette = lambda *args, **kwargs: None

    captured_groups: dict[str, list[str]] = {}

    class DummyInputHandler:
        def set_tool_shortcut_groups(self, groups):
            captured_groups.clear()
            captured_groups.update(groups)

    main_window.canvas = types.SimpleNamespace(
        input_handler=DummyInputHandler()
    )

    app = types.SimpleNamespace(drawing_context=DrawingContext())
    builder = ToolBarBuilder(main_window, app)

    class DummyDrawTool(BaseTool):
        name = "DummyDraw"
        icon = "icons/toolpen.png"
        shortcut = "1"
        category = "draw"

    class DummyShapeOneTool(BaseTool):
        name = "DummyShapeOne"
        icon = "icons/toolline.png"
        shortcut = "s"
        category = "shape"

    class DummyShapeTwoTool(BaseTool):
        name = "DummyShapeTwo"
        icon = "icons/toolellipse.png"
        shortcut = "s"
        category = "shape"

    class DummySelectTool(BaseTool):
        name = "DummySelect"
        icon = "icons/toolselectrect.png"
        shortcut = "v"
        category = "select"

    class DummySelectTwoTool(BaseTool):
        name = "DummySelectTwo"
        icon = "icons/toolselectcircle.png"
        shortcut = "v"
        category = "select"

    class DummyExtraTool(BaseTool):
        name = "DummyExtra"
        icon = "icons/toolbucket.png"
        shortcut = "6"
        category = "draw"

    from portal.tools import registry as tool_registry

    def fake_get_tools():
        return [
            {
                "class": DummyDrawTool,
                "name": DummyDrawTool.name,
                "icon": DummyDrawTool.icon,
                "shortcut": DummyDrawTool.shortcut,
                "category": DummyDrawTool.category,
            },
            {
                "class": DummyShapeOneTool,
                "name": DummyShapeOneTool.name,
                "icon": DummyShapeOneTool.icon,
                "shortcut": DummyShapeOneTool.shortcut,
                "category": DummyShapeOneTool.category,
            },
            {
                "class": DummyShapeTwoTool,
                "name": DummyShapeTwoTool.name,
                "icon": DummyShapeTwoTool.icon,
                "shortcut": DummyShapeTwoTool.shortcut,
                "category": DummyShapeTwoTool.category,
            },
            {
                "class": DummySelectTool,
                "name": DummySelectTool.name,
                "icon": DummySelectTool.icon,
                "shortcut": DummySelectTool.shortcut,
                "category": DummySelectTool.category,
            },
            {
                "class": DummySelectTwoTool,
                "name": DummySelectTwoTool.name,
                "icon": DummySelectTwoTool.icon,
                "shortcut": DummySelectTwoTool.shortcut,
                "category": DummySelectTwoTool.category,
            },
            {
                "class": DummyExtraTool,
                "name": DummyExtraTool.name,
                "icon": DummyExtraTool.icon,
                "shortcut": DummyExtraTool.shortcut,
                "category": DummyExtraTool.category,
            },
        ]

    monkeypatch.setattr(tool_registry, "get_tools", fake_get_tools)

    layout = [
        {
            "name": "Shape Tools",
            "icon": "icons/toolrect.png",
            "tools": [
                {"name": DummyShapeOneTool.name, "icon": DummyShapeOneTool.icon},
                {"name": DummyShapeTwoTool.name, "icon": DummyShapeTwoTool.icon},
            ],
        },
        {
            "name": "Selection Tools",
            "icon": "icons/toolselectrect.png",
            "tools": [
                {"name": DummySelectTool.name, "icon": DummySelectTool.icon},
                {"name": DummySelectTwoTool.name, "icon": DummySelectTwoTool.icon},
            ],
        },
        {
            "name": "Dummy Draw",
            "icon": DummyDrawTool.icon,
            "tools": [
                {"name": DummyDrawTool.name, "icon": DummyDrawTool.icon},
            ],
        },
    ]

    def fake_load_layout(self, tools_by_name):
        return layout

    monkeypatch.setattr(ToolBarBuilder, "_load_toolbar_layout", fake_load_layout)

    builder._setup_left_toolbar()

    assert DummyDrawTool.name in builder.tool_actions

    shape_button = builder.tool_buttons[DummyShapeOneTool.name]
    assert shape_button is builder.tool_buttons[DummyShapeTwoTool.name]
    shape_action_names = [action.text() for action in shape_button.menu().actions()]
    assert shape_action_names == [DummyShapeOneTool.name, DummyShapeTwoTool.name]
    assert shape_button.toolTip() == "Shape Tools (S)"

    selection_button = builder.tool_buttons[DummySelectTool.name]
    assert selection_button is builder.tool_buttons[DummySelectTwoTool.name]
    selection_action_names = [action.text() for action in selection_button.menu().actions()]
    assert selection_action_names == [DummySelectTool.name, DummySelectTwoTool.name]
    assert selection_button.toolTip() == "Selection Tools (V)"

    direct_button = builder.tool_buttons[DummyDrawTool.name]
    assert direct_button.menu() is None

    extra_button = builder.tool_buttons[DummyExtraTool.name]
    assert extra_button.menu() is None

    builder.update_tool_buttons(DummyShapeTwoTool.name)
    assert shape_button.defaultAction().text() == DummyShapeTwoTool.name
    assert shape_button.toolTip() == "Shape Tools (S)"

    builder.update_tool_buttons(DummySelectTwoTool.name)
    assert selection_button.defaultAction().text() == DummySelectTwoTool.name
    assert selection_button.toolTip() == "Selection Tools (V)"

    assert captured_groups == {
        "s": [DummyShapeOneTool.name, DummyShapeTwoTool.name],
        "v": [DummySelectTool.name, DummySelectTwoTool.name],
    }
