"""Shared helpers for tracking which layer a tool is operating on."""

from __future__ import annotations

from typing import Any, Tuple

def resolve_active_layer_manager(document):
    return getattr(document, "layer_manager", None)


class ActiveLayerTracker:
    """Utility that records and compares the active layer context for a tool.

    Tools that cache geometry or preview state often need to know when the user
    has switched to a different layer, document, or frame. ``ActiveLayerTracker``
    captures the trio of ``(document, layer_manager, layer_uid)`` and exposes a
    light-weight ``has_changed`` check so callers can invalidate their caches
    without wiring bespoke signals for every tool.
    """

    __slots__ = ("_canvas", "_document", "_layer_manager", "_layer_uid")

    def __init__(self, canvas) -> None:
        self._canvas = canvas
        self._document = None
        self._layer_manager = None
        self._layer_uid = None

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Forget the stored context so the next check treats it as changed."""

        self._document = None
        self._layer_manager = None
        self._layer_uid = None

    # ------------------------------------------------------------------
    def _capture(self) -> Tuple[Any, Any, int | None]:
        document = getattr(self._canvas, "document", None)
        layer_manager = (
            resolve_active_layer_manager(document)
            if document is not None
            else None
        )
        active_layer = (
            getattr(layer_manager, "active_layer", None)
            if layer_manager is not None
            else None
        )
        layer_uid = getattr(active_layer, "uid", None)
        return document, layer_manager, layer_uid

    # ------------------------------------------------------------------
    def has_changed(self) -> bool:
        """Return ``True`` when the active layer context has shifted."""

        document, layer_manager, layer_uid = self._capture()
        return (
            document is not self._document
            or layer_manager is not self._layer_manager
            or layer_uid != self._layer_uid
        )

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Record the current active layer context."""

        self._document, self._layer_manager, self._layer_uid = self._capture()

    # ------------------------------------------------------------------
    def snapshot(self) -> Tuple[Any, Any, int | None]:
        """Return the last recorded ``(document, layer_manager, layer_uid)``."""

        return self._document, self._layer_manager, self._layer_uid

