from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QImage, QImageReader, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox

from portal.core.document import Document


class DocumentService:
    """High level operations for loading and saving documents."""

    _OPEN_FILE_FILTERS: tuple[str, ...] = (
        "All Supported Files (*.aole *.png *.jpg *.bmp *.tif *.tiff)",
        "Pixel Portal Document (*.aole)",
        "Image Files (*.png *.jpg *.bmp)",
        "TIFF Files (*.tif *.tiff)",
    )

    _SAVE_FILE_FILTERS: tuple[str, ...] = (
        "Pixel Portal Document (*.aole)",
        "PNG (*.png)",
        "JPEG (*.jpg *.jpeg)",
        "Bitmap (*.bmp)",
        "TIFF (*.tif *.tiff)",
    )

    _RASTER_EXTENSIONS: frozenset[str] = frozenset({
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
    })

    _ARCHIVE_SAVE_HANDLERS: dict[str, Callable[[Document, str], None]] = {
        ".aole": Document.save_aole,
        ".tif": Document.save_tiff,
        ".tiff": Document.save_tiff,
    }

    def __init__(self, app=None):
        self.app = app

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------
    def open_document(self) -> None:
        app = self.app
        if app is None:
            return
        if not app.check_for_unsaved_changes():
            return

        file_path, selected_filter = QFileDialog.getOpenFileName(
            self._dialog_parent(),
            "Open Document",
            getattr(app, "last_directory", ""),
            self._build_filter_string(self._OPEN_FILE_FILTERS),
        )
        if not file_path:
            return

        extension_hint = self._extract_extension_hint(selected_filter)
        document = self._load_document_from_path(file_path, extension_hint)
        if document is None:
            self._show_message(
                QMessageBox.Warning,
                "Unable to open the selected document.",
                "The file appears to be corrupted or in an unsupported format.",
            )
            return

        self._update_last_directory(file_path)
        app.attach_document(document)
        app.undo_manager.clear()
        app.is_dirty = False
        app.undo_stack_changed.emit()
        app.document_changed.emit()
        if app.main_window:
            app.main_window.canvas.set_initial_zoom()

    def open_as_key(self) -> None:
        app = self.app
        if app is None:
            return

        document = getattr(app, "document", None)
        if document is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self._dialog_parent(),
            "Import Image as Layer",
            getattr(app, "last_directory", ""),
            "Image Files (*.png *.jpg *.bmp *.tif *.tiff);;All Files (*)",
        )
        if not file_path:
            return

        image = QImage(file_path)
        if image.isNull():
            self._show_message(
                QMessageBox.Warning,
                "Unable to import image.",
                "The selected file could not be read as an image.",
            )
            return

        self._update_last_directory(file_path)
        layer_name = Path(file_path).stem or "Imported Layer"
        active_layer = document.layer_manager.active_layer
        if active_layer is None:
            return
        target_image = active_layer.image
        painter = QPainter(target_image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawImage(0, 0, image)
        painter.end()
        active_layer.on_image_change.emit()
        active_layer.name = layer_name
        app.is_dirty = True
        app.document_changed.emit()
        app.undo_stack_changed.emit()

    def save_document(self) -> None:
        app = self.app
        if app is None:
            return

        document = getattr(app, "document", None)
        if document is None:
            return

        file_path = getattr(document, "file_path", None)
        if not file_path:
            self.save_document_as()
            return

        if not self._save_document_to_path(document, file_path):
            self.save_document_as()
            return

        self._finalize_save(document, file_path)

    def save_document_as(self) -> None:
        app = self.app
        if app is None:
            return

        document = getattr(app, "document", None)
        if document is None:
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self._dialog_parent(),
            "Save Document",
            getattr(app, "last_directory", ""),
            self._build_filter_string(self._SAVE_FILE_FILTERS),
        )
        if not file_path:
            return

        normalized_path = self._normalize_save_path(file_path, selected_filter)
        if not self._save_document_to_path(document, normalized_path):
            return

        document.file_path = normalized_path
        self._finalize_save(document, normalized_path)

    def export_animation(self) -> None:  # pragma: no cover - UI convenience
        self._show_message(
            QMessageBox.Information,
            "Animation export is unavailable.",
            "Animation features are currently disabled while the system is rebuilt.",
        )

    def import_animation(self) -> None:  # pragma: no cover - UI convenience
        self._show_message(
            QMessageBox.Information,
            "Animation import is unavailable.",
            "Animation features are currently disabled while the system is rebuilt.",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _dialog_parent(self):
        app = self.app
        if app is None:
            return None
        return getattr(app, "main_window", None)

    @staticmethod
    def _build_filter_string(filters: tuple[str, ...]) -> str:
        return ";;".join(filters)

    @staticmethod
    def _extract_extension_hint(selected_filter: str | None) -> str | None:
        if not selected_filter:
            return None
        try:
            _, pattern_section = selected_filter.split("(", 1)
            pattern_section, _ = pattern_section.split(")", 1)
        except ValueError:
            return None

        extensions = []
        for token in pattern_section.split():
            token = token.strip()
            if not token.startswith("*."):
                continue
            suffix = token[2:].rstrip(")*").lower()
            if suffix and suffix != "*":
                extensions.append(suffix)

        unique_extensions = {ext for ext in extensions}
        if len(unique_extensions) == 1:
            suffix = unique_extensions.pop()
        elif len(extensions) == 2:
            suffix = extensions[-1]
        else:
            return None

        return f".{suffix}"

    def _load_document_from_path(
        self, file_path: str, extension_hint: str | None
    ) -> Document | None:
        suffix = Path(file_path).suffix.lower()
        if not suffix and extension_hint:
            suffix = extension_hint.lower()

        if suffix == ".aole":
            try:
                return Document.load_aole(file_path)
            except (OSError, ValueError):
                return None
        if suffix in {".tif", ".tiff"}:
            try:
                return Document.load_tiff(file_path)
            except (OSError, ValueError):
                return None

        image = QImage(file_path)
        if image.isNull():
            reader = QImageReader(file_path)
            reader.setDecideFormatFromContent(True)
            image = reader.read()
            if image.isNull():
                return None

        document = Document(max(1, image.width()), max(1, image.height()))
        layer_manager = document.layer_manager
        layer = layer_manager.active_layer
        if layer is None:
            layer_manager.add_layer("Layer 1")
            layer = layer_manager.active_layer
        if layer is not None:
            painter = QPainter(layer.image)
            painter.drawImage(0, 0, image)
            painter.end()
            layer.name = Path(file_path).stem or "Layer 1"
        document.file_path = file_path
        return document

    def _save_document_to_path(self, document: Document, file_path: str) -> bool:
        suffix = Path(file_path).suffix.lower()
        handler = self._ARCHIVE_SAVE_HANDLERS.get(suffix)
        try:
            if handler is not None:
                handler(document, file_path)
                return True
            if suffix in self._RASTER_EXTENSIONS:
                image = document.render()
                return bool(image.save(file_path))
            # Default to PNG when no extension was supplied
            image = document.render()
            target_path = str(Path(file_path).with_suffix(".png"))
            saved = image.save(target_path)
            if saved:
                document.file_path = target_path
            return saved
        except OSError:
            self._show_message(
                QMessageBox.Critical,
                "Failed to save document.",
                "An error occurred while writing the file.",
            )
            return False

    def _finalize_save(self, document: Document, file_path: str) -> None:
        app = self.app
        if app is None:
            return
        self._update_last_directory(file_path)
        app.is_dirty = False
        if hasattr(app, "update_main_window_title"):
            app.update_main_window_title()

    def _normalize_save_path(
        self, file_path: str, selected_filter: str | None
    ) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix in self._ARCHIVE_SAVE_HANDLERS or suffix in self._RASTER_EXTENSIONS:
            return str(path)

        extension_hint = self._extract_extension_hint(selected_filter)
        if extension_hint:
            suffix = extension_hint
        if not suffix:
            suffix = ".png"
        return str(path.with_suffix(suffix))

    def _update_last_directory(self, file_path: str) -> None:
        app = self.app
        if app is None:
            return
        directory = os.path.dirname(file_path) or ""
        app.last_directory = directory
        config = getattr(app, "config", None)
        if config is not None:
            config.set("General", "last_directory", directory)

    def _show_message(
        self,
        icon: QMessageBox.Icon,
        text: str,
        informative_text: str = "",
    ) -> None:
        message_box = QMessageBox(self._dialog_parent())
        message_box.setIcon(icon)
        message_box.setText(text)
        if informative_text:
            message_box.setInformativeText(informative_text)
        message_box.exec()
