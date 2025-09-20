"""Shared styling helpers for the transform tool gizmos."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor


# ``QCursor`` objects rely on a running ``QGuiApplication``. Importing tools
# happens during module import before tests (and ``pytest-qt``'s ``qapp``
# fixture) spin up the application, so we expose a factory to avoid constructing
# cursor instances at import time. The tools call :func:`make_transform_cursor`
# from their initialisers when the application is already available.
TRANSFORM_CURSOR_SHAPE = Qt.OpenHandCursor


def make_transform_cursor() -> QCursor:
    """Return a cursor instance for transform gizmos."""

    return QCursor(TRANSFORM_CURSOR_SHAPE)


TRANSFORM_GIZMO_BASE_COLOR = QColor("#0c7bdc")
TRANSFORM_GIZMO_HOVER_COLOR = QColor(TRANSFORM_GIZMO_BASE_COLOR)
TRANSFORM_GIZMO_HOVER_COLOR = TRANSFORM_GIZMO_HOVER_COLOR.lighter(130)
TRANSFORM_GIZMO_ACTIVE_COLOR = QColor(TRANSFORM_GIZMO_BASE_COLOR)
TRANSFORM_GIZMO_ACTIVE_COLOR = TRANSFORM_GIZMO_ACTIVE_COLOR.lighter(160)
