# Pixel Portal Technical Reference

## Overview
Pixel Portal is a PySide6 desktop application for pixel art creation that combines a layer-based renderer, tile-aware drawing tools, and placeholder timeline controls. The runtime is organized into a small set of packages under `portal/` that separate document logic, UI composition, user tools, and supporting services.

## Runtime entry point
The application starts at `python -m portal.main`, which creates the Qt `QApplication`, instantiates shared services, and wires the `App` façade to the `MainWindow` UI before entering the Qt event loop.【F:portal/main.py†L1-L18】

## Architectural layers
- **Core (`portal/core/`)** – Document model, undo/redo, drawing helpers, and controllers that orchestrate file operations and playback metadata.【F:portal/core/app.py†L5-L143】【F:portal/core/document.py†L1-L115】
- **UI (`portal/ui/`)** – Widgets that build the main window, canvas, timeline, dockable panels, and dialogs. These components subscribe to the core controllers and expose application actions.【F:portal/ui/ui.py†L1-L147】【F:portal/ui/canvas.py†L1-L118】
- **Tools (`portal/tools/`)** – Extensible drawing tool implementations driven by a registry that discovers built-in modules and optional entry points.【F:portal/tools/basetool.py†L1-L105】【F:portal/tools/registry.py†L1-L67】
- **Commands (`portal/commands/`)** – Command objects that adapt user interactions into undoable document mutations and hook menus, toolbars, and keyboard shortcuts.【F:portal/core/command.py†L1-L118】【F:portal/commands/action_manager.py†L1-L119】
- **AI (`portal/ai/`)** – Optional helpers for AI-assisted workflows. These modules are imported defensively so the application still runs when heavy dependencies are absent.【F:portal/ui/ui.py†L27-L34】

## Core systems
### App façade and controllers
`App` owns the high-level controllers, exposes Qt signals for UI wiring, and forwards most business logic to `DocumentController`. It also publishes scripting APIs and playback settings so timeline widgets can manipulate animation state consistently.【F:portal/core/app.py†L13-L206】

`DocumentController` is the central mediator for document lifecycle, undo stack management, playback configuration, AI output rectangles, and clipboard/service integrations. It creates the initial document, keeps the window title in sync with dirty state, and coordinates between services such as `DocumentService` and `ClipboardService`.【F:portal/core/document_controller.py†L1-L154】

### Document model
`Document` owns a single `LayerManager`, tracks metadata such as the AI output rectangle, playback frame counts, and file associations, and exposes helpers for cloning, rendering, and managing the layer stack.【F:portal/core/document.py†L1-L249】 Animation-specific concepts such as keyframes and frame managers have been removed for the reset effort; playback totals and FPS remain only so the UI can surface placeholder controls while new animation systems are rebuilt.【F:portal/core/document.py†L16-L109】

### Drawing context and rendering
Interactive drawing relies on the `DrawingContext` object to broadcast brush configuration, symmetry axes, and pattern brushes to interested widgets.【F:portal/core/drawing_context.py†L1-L67】 The `Drawing` helper then applies those settings when stamping pixels, honoring mirror axes, wrap-around, and pattern fills.【F:portal/core/drawing.py†L1-L118】 Canvas rendering is delegated to `CanvasRenderer` (not shown) via the `Canvas` widget, which manages zoom, onion skin overlays, tile previews, AI output handles, and tool dispatching.【F:portal/ui/canvas.py†L1-L118】【F:portal/ui/canvas.py†L119-L209】

### Command and undo infrastructure
The application implements a command pattern: each undoable operation subclasses `Command`, captures the state it needs, and restores it during `undo`. Composite commands allow batching, while specialized commands such as `DrawCommand` compute bounding rectangles that include mirrored strokes and pattern padding.【F:portal/core/command.py†L1-L164】 Commands are pushed onto an `UndoManager`, which maintains separate undo/redo stacks used by the controller and UI actions.【F:portal/core/undo.py†L1-L36】

### Services
`DocumentService` centralizes document I/O, including open/save dialogs, AOLE and TIFF serialization, and raster exports. It resolves dialog filters, normalizes file extensions, and delegates to the document for format-specific persistence.【F:portal/core/services/document_service.py†L1-L118】 Clipboard operations, selection cropping, and palette management live alongside in the controller and associated services (see `portal/core/services/clipboard_service.py`).

`SettingsController` reads `settings.ini`, exposes grid/background/animation defaults, and persists updates triggered from the UI, including optional AI prompt history.【F:portal/core/settings_controller.py†L1-L120】

### Playback stubs
A lightweight `NullAnimationPlayer` keeps the timeline and preview panels responsive without advancing real frames. Playback controls update loop ranges and FPS metadata on the document controller so UI code can remain wired while the animation stack is rebuilt.【F:portal/ui/preview_panel.py†L1-L136】【F:portal/ui/ui.py†L1-L140】

