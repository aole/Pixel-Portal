import types

from PySide6.QtWidgets import QMainWindow

from portal.commands.tool_bar_builder import ToolBarBuilder
from portal.core.drawing_context import DrawingContext
from portal.tools.basetool import BaseTool


def test_toolbar_groups_tools_by_category(qapp, monkeypatch):
    main_window = QMainWindow()
    main_window.action_manager = types.SimpleNamespace()
    main_window.add_color_to_palette = lambda *args, **kwargs: None

    app = types.SimpleNamespace(drawing_context=DrawingContext())
    builder = ToolBarBuilder(main_window, app)

    class DummyDrawTool(BaseTool):
        name = "DummyDraw"
        icon = "icons/toolpen.png"
        shortcut = "1"
        category = "draw"

    class DummyShapeTool(BaseTool):
        name = "DummyShape"
        icon = "icons/toolline.png"
        shortcut = "2"
        category = "shape"

    class DummySelectTool(BaseTool):
        name = "DummySelect"
        icon = "icons/toolselectrect.png"
        shortcut = "3"
        category = "select"

    from portal.tools import registry as tool_registry

    real_get_tools = tool_registry.get_tools

    def fake_get_tools():
        tools = real_get_tools()
        tools.extend(
            [
                {
                    "class": DummyDrawTool,
                    "name": DummyDrawTool.name,
                    "icon": DummyDrawTool.icon,
                    "shortcut": DummyDrawTool.shortcut,
                    "category": DummyDrawTool.category,
                },
                {
                    "class": DummyShapeTool,
                    "name": DummyShapeTool.name,
                    "icon": DummyShapeTool.icon,
                    "shortcut": DummyShapeTool.shortcut,
                    "category": DummyShapeTool.category,
                },
                {
                    "class": DummySelectTool,
                    "name": DummySelectTool.name,
                    "icon": DummySelectTool.icon,
                    "shortcut": DummySelectTool.shortcut,
                    "category": DummySelectTool.category,
                },
            ]
        )
        return tools

    monkeypatch.setattr(tool_registry, "get_tools", fake_get_tools)

    builder._setup_left_toolbar()

    # Direct tools are added as actions on the toolbar
    assert DummyDrawTool.name in builder.tool_actions

    shape_actions = [a.text() for a in builder.main_window.shape_button.menu().actions()]
    selection_actions = [a.text() for a in builder.main_window.selection_button.menu().actions()]

    assert DummyShapeTool.name in shape_actions
    assert DummySelectTool.name in selection_actions
    assert DummyDrawTool.name not in shape_actions + selection_actions
