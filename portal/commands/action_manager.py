from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor
from portal.ui.background import Background

class ActionManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.app = main_window.app

    def setup_actions(self, canvas):
        # File actions
        self.new_action = QAction(QIcon("icons/new.png"), "&New", self.main_window)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.main_window.open_new_file_dialog)

        self.open_action = QAction(QIcon("icons/load.png"), "&Open", self.main_window)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.app.document_service.open_document)

        self.save_action = QAction(QIcon("icons/save.png"), "&Save", self.main_window)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.app.document_service.save_document)

        self.save_palette_as_png_action = QAction("Save Palette as PNG...", self.main_window)
        self.save_palette_as_png_action.triggered.connect(self.main_window.save_palette_as_png)

        self.load_palette_action = QAction("Load Palette from Image...", self.main_window)
        self.load_palette_action.triggered.connect(self.main_window.load_palette_from_image)

        self.exit_action = QAction("&Exit", self.main_window)
        self.exit_action.triggered.connect(self.app.exit)

        # Edit actions
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

        self.clear_action = QAction(QIcon("icons/clear.png"), "Clear", self.main_window)
        self.clear_action.setShortcut(QKeySequence.Delete)
        self.clear_action.triggered.connect(self.app.clear_layer)

        # Select actions
        self.select_all_action = QAction("Select &All", self.main_window)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_all_action.triggered.connect(self.app.select_all)

        self.select_none_action = QAction("Select &None", self.main_window)
        self.select_none_action.setShortcut("Ctrl+D")
        self.select_none_action.triggered.connect(self.app.select_none)

        self.invert_selection_action = QAction("&Invert Selection", self.main_window)
        self.invert_selection_action.setShortcut("Ctrl+I")
        self.invert_selection_action.triggered.connect(self.app.invert_selection)

        # Image actions
        self.resize_action = QAction(QIcon("icons/resize.png"), "&Resize", self.main_window)
        self.resize_action.setShortcut("Ctrl+R")
        self.resize_action.triggered.connect(self.main_window.open_resize_dialog)

        self.crop_action = QAction("Crop to Selection", self.main_window)
        self.crop_action.triggered.connect(self.app.crop_to_selection)
        self.crop_action.setEnabled(False)

        self.flip_action = QAction("Flip...", self.main_window)
        self.flip_action.triggered.connect(self.main_window.open_flip_dialog)

        # Layer actions
        self.conform_to_palette_action = QAction("Conform to Palette", self.main_window)
        self.conform_to_palette_action.triggered.connect(self.app.conform_to_palette)

        # View actions
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

        # Tool actions
        self.circular_brush_action = QAction(QIcon("icons/brush_cirular.png"), "Circular", self.main_window)
        self.circular_brush_action.setCheckable(True)
        self.square_brush_action = QAction(QIcon("icons/brush_square.png"), "Square", self.main_window)
        self.square_brush_action.setCheckable(True)

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
