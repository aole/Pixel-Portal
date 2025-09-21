import functools
import json
from importlib import resources
from pathlib import Path

from PySide6.QtWidgets import QToolBar, QLabel, QSlider, QToolButton, QMenu
from PySide6.QtGui import QPixmap, QIcon, QAction, QActionGroup, QKeySequence
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
        self._button_entry_names = {}
        self._button_actions_map = {}
        self._shortcut_groups = {}

    def setup_toolbars(self):
        self._setup_top_toolbar()
        self._setup_left_toolbar()

    def _format_shortcut_hint(self, shortcut):
        if not shortcut:
            return None

        sequence = QKeySequence(shortcut)
        text = sequence.toString(QKeySequence.NativeText)
        if text:
            return text

        if isinstance(shortcut, str):
            formatted = shortcut.strip()
            if formatted:
                return formatted.upper()

        return None

    def _action_display_text(self, action):
        if action is None:
            return ""

        text = (action.text() or "").replace("&", "").strip()
        if text:
            return text

        tooltip = action.toolTip()
        if tooltip:
            paren_index = tooltip.find("(")
            if paren_index > 0:
                return tooltip[:paren_index].strip()
            return tooltip.strip()

        return ""

    def _action_primary_hint(self, action):
        if action is None:
            return None

        hint = action.property("shortcut_hint")
        if hint is not None:
            hint_text = str(hint).strip()
            if hint_text:
                return hint_text

        shortcut = action.shortcut()
        if isinstance(shortcut, QKeySequence):
            if hasattr(shortcut, "isEmpty"):
                if not shortcut.isEmpty():
                    text = shortcut.toString(QKeySequence.NativeText)
                    if text:
                        return text
            else:
                text = shortcut.toString(QKeySequence.NativeText)
                if text:
                    return text
        elif shortcut:
            shortcut_text = str(shortcut).strip()
            if shortcut_text:
                return shortcut_text

        try:
            sequences = action.shortcuts()
        except AttributeError:
            sequences = []

        for sequence in sequences:
            if isinstance(sequence, QKeySequence):
                if hasattr(sequence, "isEmpty") and sequence.isEmpty():
                    continue
                text = sequence.toString(QKeySequence.NativeText)
            else:
                text = str(sequence).strip()
            if text:
                return text

        tooltip = action.toolTip()
        if tooltip:
            start = tooltip.rfind("(")
            end = tooltip.rfind(")")
            if start != -1 and end != -1 and end > start:
                candidate = tooltip[start + 1 : end].strip()
                if candidate:
                    return candidate

        return None

    def _button_tooltip_from_actions(self, entry_name, actions):
        if not actions:
            return entry_name or ""

        default_action = actions[0]

        if len(actions) == 1:
            tooltip = default_action.toolTip()
            if tooltip:
                return tooltip
            if entry_name:
                return entry_name
            return self._action_display_text(default_action)

        label = entry_name or self._action_display_text(default_action)
        hint = self._action_primary_hint(default_action)

        if label and hint:
            return f"{label} ({hint})"
        if label:
            return label
        if hint:
            return hint

        tooltip = default_action.toolTip()
        if tooltip:
            return tooltip

        return self._action_display_text(default_action)

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
        self.main_window.pen_width_slider.valueChanged.connect(
            self.main_window.on_width_slider_changed
        )
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
        self._shortcut_groups = {}
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
                        "shortcut": tool.get("shortcut"),
                    }
                )

            if not normalized_tools:
                continue

            entry_name = entry.get("name") or normalized_tools[0]["name"]
            entry_icon = entry.get("icon")

            if len(normalized_tools) == 1:
                tool_info = normalized_tools[0]
                button = QToolButton(self.main_window)
                action = tool_info["action"]
                button.setDefaultAction(action)

                entry_label = entry_name or tool_info["name"]
                self._button_entry_names[button] = entry_label
                self._button_actions_map[button] = [action]
                self._refresh_button_tooltip(button, action)

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
                button.setPopupMode(QToolButton.MenuButtonPopup)
                menu = QMenu(button)
                button.setMenu(menu)

                first_action = None
                actions_for_button = []
                for tool_info in normalized_tools:
                    action = tool_info["action"]
                    menu.addAction(action)
                    if first_action is None:
                        first_action = action
                    actions_for_button.append(action)
                    self.tool_buttons[tool_info["name"]] = button
                    configured_tools.add(tool_info["name"])

                if not first_action:
                    continue

                button.setDefaultAction(first_action)

                entry_label = entry_name or normalized_tools[0]["name"]
                self._button_entry_names[button] = entry_label
                self._button_actions_map[button] = list(actions_for_button)
                self._refresh_button_tooltip(button, first_action)

                group_shortcut = None
                for tool_info in normalized_tools:
                    candidate = tool_info.get("shortcut")
                    if not candidate:
                        group_shortcut = None
                        break
                    if group_shortcut is None:
                        group_shortcut = candidate
                    elif candidate != group_shortcut:
                        group_shortcut = None
                        break

                if group_shortcut:
                    self._register_shortcut_group(
                        group_shortcut, [tool_info["name"] for tool_info in normalized_tools]
                    )

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
            button.setDefaultAction(action)

            self._button_entry_names[button] = tool_name
            self._button_actions_map[button] = [action]
            self._refresh_button_tooltip(button, action)

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

        canvas = getattr(self.main_window, "canvas", None)
        input_handler = getattr(canvas, "input_handler", None)
        if input_handler and hasattr(input_handler, "set_tool_shortcut_groups"):
            input_handler.set_tool_shortcut_groups(self._shortcut_groups)

    def _get_or_create_tool_action(self, tool):
        tool_name = tool["name"]
        if tool_name in self.tool_actions:
            return self.tool_actions[tool_name]

        icon_path = tool.get("icon") or ""
        action = QAction(QIcon(icon_path), tool_name, self.main_window)
        action.setCheckable(True)
        shortcut_hint = self._format_shortcut_hint(tool.get("shortcut"))
        if shortcut_hint:
            action.setProperty("shortcut_hint", shortcut_hint)
            action.setToolTip(f"{tool_name} ({shortcut_hint})")
        else:
            action.setToolTip(tool_name)
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

        self._refresh_button_tooltip(button, action)

        icon = action.icon()
        if icon.isNull():
            icon_path = self._button_fallback_icons.get(button)
            if icon_path:
                button.setIcon(QIcon(icon_path))
        else:
            button.setIcon(icon)

    def _refresh_button_tooltip(self, button, default_action):
        if button is None or default_action is None:
            return

        actions = self._button_actions_map.get(button, [])
        if actions:
            ordered_actions = [default_action] + [a for a in actions if a is not default_action]
        else:
            ordered_actions = [default_action]

        entry_name = self._button_entry_names.get(button)
        tooltip = self._button_tooltip_from_actions(entry_name, ordered_actions)
        button.setToolTip(tooltip)

        if actions:
            self._button_actions_map[button] = ordered_actions

    def _register_shortcut_group(self, shortcut, tool_names):
        if not shortcut or not tool_names:
            return

        normalized_key = str(shortcut).strip().lower()
        if not normalized_key:
            return

        existing = self._shortcut_groups.setdefault(normalized_key, [])
        for name in tool_names:
            if name and name not in existing:
                existing.append(name)

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
