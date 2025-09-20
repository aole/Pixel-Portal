import functools
import json
from importlib import resources
from pathlib import Path

from PySide6.QtWidgets import QToolBar, QLabel, QSlider, QToolButton, QMenu
from PySide6.QtGui import QPixmap, QIcon, QAction, QActionGroup
from PySide6.QtCore import Qt
from portal.ui.color_button import ActiveColorButton

class ToolBarBuilder:
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.action_manager = main_window.action_manager
        self.top_toolbar = None
        self.left_toolbar = None
        self.tool_actions = {}
        self.tool_action_group = None
        self.tool_buttons = {}
        self._button_fallback_icons = {}

    def setup_toolbars(self):
        self._setup_top_toolbar()
        self._setup_left_toolbar()

    def _setup_top_toolbar(self):
        self.top_toolbar = QToolBar("Top Toolbar")
        self.main_window.addToolBar(Qt.TopToolBarArea, self.top_toolbar)

        self.top_toolbar.addAction(self.action_manager.new_action)
        self.top_toolbar.addAction(self.action_manager.open_action)
        self.top_toolbar.addAction(self.action_manager.save_action)
        self.top_toolbar.addSeparator()

        # Brush size slider
        brush_icon = QLabel()
        pixmap = QPixmap("icons/brush.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        brush_icon.setPixmap(pixmap)
        self.top_toolbar.addWidget(brush_icon)

        self.main_window.pen_width_label = QLabel(f"{self.app.drawing_context.pen_width:02d}")
        self.top_toolbar.addWidget(self.main_window.pen_width_label)

        self.main_window.pen_width_slider = QSlider(Qt.Horizontal)
        self.main_window.pen_width_slider.setRange(1, 64)
        self.main_window.pen_width_slider.setValue(self.app.drawing_context.pen_width)
        self.main_window.pen_width_slider.setMinimumWidth(32)
        self.main_window.pen_width_slider.setMaximumWidth(100)
        self.main_window.pen_width_slider.setSingleStep(1)
        self.main_window.pen_width_slider.setPageStep(1)
        self.main_window.pen_width_slider.valueChanged.connect(self.app.drawing_context.set_pen_width)
        self.top_toolbar.addWidget(self.main_window.pen_width_slider)

        self.action_manager.circular_brush_action.setChecked(self.app.drawing_context.brush_type == "Circular")
        self.action_manager.circular_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Circular"))
        self.top_toolbar.addAction(self.action_manager.circular_brush_action)

        self.action_manager.square_brush_action.setChecked(self.app.drawing_context.brush_type == "Square")
        self.action_manager.square_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Square"))
        self.top_toolbar.addAction(self.action_manager.square_brush_action)

        self.action_manager.pattern_brush_action.setChecked(self.app.drawing_context.brush_type == "Pattern")
        self.action_manager.pattern_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Pattern"))
        self.top_toolbar.addAction(self.action_manager.pattern_brush_action)

        self.top_toolbar.addSeparator()

        self.top_toolbar.addAction(self.action_manager.mirror_x_action)
        self.top_toolbar.addAction(self.action_manager.mirror_y_action)

        self.top_toolbar.addSeparator()

        self.top_toolbar.addAction(self.action_manager.ruler_action)

        self.action_manager.grid_action.triggered.connect(self.main_window.canvas.toggle_grid)
        self.top_toolbar.addAction(self.action_manager.grid_action)

    def _setup_left_toolbar(self):
        self.left_toolbar = QToolBar("Tools")
        self.main_window.addToolBar(Qt.LeftToolBarArea, self.left_toolbar)
        self.left_toolbar.layout().setAlignment(Qt.AlignLeft)

        active_color_button = ActiveColorButton(self.app.drawing_context)
        active_color_button.rightClicked.connect(self.main_window.add_color_to_palette)
        self.left_toolbar.addWidget(active_color_button)

        from portal.tools import registry

        tools = registry.get_tools()
        tools_by_name = {tool["name"]: tool for tool in tools}

        self.tool_actions = {}
        self.tool_buttons = {}
        self._button_fallback_icons = {}
        self.tool_action_group = QActionGroup(self.main_window)
        self.tool_action_group.setExclusive(True)

        configured_tools = set()
        toolbar_layout = self._load_toolbar_layout(tools_by_name)

        for entry in toolbar_layout:
            normalized_tools = []
            for tool_spec in entry.get("tools", []):
                if isinstance(tool_spec, str):
                    tool_name = tool_spec
                    icon_path = None
                else:
                    tool_name = tool_spec.get("name")
                    icon_path = tool_spec.get("icon")
                tool = tools_by_name.get(tool_name)
                if not tool:
                    continue
                action = self._get_or_create_tool_action(tool)
                normalized_tools.append(
                    {
                        "name": tool_name,
                        "action": action,
                        "icon": icon_path,
                    }
                )

            if not normalized_tools:
                continue

            entry_name = entry.get("name") or normalized_tools[0]["name"]
            entry_icon = entry.get("icon")

            if len(normalized_tools) == 1:
                tool_info = normalized_tools[0]
                button = QToolButton(self.main_window)
                button.setToolTip(entry_name)
                action = tool_info["action"]
                button.setDefaultAction(action)

                fallback_icon = entry_icon or tool_info.get("icon")
                icon = action.icon()
                if icon.isNull():
                    if fallback_icon:
                        button.setIcon(QIcon(fallback_icon))
                else:
                    button.setIcon(icon)
                if fallback_icon:
                    self._button_fallback_icons[button] = fallback_icon

                self.left_toolbar.addWidget(button)
                self.tool_buttons[tool_info["name"]] = button
                configured_tools.add(tool_info["name"])
            else:
                button = QToolButton(self.main_window)
                button.setToolTip(entry_name)
                button.setPopupMode(QToolButton.MenuButtonPopup)
                menu = QMenu(button)
                button.setMenu(menu)

                first_action = None
                for tool_info in normalized_tools:
                    action = tool_info["action"]
                    menu.addAction(action)
                    if first_action is None:
                        first_action = action
                    self.tool_buttons[tool_info["name"]] = button
                    configured_tools.add(tool_info["name"])

                if not first_action:
                    continue

                button.setDefaultAction(first_action)

                fallback_icon = entry_icon or normalized_tools[0].get("icon")
                icon = first_action.icon()
                if icon.isNull():
                    if fallback_icon:
                        button.setIcon(QIcon(fallback_icon))
                else:
                    button.setIcon(icon)
                if fallback_icon:
                    self._button_fallback_icons[button] = fallback_icon

                self.left_toolbar.addWidget(button)

        for tool in tools:
            tool_name = tool["name"]
            if tool_name in configured_tools:
                continue

            action = self._get_or_create_tool_action(tool)
            button = QToolButton(self.main_window)
            button.setToolTip(tool_name)
            button.setDefaultAction(action)

            fallback_icon = tool.get("icon")
            icon = action.icon()
            if icon.isNull():
                if fallback_icon:
                    button.setIcon(QIcon(fallback_icon))
            else:
                button.setIcon(icon)
            if fallback_icon:
                self._button_fallback_icons[button] = fallback_icon

            self.left_toolbar.addWidget(button)
            self.tool_buttons[tool_name] = button
            configured_tools.add(tool_name)

        current_tool = getattr(self.app.drawing_context, "tool", None)
        if current_tool:
            self.update_tool_buttons(current_tool)

    def _get_or_create_tool_action(self, tool):
        tool_name = tool["name"]
        if tool_name in self.tool_actions:
            return self.tool_actions[tool_name]

        icon_path = tool.get("icon") or ""
        action = QAction(QIcon(icon_path), tool_name, self.main_window)
        action.setCheckable(True)
        action.triggered.connect(
            functools.partial(self.app.drawing_context.set_tool, tool_name)
        )
        self.tool_actions[tool_name] = action
        self.tool_action_group.addAction(action)
        if getattr(self.app.drawing_context, "tool", None) == tool_name:
            action.setChecked(True)
        return action

    def update_tool_buttons(self, tool_name):
        action = self.tool_actions.get(tool_name)
        if action:
            action.setChecked(True)

        button = self.tool_buttons.get(tool_name)
        if not action or not button:
            return

        button.setDefaultAction(action)

        icon = action.icon()
        if icon.isNull():
            icon_path = self._button_fallback_icons.get(button)
            if icon_path:
                button.setIcon(QIcon(icon_path))
        else:
            button.setIcon(icon)

    def _load_toolbar_layout(self, tools_by_name):
        config = self._read_toolbar_config()
        if not config:
            return []

        layout_entries = config.get("left_toolbar", [])
        if not isinstance(layout_entries, list):
            return []

        normalized_entries = []
        for entry in layout_entries:
            if not isinstance(entry, dict):
                continue

            entry_copy = {
                "name": entry.get("name"),
                "icon": entry.get("icon"),
                "tools": [],
            }

            raw_tools = entry.get("tools", [])
            if not isinstance(raw_tools, list):
                continue

            for tool_spec in raw_tools:
                if isinstance(tool_spec, str):
                    tool_name = tool_spec
                    icon_path = None
                elif isinstance(tool_spec, dict):
                    tool_name = tool_spec.get("name")
                    icon_path = tool_spec.get("icon")
                else:
                    continue

                if not tool_name or tool_name not in tools_by_name:
                    continue

                entry_copy["tools"].append({"name": tool_name, "icon": icon_path})

            if not entry_copy["tools"]:
                continue

            normalized_entries.append(entry_copy)

        return normalized_entries

    def _read_toolbar_config(self):
        config_text = None

        try:
            resource_path = resources.files("portal").joinpath("config/toolbar_tools.json")
            config_text = resource_path.read_text(encoding="utf-8")
        except (FileNotFoundError, ModuleNotFoundError, AttributeError, OSError):
            pass

        if config_text is None:
            local_path = Path(__file__).resolve().parents[1] / "config" / "toolbar_tools.json"
            try:
                config_text = local_path.read_text(encoding="utf-8")
            except (FileNotFoundError, OSError):
                return None

        try:
            return json.loads(config_text)
        except json.JSONDecodeError:
            return None
