from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor
from portal.ui.background import Background
import importlib.util

# Check for optional background removal dependency without importing heavy modules
REMBG_AVAILABLE = importlib.util.find_spec("rembg") is not None

class ActionManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.app = main_window.app

    def setup_actions(self, canvas):
        """Set up all application actions by delegating to category builders.

        Adding a new action category is as simple as implementing another
        ``_build_*`` helper and invoking it here.
        """
        self.canvas = canvas
        self._build_file_actions()
        self._build_edit_actions()
        self._build_select_actions()
        self._build_image_actions()
        self._build_layer_actions()
        self._build_view_actions(canvas)
        self._build_tool_actions()

    def _build_file_actions(self):
        """Create actions related to file management."""
        self.new_action = QAction(QIcon("icons/new.png"), "&New", self.main_window)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.main_window.open_new_file_dialog)

        self.open_action = QAction(QIcon("icons/load.png"), "&Open", self.main_window)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.app.document_service.open_document)

        self.open_as_key_action = QAction("Open as Key...", self.main_window)
        self.open_as_key_action.triggered.connect(self.app.document_service.open_as_key)

        self.import_animation_action = QAction("Import Animation...", self.main_window)
        self.import_animation_action.triggered.connect(self.app.document_service.import_animation)

        self.export_animation_action = QAction("Export Animation...", self.main_window)
        self.export_animation_action.triggered.connect(self.app.document_service.export_animation)

        self.save_action = QAction(QIcon("icons/save.png"), "&Save", self.main_window)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.app.document_service.save_document)

        self.save_as_action = QAction("Save &As...", self.main_window)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.app.document_service.save_document_as)

        self.save_palette_as_png_action = QAction("Save Palette as PNG...", self.main_window)
        self.save_palette_as_png_action.triggered.connect(self.main_window.save_palette_as_png)

        self.load_palette_action = QAction("Load Palette from Image...", self.main_window)
        self.load_palette_action.triggered.connect(self.main_window.load_palette_from_image)

        self.exit_action = QAction("&Exit", self.main_window)
        self.exit_action.triggered.connect(self.app.exit)

    def _build_edit_actions(self):
        """Create actions for standard edit operations."""
        self.undo_action = QAction("&Undo", self.main_window)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(self.app.undo)

        self.redo_action = QAction("&Redo", self.main_window)
        self.redo_action.setShortcut("Ctrl+Shift+Z")
        self.redo_action.triggered.connect(self.app.redo)

        self.cut_action = QAction("Cu&t", self.main_window)
        self.cut_action.setShortcut(QKeySequence.Cut)
        self.cut_action.triggered.connect(self.app.clipboard_service.cut)

        self.copy_action = QAction("&Copy", self.main_window)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(self.app.clipboard_service.copy)

        self.paste_action = QAction("&Paste", self.main_window)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(self.app.clipboard_service.paste)

        self.paste_as_new_image_action = QAction("Paste as New Image", self.main_window)
        self.paste_as_new_image_action.setShortcut("Ctrl+Shift+V")
        self.paste_as_new_image_action.triggered.connect(self.app.clipboard_service.paste_as_new_image)

        self.paste_as_key_action = QAction("Paste as Key", self.main_window)
        self.paste_as_key_action.triggered.connect(self.app.clipboard_service.paste_as_key)

        self.clear_action = QAction(QIcon("icons/clear.png"), "Clear", self.main_window)
        self.clear_action.setShortcut(QKeySequence.Delete)
        self.clear_action.triggered.connect(self.app.clear_layer)

        self.create_brush_action = QAction("Create Brush", self.main_window)
        self.create_brush_action.triggered.connect(self.app.create_brush)

        self.settings_action = QAction("Settings...", self.main_window)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self.main_window.open_settings_dialog)

    def _build_select_actions(self):
        """Create actions for selection manipulation."""
        self.select_all_action = QAction("Select &All", self.main_window)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_all_action.triggered.connect(self.app.select_all)

        self.select_none_action = QAction("Select &None", self.main_window)
        self.select_none_action.setShortcut("Ctrl+D")
        self.select_none_action.triggered.connect(self.app.select_none)

        self.invert_selection_action = QAction("&Invert Selection", self.main_window)
        self.invert_selection_action.setShortcut("Ctrl+I")
        self.invert_selection_action.triggered.connect(self.app.invert_selection)

        self.select_opaque_action = QAction("Select &Opaque", self.main_window)
        self.select_opaque_action.triggered.connect(self.app.select_opaque)

    def _build_image_actions(self):
        """Create actions that modify the current image."""
        self.resize_action = QAction(QIcon("icons/resize.png"), "&Resize", self.main_window)
        self.resize_action.setShortcut("Ctrl+R")
        self.resize_action.triggered.connect(self.main_window.open_resize_dialog)

        self.crop_action = QAction("Fit Canvas to Selection", self.main_window)
        self.crop_action.triggered.connect(self.app.crop_to_selection)
        self.crop_action.setEnabled(False)

        self.flip_action = QAction("Flip...", self.main_window)
        self.flip_action.triggered.connect(self.main_window.open_flip_dialog)

    def _build_layer_actions(self):
        """Create actions operating on layers."""
        self.conform_to_palette_action = QAction("Conform to Palette", self.main_window)
        self.conform_to_palette_action.triggered.connect(self.app.conform_to_palette)

        self.remove_background_action = QAction("Remove Background", self.main_window)

        if hasattr(self.main_window, "open_remove_background_dialog"):
            self.remove_background_action.triggered.connect(
                self.main_window.open_remove_background_dialog
            )
        else:
            # Tests and lightweight host windows may not expose the optional
            # dialog. Skip wiring the signal in that case so setup can
            # complete without raising an AttributeError.
            self.remove_background_action.setEnabled(False)

        self.remove_background_action.setEnabled(
            self.remove_background_action.isEnabled() and REMBG_AVAILABLE
        )
        if not REMBG_AVAILABLE:
            self.remove_background_action.setToolTip(
                "Background removal unavailable: install rembg and onnxruntime"
            )

    def _build_view_actions(self, canvas):
        """Create actions that affect the canvas view."""
        self.checkered_action = QAction("Checkered Background", self.main_window)
        self.checkered_action.triggered.connect(lambda: canvas.set_background(Background()))

        self.white_action = QAction("White", self.main_window)
        self.white_action.triggered.connect(lambda: canvas.set_background(Background(QColor("white"))))

        self.black_action = QAction("Black", self.main_window)
        self.black_action.triggered.connect(lambda: canvas.set_background(Background(QColor("black"))))

        self.gray_action = QAction("Gray", self.main_window)
        self.gray_action.triggered.connect(lambda: canvas.set_background(Background(QColor("gray"))))

        self.magenta_action = QAction("Magenta", self.main_window)
        self.magenta_action.triggered.connect(lambda: canvas.set_background(Background(QColor("magenta"))))

        self.custom_color_action = QAction("Custom Color...", self.main_window)
        self.custom_color_action.triggered.connect(self.main_window.open_background_color_dialog)

        self.image_background_action = QAction("Image...", self.main_window)
        self.image_background_action.triggered.connect(self.main_window.open_background_image_dialog)

        self.tile_preview_action = QAction("Tile Preview", self.main_window)
        self.tile_preview_action.setCheckable(True)
        self.tile_preview_action.toggled.connect(canvas.toggle_tile_preview)

    def _build_tool_actions(self):
        """Create actions for selecting and configuring tools."""
        self.circular_brush_action = QAction(QIcon("icons/brush_cirular.png"), "Circular", self.main_window)
        self.circular_brush_action.setCheckable(True)

        self.square_brush_action = QAction(QIcon("icons/brush_square.png"), "Square", self.main_window)
        self.square_brush_action.setCheckable(True)

        self.pattern_brush_action = QAction(QIcon("icons/brush_pattern.png"), "Pattern", self.main_window)
        self.pattern_brush_action.setCheckable(True)

        self.mirror_x_action = QAction(QIcon("icons/mirrorx.png"), "Mirror X", self.main_window)
        self.mirror_x_action.setCheckable(True)
        self.mirror_x_action.triggered.connect(self.app.set_mirror_x)

        self.mirror_y_action = QAction(QIcon("icons/mirrory.png"), "Mirror Y", self.main_window)
        self.mirror_y_action.setCheckable(True)
        self.mirror_y_action.triggered.connect(self.app.set_mirror_y)

        self.grid_action = QAction(QIcon("icons/grid.png"), "Toggle Grid", self.main_window)
        self.grid_action.setCheckable(True)

        self.ai_action = QAction(QIcon("icons/AI.png"), "AI Image", self.main_window)
        self.ai_action.triggered.connect(self.main_window.toggle_ai_panel)
