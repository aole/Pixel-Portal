"""Utilities for constructing selection paths based on image colours.

The selection tools expose two flavours of colour-based picking:

* Contiguous flood fills that collect pixels matching the sampled colour
  using a four-neighbour search.
* Global selections that grab every matching pixel in the rendered image.

Historically every tool reimplemented the logic which made the behaviour
harder to reason about and noticeably slower on large canvases.  The helpers
below share the traversal code and collapse each row of matches into horizontal
segments, significantly reducing the amount of work required to build the
``QPainterPath`` representation consumed by the selection subsystem.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import DefaultDict, List

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage, QPainterPath


RowMatches = DefaultDict[int, List[int]]


def build_color_selection_path(
    image: QImage | None,
    point: QPoint,
    *,
    contiguous: bool,
) -> QPainterPath | None:
    """Return a selection path for pixels matching ``point``'s colour.

    Parameters
    ----------
    image:
        The composited document snapshot to sample.  ``None`` or ``QImage``
        instances without pixel data result in ``None`` being returned.
    point:
        The document coordinate that will be sampled as the reference colour.
    contiguous:
        When ``True`` performs a four-direction flood fill starting from
        ``point``.  When ``False`` every pixel matching the sampled colour is
        collected regardless of connectivity.
    """

    if image is None or image.isNull():
        return None

    # ``QPoint`` exposes floating point accessors in Qt 6.  Normalise to ints
    # early to avoid surprises when a caller passes a point produced by Qt's
    # event API.
    target_x = int(point.x())
    target_y = int(point.y())

    if not image.rect().contains(target_x, target_y):
        return None

    if image.format() != QImage.Format_ARGB32:
        image = image.convertToFormat(QImage.Format_ARGB32)

    target_rgba = int(image.pixel(target_x, target_y))

    if contiguous:
        rows = _collect_contiguous_matches(image, target_x, target_y, target_rgba)
    else:
        rows = _collect_global_matches(image, target_rgba)

    return _path_from_row_matches(rows)


def _collect_contiguous_matches(
    image: QImage, start_x: int, start_y: int, target_rgba: int
) -> RowMatches:
    width = image.width()
    height = image.height()

    rows: RowMatches = defaultdict(list)
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque([(start_x, start_y)])

    while queue:
        x, y = queue.popleft()
        idx = y * width + x
        if visited[idx]:
            continue
        visited[idx] = 1

        if int(image.pixel(x, y)) != target_rgba:
            continue

        rows[y].append(x)

        if x > 0:
            neighbour = idx - 1
            if not visited[neighbour]:
                queue.append((x - 1, y))
        if x + 1 < width:
            neighbour = idx + 1
            if not visited[neighbour]:
                queue.append((x + 1, y))
        if y > 0:
            neighbour = idx - width
            if not visited[neighbour]:
                queue.append((x, y - 1))
        if y + 1 < height:
            neighbour = idx + width
            if not visited[neighbour]:
                queue.append((x, y + 1))

    return rows


def _collect_global_matches(image: QImage, target_rgba: int) -> RowMatches:
    width = image.width()
    height = image.height()

    rows: RowMatches = defaultdict(list)
    for y in range(height):
        append_to_row = rows[y].append
        for x in range(width):
            if int(image.pixel(x, y)) == target_rgba:
                append_to_row(x)
    return rows


def _path_from_row_matches(rows: RowMatches) -> QPainterPath | None:
    if not rows:
        return None

    path = QPainterPath()
    for y in sorted(rows.keys()):
        xs = sorted(rows[y])
        start = xs[0]
        run_end = xs[0]
        for x in xs[1:]:
            if x == run_end + 1:
                run_end = x
                continue
            path.addRect(QRect(start, y, run_end - start + 1, 1))
            start = run_end = x
        path.addRect(QRect(start, y, run_end - start + 1, 1))

    simplified = path.simplified()
    if simplified.isEmpty():
        return None
    return simplified
