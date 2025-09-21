# Pixel-Portal User Manual

## Table of Contents
- [1. Welcome](#1-welcome)
- [2. System Requirements](#2-system-requirements)
- [3. Installation and Setup](#3-installation-and-setup)
  - [3.1 Standard desktop installation](#31-standard-desktop-installation)
  - [3.2 Minimal and headless environments](#32-minimal-and-headless-environments)
  - [3.3 Optional AI dependencies](#33-optional-ai-dependencies)
  - [3.4 Updating to a newer build](#34-updating-to-a-newer-build)
- [4. Launching Pixel-Portal](#4-launching-pixel-portal)
  - [4.1 First run](#41-first-run)
  - [4.2 Command-line tips](#42-command-line-tips)
  - [4.3 Where Pixel-Portal stores preferences](#43-where-pixel-portal-stores-preferences)
- [5. Understanding Pixel-Portal documents](#5-understanding-pixel-portal-documents)
- [6. Tour of the workspace](#6-tour-of-the-workspace)
  - [6.1 Canvas and animation timeline](#61-canvas-and-animation-timeline)
  - [6.2 Toolbars](#62-toolbars)
  - [6.3 Dockable panels](#63-dockable-panels)
  - [6.4 Status bar](#64-status-bar)
  - [6.5 Customising the layout](#65-customising-the-layout)
- [7. Quick start workflow](#7-quick-start-workflow)
- [8. Canvas navigation and display controls](#8-canvas-navigation-and-display-controls)
- [9. Drawing, selection, and transform tools](#9-drawing-selection-and-transform-tools)
  - [9.1 Choosing tools and brush settings](#91-choosing-tools-and-brush-settings)
  - [9.2 Painting tools](#92-painting-tools)
  - [9.3 Shape tools](#93-shape-tools)
  - [9.4 Selection tools](#94-selection-tools)
  - [9.5 Transform, crop, and utility tools](#95-transform-crop-and-utility-tools)
  - [9.6 Modifier keys and gesture reference](#96-modifier-keys-and-gesture-reference)
- [10. Color and palette management](#10-color-and-palette-management)
- [11. Working with layers](#11-working-with-layers)
- [12. Animation workflow](#12-animation-workflow)
  - [12.1 Timeline editing](#121-timeline-editing)
  - [12.2 Onion skinning and playback controls](#122-onion-skinning-and-playback-controls)
  - [12.3 Previewing animations](#123-previewing-animations)
- [13. AI assistance](#13-ai-assistance)
  - [13.1 Preparing the environment](#131-preparing-the-environment)
  - [13.2 Using the AI panel](#132-using-the-ai-panel)
  - [13.3 Managing AI output](#133-managing-ai-output)
- [14. Background removal and palette conformance](#14-background-removal-and-palette-conformance)
- [15. Document, import, and export operations](#15-document-import-and-export-operations)
  - [15.1 Creating, opening, and saving documents](#151-creating-opening-and-saving-documents)
  - [15.2 Importing animation files](#152-importing-animation-files)
  - [15.3 Exporting sprites and animations](#153-exporting-sprites-and-animations)
- [16. Scripting and automation](#16-scripting-and-automation)
- [17. Settings reference](#17-settings-reference)
- [18. Keyboard shortcut guide](#18-keyboard-shortcut-guide)
- [19. Workflow tips and best practices](#19-workflow-tips-and-best-practices)
- [20. Troubleshooting](#20-troubleshooting)
- [21. Glossary](#21-glossary)
- [22. Additional resources](#22-additional-resources)

---

## 1. Welcome
Pixel-Portal is a dedicated pixel-art and animation editor built with Python and PySide6. It combines a crisp, tile-aware canvas with intuitive animation controls, palette management, scripting hooks, and optional AI-assisted generation. Whether you are blocking out small sprites or building longer animation loops, this manual explains every feature so you can work efficiently from day one.

## 2. System Requirements
- **Operating system:** Windows 10+, macOS 12+, or a modern Linux distribution capable of running Python 3.12 or later.
- **Hardware:** Any CPU capable of running Qt applications; 8 GB RAM is recommended for comfortable animation work. Dedicated GPUs accelerate AI features but are not required for drawing.
- **Display:** A 1080p monitor or larger is recommended. Pixel-Portal adapts to HiDPI screens automatically.
- **Dependencies:** Python 3.12+, Qt platform plugins (installed with PySide6), and Pillow for file import/export. Optional AI features depend on PyTorch, diffusers, and related libraries (see Section 13).

## 3. Installation and Setup

### 3.1 Standard desktop installation
1. Install Python 3.12 or newer from python.org or via your OS package manager.
2. Clone or download the Pixel-Portal repository:
   ```bash
   git clone https://github.com/your-username/Pixel-Portal.git
   cd Pixel-Portal
   ```
3. (Recommended) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # macOS/Linux bash
   source .venv/bin/activate
   ```
4. Install dependencies for the full desktop experience:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Launch the application with `python -m portal.main`. The main window should appear with the default workspace layout.

### 3.2 Minimal and headless environments
For automated pipelines or lightweight testing you can install the trimmed dependency set:
```bash
pip install -r requirements-headless.txt
```
When running without a display server (CI or remote shell), export the Qt offscreen platform before launching:
```bash
export QT_QPA_PLATFORM=offscreen  # Linux/macOS
set QT_QPA_PLATFORM=offscreen     # Windows cmd
```
Headless mode disables the GUI but still allows automated script execution and tests.

### 3.3 Optional AI dependencies
The AI panel relies on the following libraries:
- `torch` with CUDA (optional but highly recommended for fast generation)
- `diffusers`
- `transformers`
- `safetensors`
- `onnxruntime` and `rembg` for background removal
Install them with:
```bash
pip install -r requirements.txt  # includes AI stack
```
If GPU acceleration is required, install the PyTorch build that matches your CUDA runtime before installing the remaining packages.

### 3.4 Updating to a newer build
1. Pull the latest code: `git pull origin main`.
2. Update dependencies: `pip install -r requirements.txt --upgrade`.
3. Launch Pixel-Portal to apply any migration prompts. Settings are retained in `settings.ini` and remain compatible with newer versions.

## 4. Launching Pixel-Portal

### 4.1 First run
Executing `python -m portal.main` opens the main window, initializes an empty document, and preloads default palettes. If the app detects AI libraries or custom scripts, the corresponding panels appear automatically. The window title includes the current document name and an asterisk when unsaved changes are present.

### 4.2 Command-line tips
- Launch Pixel-Portal from the repository root so relative asset paths (icons, palettes) resolve correctly.
- Set environment variables such as `QT_QPA_PLATFORM=offscreen` before launching when working in headless or remote sessions.
- Reset the application to factory defaults by deleting or renaming `settings.ini` before the next launch.

### 4.3 Where Pixel-Portal stores preferences
User preferences are persisted in `settings.ini` at the application root. The file records:
- Last used directory for open/save dialogs
- Grid visibility, spacing, and colors
- Canvas background image mode and opacity
- Ruler helper configuration
- Stored negative prompt text for AI generation
Delete this file to revert to factory defaults. Project assets, palettes, and exported media are stored wherever you choose to save them.

## 5. Understanding Pixel-Portal documents
A Pixel-Portal project is built from the following layers:
- **Document:** Defines canvas size, resolution, playback settings, and metadata. Native `.aole` files preserve the full layer stack, animation frames, palette assignments, and undo history metadata.
- **Frames:** Each animation frame owns its own layer stack. The timeline maps playback frames to key frames and repeats frames based on the playback range.
- **Layers:** Individual raster images stacked to form the final artwork. Layers carry visibility, opacity, and names. Commands such as drawing, transforms, and filters operate on the active layer.
- **Selection:** Tools can limit edits to specific regions. Selections affect painting commands, fills, and clipboard operations.
- **Undo/Redo:** Every command is undoable. The undo stack is cleared when a new document is created or an animation is imported.

## 6. Tour of the workspace

### 6.1 Canvas and animation timeline
- The **canvas** occupies the center of the window, displaying the current frame with pixel-perfect zooming. Onion skin ghosts and tile previews render directly on the canvas for accurate placement.
- The **timeline** sits beneath the canvas. It shows frame indices, onion skin range handles, auto-key status, and playback position. Drag the playhead or scroll the mouse wheel over the timeline to scrub, and use the context menu for frame insertion or deletion.

### 6.2 Toolbars
- The **top toolbar** contains file commands, undo/redo, brush width slider, brush shape buttons (circular, square, pattern), mirror toggles (X/Y), ruler toggle, grid toggle, and AI panel toggle.
- The **left toolbar** hosts grouped tools. Clicking a group cycles through related tools (for example, pressing `S` repeatedly cycles the rectangle, ellipse, and line tools). Active primary/secondary colors appear at the top; right-click the active color to add it to the palette.
- The **color toolbar** along the bottom edge mirrors the active palette. Clicking a swatch sets the foreground color, right-click removes it, and the context menu offers import/export options.

### 6.3 Dockable panels
- **Layers dock:** Manage the layer stack, toggle visibility, adjust opacity sliders, rename layers, and invoke context menu commands such as Merge Down or Duplicate.
- **Preview dock:** Plays the animation in a floating window, useful for monitoring the final timing while editing.
- **AI dock:** Provides prompt fields, model pickers, output-area controls, and generation progress indicators (visible when AI dependencies load).
- **Other docks:** Depending on plugins, additional panels (such as reference images or script controls) may appear. All docks follow Qt’s docking system: drag their title bars to float or dock them on any screen edge.

### 6.4 Status bar
The status bar reports live information:
- Cursor position relative to the document origin
- Current zoom level
- Selection width and height
- Transform angle and scale during rotation/scale operations
- Ruler measurement when the helper is active
When the canvas is idle, transform readouts disappear to keep the status bar uncluttered.

### 6.5 Customising the layout
- Drag dock panels to rearrange them. Drop indicators highlight valid docking targets.
- Double-click a dock title to toggle between floating and docked states.
- Reopen hidden panels from **Windows → Panels** or **Windows → Toolbars** if parts of the UI disappear off-screen.
- Toolbar visibility can be toggled from **View → Toolbars**. Custom arrangements persist between sessions via `settings.ini`.

## 7. Quick start workflow
1. Choose **File → New** (or press `Ctrl+N`) to create a document. Set width/height manually or use preset buttons (16×16, 32×32, 64×64, 128×128).
2. Select the **Pen** tool (`B`) from the toolbar. Adjust brush size with the slider on the top toolbar.
3. Set your foreground color from the palette. Use the **Eyedropper** (`I` or hold `Alt`) to sample pixels from the canvas.
4. Sketch on the canvas. Middle mouse button pans and the mouse wheel zooms toward the cursor for precise navigation.
5. Add new layers from the Layers dock or press the “+” button beneath the layer list. Rename a layer by double-clicking its title.
6. To animate, move the timeline playhead, enable **Auto-Key**, and draw on subsequent frames. Onion skin controls help visualize adjacent frames.
7. Save progress with **File → Save** (`Ctrl+S`). Use the `.aole` format for full fidelity or export PNGs/GIFs when ready to share.

## 8. Canvas navigation and display controls
- **Zoom:** Use the mouse wheel to zoom toward the cursor. The canvas recenters automatically to keep the hovered pixel in place.
- **Pan:** Middle mouse button drag to reposition the canvas.
- **Grid:** Toggle the pixel grid from the toolbar or **View → Grid**. Major/minor spacing and colors are configurable in Settings.
- **Tile preview:** Enable **View → Tile Preview** to repeat the canvas in a tiled arrangement—ideal for seamless textures.
- **Onion skin:** Onion skin options sit on the timeline (previous/next frame count and tint colors). Enable them when animating to view ghosted frames around the current key.
- **Backgrounds:** Choose between checkered transparency, solid colors (white, black, gray, magenta), or a custom color/image. Image backgrounds can be fit, stretched, filled, or centered with adjustable opacity.
- **Ruler helper:** Activate from the toolbar. Drag the ruler endpoints on the canvas to measure distances; the status bar shows the measurement in pixels. Configure segment count in Settings.
- **Mirror guides:** Toggle horizontal or vertical mirroring to draw symmetrically. Drag the mirror axis handles on the canvas to reposition them.

## 9. Drawing, selection, and transform tools

### 9.1 Choosing tools and brush settings
- Click toolbar icons or press shortcuts (displayed in tooltips) to select a tool. Grouped tools share the same shortcut; press it repeatedly to cycle.
- Adjust brush width via the slider in the top toolbar; the numeric label updates in real time.
- Brush shape buttons toggle circular, square, or pattern brushes. Pattern brushes use the last brush created from a selection (see Section 9.6).
- Mirroring buttons enable simultaneous strokes across axes. Combine X and Y for quadrants.

### 9.2 Painting tools
- **Pen (`B`):** Draws solid pixels with optional mirror and tile preview support. Right-click temporarily switches to the eraser.
- **Eraser (`E`):** Removes pixels while respecting selections. Hold `Alt` to sample colors even while erasing.
- **Bucket (`F`):** Flood-fills contiguous regions. Enable tile preview to fill across wrapped edges.
- **Picker (`I`):** Samples color under the cursor. Holding `Alt` temporarily activates the picker while any drawing tool is active.
- **Pattern brush:** After running **Edit → Create Brush**, the Pen tool stamps the captured image. Pattern brushes respect selections and tile preview.

### 9.3 Shape tools
- **Line (cycle with `S`):** Draws straight lines with current brush settings. Holding `Shift` constrains angles to 45° increments.
- **Rectangle (cycle with `S`):** Draws filled or outlined rectangles depending on brush width. Hold `Shift` to force squares.
- **Ellipse (cycle with `S`):** Draws ellipses or circles (when `Shift` is held). Preview overlays show the result before committing.

### 9.4 Selection tools
- **Rectangle Select (`V` cycle):** Drag to select a rectangular region. Hold `Shift` for square selections, `Ctrl` to add to the current selection, and `Alt` to subtract.
- **Circle Select (`V` cycle):** Similar modifiers, but for circular/elliptical regions.
- **Lasso Select (`V` cycle):** Freeform selection path. Close the loop manually or release the mouse to auto-complete. Use `Ctrl`/`Alt` to add or subtract just like the rectangle tool.
- **Color Select (`V` cycle):** Click to select pixels sharing the sampled color on the active layer. Hold `Ctrl` to sample the color across the entire layer instead of limiting to contiguous regions.
Selections support move handles for repositioning. Use **Select → Invert** (`Ctrl+I`) or **Select → None** (`Ctrl+D`) to adjust.

### 9.5 Transform, crop, and utility tools
- **Transform (`M`):** Combines move, rotate, and scale gizmos. Drag inside the marquee to move, handles to scale, and the corner rotation handle to rotate. The status bar displays angle and scale factors in real time. Hold `Shift` to constrain rotation to 15° increments and maintain aspect ratio while scaling.
- **Crop:** Drag the bounding box handles to adjust document size. The tool supports expanding the canvas and cropping down; commit the change via the confirmation buttons on the overlay.
- Use the layer context menu options such as **Select Opaque** when you need to isolate pixels without leaving the active tool.

### 9.6 Modifier keys and gesture reference
- **Alt (any paint tool):** Eyedropper
- **Ctrl (paint tools):** Temporarily activates the Transform tool while pressed
- **Shift (shape/select tools):** Constrain proportions or angles
- **Right-click (paint tools):** Use the eraser color (transparent)
- **Middle-click:** Pan canvas
- **Mouse wheel:** Zoom around the cursor
- **Ctrl+click a layer entry:** Selects that layer's opaque pixels without changing the active layer

## 10. Color and palette management
- Active foreground/background swatches appear at the top of the toolbar. Click a swatch to open a color picker or right-click the active swatch to add it to the palette.
- The palette grid stores up to 256 colors. Left-click applies the color, right-click removes it from the palette.
- Import palette from an image via **Palette → Load From Image**. Pixel-Portal scans up to 256 unique colors.
- Export the palette as a PNG color strip with **Palette → Save as PNG** for sharing with other tools.
- Palettes persist in `palettes/default.colors`. Editing the file outside Pixel-Portal allows batch updates; reload from the Palette menu to apply changes.

## 11. Working with layers
- Add a new layer with the “+” button, duplicate via the context menu, and delete with the trash icon.
- Drag layers to reorder them. Dragging respects undo/redo and updates the canvas immediately.
- Toggle visibility by clicking the eye icon next to each layer. Opacity sliders provide live previews while dragging; releasing commits an undoable command.
- Double-click a layer name to rename it. Layer thumbnails refresh automatically after drawing.
- Right-click a layer for advanced commands: **Merge Down**, **Merge Down (Current Frame)**, **Duplicate**, **Select Opaque**, **Remove Background**, and **Collapse Layers** (flattens the entire stack into a single layer).
- Collapse Layers preserves the active frame while converting all layers into one, useful for exporting flattened sprites.
- Use **Layer → Remove Background** to launch the background removal dialog and choose whether to apply to the current key or all keys in the active layer.

## 12. Animation workflow

### 12.1 Timeline editing
- Click in the timeline to move the playhead. Drag to scrub through frames.
- Right-click the timeline to insert frames, duplicate frames, delete frames, or adjust keyframe spans.
- Auto-key ensures that drawing on a frame automatically creates a key for the active layer. Toggle it from the timeline controls.
- The frame counter displays playback length and the currently selected frame index. Adjust total playback frames to introduce holds without adding duplicate keys.

### 12.2 Onion skinning and playback controls
- Onion skin sliders define how many previous/next frames appear and their opacity tint.
- Playback controls (Play/Pause, FPS slider, loop toggle) live beneath the timeline. Press `Space` to toggle playback from anywhere in the window.
- FPS adjustments update both the animation player and exported animation defaults.

### 12.3 Previewing animations
- The Preview dock mirrors the main playhead. Dock it beside the canvas for side-by-side reference or float it on a secondary display.
- Preview playback can be triggered independently of the main timeline to inspect loops at different zoom levels. The preview uses bilinear scaling to show smooth results while preserving pixel-perfect rendering in the main canvas.

## 13. AI assistance

### 13.1 Preparing the environment
Ensure the optional AI libraries are installed (Section 3.3). GPU acceleration requires the appropriate PyTorch build. Without the dependencies, the AI dock remains hidden and menu options are disabled.

### 13.2 Using the AI panel
- Open the dock via the toolbar AI button or **View → Windows → Panels → AI**.
- Provide a **Prompt** and optional **Negative Prompt**. Default negative prompts are stored in Settings and prefilled at launch.
- Choose the model (Stable Diffusion 1.5, SDXL, or any configured checkpoint), sampler, steps, guidance strength, and denoising strength.
- The **Output Area** button activates draggable handles on the canvas defining where the generated image is placed. Resize or reposition the rectangle to target part of the frame.
- Trigger generation with **Generate** (text-to-image) or **Generate from Frame** (image-to-image). A progress bar and cancel button manage long operations.

### 13.3 Managing AI output
- Results appear as new layers in the active frame, preserving existing artwork.
- Enable **Background Removal** (requires `rembg` and `onnxruntime`) to automatically isolate the subject after generation.
- AI prompts and parameters persist across sessions. Reset them from the AI tab in Settings if needed.

## 14. Background removal and palette conformance
- Launch **Layer → Remove Background** to choose between processing the current keyframe or all keys in the active layer. The operation is undoable and respects transparent pixels.
- **Layer → Conform to Palette** remaps colors to the active palette grid, ensuring exported sprites stay within a controlled color set. This is especially helpful when using AI generations or scanned artwork that introduces stray colors.

## 15. Document, import, and export operations

### 15.1 Creating, opening, and saving documents
- **File → New** (`Ctrl+N`): set width/height with numeric inputs or preset buttons.
- **File → Open** (`Ctrl+O`): supports `.aole`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, and `.tiff` files. Raster files import as single-layer documents.
- **File → Open as Key:** imports an image directly into the current timeline position as a keyframe without replacing the existing document.
- **File → Save / Save As:** choose `.aole` for complete projects, or export to `.png`, `.jpg`, `.bmp`, `.tif`, `.tiff`. Pixel-Portal warns if the format cannot store layers/animation data.
- Unsaved changes trigger a confirmation dialog when closing or opening another file.

### 15.2 Importing animation files
- Use **File → Import Animation** to load GIF, APNG, PNG sequence, WebP, or TIFF animation data. Pixel-Portal reads embedded metadata to preserve frame delays and playback ranges.
- Imported animations populate the frame manager with individual keyframes. The application adjusts the playback frame count and FPS automatically, then resets the undo stack.

### 15.3 Exporting sprites and animations
- **File → Export Animation** outputs GIF, APNG, or WebP. Choose the format from the save dialog filter; Pixel-Portal ensures the file extension matches the selected option.
- The export inherits the current playback range and FPS. Adjust them on the timeline before exporting to control loop length and pacing.
- For sprite sheets, export individual frames as PNGs by stepping through the timeline and using **File → Save As** with unique filenames.

## 16. Scripting and automation
- Place Python scripts inside the `scripts/` directory. Each script should define a `SCRIPT_INFO` dictionary describing its name and parameters, plus a `run(api, params)` function that receives the scripting API.
- Scripts appear under **Scripting** in the main menu. Selecting one opens a parameter dialog that supports text fields, sliders, checkboxes, color pickers, and dropdowns.
- The scripting API grants access to the document, layers, and drawing commands while ensuring operations remain undoable. Use `api.create_layer()` to add layers and `api.modify_layer()` to perform drawing with built-in undo support.
- Scripts execute on the main thread. Long-running operations should provide progress feedback via custom dialogs to keep the UI responsive.

## 17. Settings reference
Open **Edit → Settings** (`Ctrl+,`) to configure:
- **Grid tab:** Toggle major/minor grids, set spacing (1–1024 px), and choose colors.
- **Canvas tab:** Pick background image mode (Fit, Stretch, Fill, Center), adjust background image opacity, and set ruler segment count.
- **AI tab:** Manage the default negative prompt text used by the AI panel.
Use the **Reset to Defaults** button in each tab to revert to factory values. Apply commits changes without closing the dialog; OK saves and closes; Cancel discards pending edits.

## 18. Keyboard shortcut guide
- **File:** New (`Ctrl+N`), Open (`Ctrl+O`), Save (`Ctrl+S`), Save As (`Ctrl+Shift+S`).
- **Edit:** Undo (`Ctrl+Z`), Redo (`Ctrl+Shift+Z`), Cut (`Ctrl+X`), Copy (`Ctrl+C`), Paste (`Ctrl+V`), Paste as New Image (`Ctrl+Shift+V`), Clear (`Delete`).
- **Selection:** Select All (`Ctrl+A`), Select None (`Ctrl+D`), Invert Selection (`Ctrl+I`).
- **Image:** Resize (`Ctrl+R`).
- **Tools:** Pen (`B`), Eraser (`E`), Bucket (`F`), Picker (`I`), Transform (`M`), Shape group (`S`), Selection group (`V`).
- **Playback:** Play/Pause (`Space`).
- **Preferences:** Settings (`Ctrl+,`).
Shortcuts can be customised by editing the Qt action definitions in the source if required.

## 19. Workflow tips and best practices
- **Work destructively only when needed:** Duplicate layers before drastic edits to preserve originals. Collapsing layers is undoable but easier to manage when working on copies.
- **Use auto-key sparingly:** Enable it while animating active layers, then disable to prevent accidental key creation when editing hold frames.
- **Take advantage of tile preview:** When designing seamless textures, enable tile preview early to catch seams.
- **Create custom brushes:** Select an area (with or without transparency) and run **Edit → Create Brush**. Switch the brush mode to Pattern to stamp it repeatedly.
- **Leverage palette conformance:** After importing artwork or AI generations, run **Conform to Palette** to maintain consistent color counts for retro platforms.
- **Save iterations:** Use incremental filenames (`character_walk_v1.aole`, `character_walk_v2.aole`) to archive milestones without overwriting previous work.
- **Back up settings:** Copy `settings.ini` and `palettes/default.colors` when migrating to another machine to retain your environment.

## 20. Troubleshooting
- **Qt platform plugin error:** Ensure the `QT_QPA_PLATFORM` environment variable matches your environment. Remove it when running with a display server.
- **Missing icons or fonts:** Confirm you launched Pixel-Portal from the repository root so relative asset paths resolve correctly.
- **AI panel disabled:** Install the required AI dependencies and restart the app. The panel automatically enables when imports succeed.
- **Performance issues with large animations:** Lower onion skin counts, hide unused layers, and disable tile preview while working on high-resolution frames.
- **Unexpected palette resets:** Verify write permissions for the `palettes` directory. Palette updates are saved immediately when colors change.
- **Brush stamping offset:** Ensure no selection is active; selections constrain brush placement. Use **Select → None** to clear.

## 21. Glossary
- **AOLE:** Pixel-Portal’s native archive format storing layers, frames, and metadata.
- **Auto-key:** Timeline mode that inserts keyframes automatically when painting on unkeyed frames.
- **Denoising strength:** AI setting controlling how closely the generated output adheres to the source frame (lower values preserve more of the original).
- **Mirror axis:** Draggable guidelines on the canvas used for symmetry drawing.
- **Onion skin:** Translucent overlay of neighbouring frames for animation planning.
- **Pattern brush:** Custom brush created from a selection that can be stamped with the Pen tool.
- **Tile preview:** Canvas mode that repeats the document in a grid for seamless texture design.

## 22. Additional resources
- Browse the `scripts/` directory for automation examples such as tile generators and outline tools.
- Explore the `palettes/` folder for curated color sets that pair well with classic pixel-art styles.
- Review `todo.txt` for upcoming features and community contribution ideas.
- Join the community forum or Discord (if available) to share feedback, report bugs, and collaborate on new tools.
