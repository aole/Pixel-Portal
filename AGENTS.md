# Pixel-Portal Agent Guide

Pixel-Portal is a Python/PySide6 desktop editor tailored for pixel art. It combines a traditional
layer-based workflow with conveniences such as tile previews, palette helpers, and optional AI image
generation. Use the notes below to orient yourself quickly before making changes.

## Quick facts
- Entry point: `python -m portal.main` wires up `App`, services, and the main window.
- The canvas renders pixel-perfect output; keep interpolation settings (`Qt.FastTransformation`)
  for anything that should stay crisp.
- Tile preview controls and palette switching live on the `Canvas` and `CanvasRenderer`
  classes—check there for drawing behaviour changes.
- Optional AI features depend on heavyweight libraries that are **not** installed in this
  environment. Code touching `portal.ai` must gracefully handle missing imports (follow the existing
  `try`/`except ImportError` patterns).

## Repository map
- `portal/core/`
  - `app.py` hosts the high-level `App` façade that the UI talks to.
  - `document.py`, `layer.py`, and `layer_manager.py` implement the document model.
  - `document_controller.py` handles clipboard imports, palette quantisation, and smart cropping.
  - `drawing.py` contains flood fill, pixel-perfect brushes, symmetry helpers, and wrap-around logic.
  - `renderer.py` draws the canvas, background, grid, and tile preview mosaics.
- `portal/ui/`
  - `ui.py` constructs the `MainWindow`, hooks menus/toolbars, and lazily loads optional docks.
  - `canvas.py` is the heart of the editor: it maintains zoom, selections, tile preview toggles,
    and exposes signals the rest of the UI consumes.
  - `layer_list_widget.py`, `color_swatch_widget.py`, etc., implement the surrounding panels.
- `portal/tools/`
  - Each tool subclasses `BaseTool` (see `basetool.py`) and is registered in `registry.py`.
  - Common helpers live in `toolutils.py`; the bucket, line, ellipse, rectangle, and eraser tools all
    rely on routines in `portal.core.drawing` for predictable pixel art behaviour.
- `portal/commands/` wires Qt actions to business logic. `action_manager.py` owns action instances,
  while `menu_bar_builder.py` and friends arrange them in the UI.
- `portal/ai/` contains configuration and UI for AI assistance. Treat it as optional.
- `palettes/` stores default palette definitions (JSON). Use these when adding palette features.
- `scripts/` contains one-off helpers such as `tile_generator.py` (creates isometric/hex tiles) and
  `checkered_background.py`.
- `tests/` is a PySide6-heavy pytest suite that covers tools, selections, layers, and dialogs.

## Working with pixel-art features
- **Tile preview:** `Canvas.toggle_tile_preview` toggles repetition. Drawing tools respect the
  `canvas.tile_preview_enabled` flag and call `Drawing.paint_*` with `wrap=True`. Updates to wrapping
  logic typically touch both `portal/tools/*tool.py` and `portal/core/drawing.py`.
- **Playback metadata:** Animation systems are being rebuilt. Playback totals/FPS now live on the
  `Document` solely so the UI can expose placeholder controls. Avoid introducing new frame-manager
  dependencies.
- **Grid:** `CanvasRenderer` draws the major/minor grid lines based on `Canvas.grid_*` settings.
  UI actions for toggling these live in `commands/action_manager.py`.
- **Palette & color picking:** Palette JSON files feed into `portal/ui/color_panel.py`. The picker
  tool samples colors from the composited image via `Document.render()` to respect visibility and
  opacity.
- **Undo/redo:** All mutating actions should emit `command_generated` with a `Command` subclass from
  `portal/core/command.py`. Tools typically build commands inside their mouse event handlers.
- **Symmetry & wrap:** `Drawing` exposes helpers for horizontal symmetry and wrap-around behaviour.
  Be mindful of performance; most routines operate on numpy-like loops over QImage pixels.

## Adding or modifying tools
1. Register the tool class in `portal/tools/registry.py` with a unique `name`.
2. Subclass `BaseTool`, set cursor icons (in `icons/`), and implement mouse handlers.
3. For painting tools, delegate to `Drawing` helpers to keep fill/brush behaviour consistent.
4. Write or adjust tests in `tests/test_drawing_tools.py` (or the relevant module) to cover the new
   behaviour.

## Running the app
```bash
python -m portal.main
```
This bootstraps `App`, `DocumentService`, and `ClipboardService`, then instantiates `MainWindow`.
Set `QT_QPA_PLATFORM=offscreen` when running in a headless environment.

## Testing
- **Run only relevant tests.**
- When tests are required, export `QT_QPA_PLATFORM=offscreen` first. Run each module individually to
  avoid intermittent Qt crashes. Commonly exercised modules include:
  ```bash
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_ai_generation_size.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_canvas_input_handler.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_core.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_dialogs.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_document_controller_title.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_document_service.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_drawing_tools.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_fit_canvas_to_selection.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_grid_settings.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_selection_tools.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_tool_bar_builder.py
  QT_QPA_PLATFORM=offscreen python -m pytest tests/test_transform_tool.py
  ```
- `tests/test_segfault.py` documents historical Qt crashes; only run it when specifically asked.

## Environment & dependencies
- Use `requirements.txt` for the full experience (includes AI stack). For CI/headless work, install
  `requirements-headless.txt` instead.
- Keep `settings.ini` out of commits unless intentionally changing defaults. Values like
  `last_directory` are user-specific noise.

## Handy references
- Icons live in `icons/`; Qt loads them via relative paths.
- `portal/config/toolbar_tools.json` defines the toolbar layout. Update it if you add/remove tools.
- `alphabg.png` is the default transparent background checkerboard.
- The TODO list in `todo.txt` documents outstanding improvements and is safe to consult when looking
  for follow-up tasks.