### Scripting and extensibility
A lightweight scripting system lets users run Python snippets via `App.run_script`. Scripts define `params` metadata to drive a `ScriptDialog`, execute against a `ScriptingAPI`, and record generated commands as a single undoable composite. Errors are trapped so failed scripts leave the application in a consistent state.【F:portal/core/app.py†L139-L206】 The scripting API can enumerate layers, create new ones, and wrap modifications inside undoable commands.【F:portal/core/scripting.py†L1-L39】

### Tooling architecture
Every drawing tool subclasses `BaseTool`, which exposes Qt event hooks and helpers for allocating preview images and resolving the active layer manager. Tools register themselves via `ToolRegistry`, which discovers modules ending in `tool.py` and can load external plugins through the `pixel_portal.tools` entry point group.【F:portal/tools/basetool.py†L1-L105】【F:portal/tools/registry.py†L1-L67】 The canvas instantiates these tools and relays user input through a `CanvasInputHandler`, emitting undoable commands back to the controller.【F:portal/ui/canvas.py†L73-L118】

### UI composition
`MainWindow` builds the primary workspace: it creates the canvas, placeholder animation player, timeline, preview panel, AI dock (when available), and connects toolbar/menu actions produced by `ActionManager`, `MenuBarBuilder`, and `ToolBarBuilder`. Playback shortcuts currently update only the stored metadata, leaving room for future animation playback while keeping the UI behaviour consistent.【F:portal/ui/ui.py†L1-L147】【F:portal/ui/ui.py†L70-L136】 Action definitions cover file management, editing, selection, image operations, layer utilities, and optional background removal, with tooltips automatically populated from shortcuts.【F:portal/commands/action_manager.py†L1-L154】

## Resources and configuration
Static assets live alongside the codebase:
- `palettes/` – Built-in palette JSON files consumed by color panel widgets.
- `icons/` – Toolbar and UI icons referenced throughout the UI setup.【F:portal/ui/ui.py†L70-L112】
- `scripts/` – Example automation scripts (pattern fill, tile generation, outlines) that can be executed via the scripting dialog.
- `settings.ini` – User-tunable defaults read and written by `SettingsController`. Developers should avoid committing user-specific values.

## Testing
Pytest-based integration and unit tests reside under `tests/`, covering document core behavior, controller window-title updates, timeline math, drawing tools, canvas input routing, and toolbar wiring.【F:tests/test_core.py†L1-L160】【F:tests/test_drawing_tools.py†L1-L200】 When running in headless environments, export `QT_QPA_PLATFORM=offscreen` before invoking pytest modules individually to avoid Qt crashes (see repository agent notes).

## Running and packaging
- **Development run:** `python -m portal.main`.
- **Headless/CI:** Install `requirements-headless.txt` and set `QT_QPA_PLATFORM=offscreen` to run tests or scripted automation without a visible display.
- **Full experience:** Install `requirements.txt` to enable optional AI and image-processing features such as background removal.

## Extending Pixel Portal
1. **New tools:** Implement a `BaseTool` subclass, register it in `portal/tools/registry.py`, and provide icons/shortcuts as needed.【F:portal/tools/registry.py†L17-L58】 Update toolbar configuration (`portal/config/toolbar_tools.json`) if you want it accessible via the main toolbar.
2. **New commands:** Create a command class under `portal/core/command.py` or `portal/commands/` that encapsulates the change and ensure it cooperates with `UndoManager`.
3. **Automations:** Build scripts that call into `ScriptingAPI` to orchestrate multi-step effects. Commands generated during script execution are recorded and bundled for undo.【F:portal/core/app.py†L139-L206】
4. **External plugins:** Distribute tool plugins through the `pixel_portal.tools` entry point so `ToolRegistry.load_external_tools()` can auto-discover them.【F:portal/tools/registry.py†L41-L67】

## File format support
Pixel Portal can serialize native AOLE archives (including multi-layer metadata), layered TIFFs, and standard raster formats via `DocumentService`. The controller exposes commands for manipulating layers, selections, and transforms; animation-specific commands have been stubbed out while the playback stack is being rebuilt.【F:portal/core/services/document_service.py†L1-L118】【F:portal/core/document_controller.py†L1-L170】

## Optional AI workflow
AI assistance is additive: the `MainWindow` tries to import `portal.ui.ai_panel` but gracefully continues when the dependency is missing.【F:portal/ui/ui.py†L27-L34】 Background removal actions only enable when the third-party `rembg` module is available, keeping the rest of the UI responsive without the extra library.【F:portal/commands/action_manager.py†L1-L16】 The document tracks an `ai_output_rect` that defines where generated imagery should land, ensuring exported AI results respect the current canvas bounds.【F:portal/core/document.py†L19-L72】
