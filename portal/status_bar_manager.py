from PySide6.QtWidgets import QLabel

class StatusBarManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.canvas = main_window.canvas
        self.app = main_window.app
        self._setup_status_bar()
        self._connect_signals()

    def _setup_status_bar(self):
        status_bar = self.main_window.statusBar()
        self.main_window.cursor_pos_label = QLabel("Cursor: (0, 0)")
        self.main_window.selected_tool_label = QLabel("Tool: Pen")
        self.main_window.zoom_level_label = QLabel("Zoom: 100%")
        self.main_window.selection_size_label = QLabel("")
        status_bar.addWidget(self.main_window.cursor_pos_label)
        status_bar.addWidget(self.main_window.selected_tool_label)
        status_bar.addWidget(self.main_window.zoom_level_label)
        status_bar.addWidget(self.main_window.selection_size_label)

    def _connect_signals(self):
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)
        self.canvas.zoom_changed.connect(self.update_zoom_level_label)
        self.app.drawing_context.tool_changed.connect(self.update_selected_tool_label)
        self.canvas.selection_size_changed.connect(self.update_selection_size_label)

    def update_cursor_pos_label(self, pos):
        self.main_window.cursor_pos_label.setText(f"Cursor: ({pos.x()}, {pos.y()})")

    def update_zoom_level_label(self, zoom):
        self.main_window.zoom_level_label.setText(f"Zoom: {int(zoom * 100)}%")

    def update_selected_tool_label(self, tool):
        self.main_window.selected_tool_label.setText(f"Tool: {tool}")

    def update_selection_size_label(self, width, height):
        if width > 0 and height > 0:
            self.main_window.selection_size_label.setText(f"Selection: {width}x{height}")
        else:
            self.main_window.selection_size_label.setText("")
