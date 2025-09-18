# Pixel-Portal Image Editor

Pixel-Portal is a lightweight, cross-platform image editor built with Python and PySide6. It provides a simple yet powerful interface for image manipulation, featuring basic drawing tools, layer management, and cutting-edge AI-powered image generation capabilities.

## Key Features

- **Drawing Tools**: A variety of tools for drawing and painting, including Pen, Bucket, Ellipse, Line, and Rectangle.
- **Layer Management**: Full support for layers, allowing for complex image compositions. You can add, remove, reorder, and merge layers.
- **Frame-aware Rendering**: Canvas compositing and drawing tools operate on the active frame so animation edits stay isolated.
- **Timeline Playback**: Play, pause, and loop your animation directly from the timeline, adjusting FPS and total frames without leaving the editor.
- **Selection Tools**: Tools for selecting parts of the image, including Rectangle, Circle, and Lasso selections.
- **Image Manipulation**: Resize, crop, and flip the canvas.
- **AI-Powered Image Generation**: Integrated with state-of-the-art AI models to generate images from text prompts.
- **Optional Background Removal**: Strip backgrounds from generated images using `rembg` (requires `onnxruntime`).
- **Background Options**: Choose checkered, solid colors, or a custom image for the canvas background.
- **Undo/Redo**: A robust undo/redo system to make editing easier and non-destructive.
- **Customizable Interface**: A simple and intuitive interface that can be customized to your liking.
- **Procedural Islands**: Craft colorful island layers with adjustable water coverage, large landmasses, and optional biomes via the Island Creator script.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/Pixel-Portal.git
   cd Pixel-Portal
   ```

2. **Create a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

### Running the Application

Once the dependencies are installed, you can run the application with the following command:

```sh
python -m portal.main
```

## Running the Tests

The test suite relies on PySide6 and must run in a headless environment. Set the
`QT_QPA_PLATFORM` environment variable to `offscreen` and execute each test file
individually:

```sh
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_core.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_dialogs.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_document_and_layers.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_drawing_tools.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_selection_tools.py
```

## Working with Frames

Pixel-Portal's document model now supports multiple frames inside a single
project. Frames wrap their own layer stack and can be accessed through the
`Document.frame_manager` helper. A few convenience methods are available on the
document itself:

- `Document.add_frame()` creates a fresh frame that mirrors the document size.
- `Document.remove_frame(index)` removes a frame (while ensuring at least one
  frame remains).
- `Document.select_frame(index)` switches the active frame and therefore the
  layer manager the UI interacts with.
- `Document.render_current_frame()` composites the active frame into a single
  `QImage`.
- `Document.add_layer_manager_listener(callback)` registers a hook that fires
  whenever the active frame changes. This keeps UI components wired to the
  correct `LayerManager` as the selection moves between frames.

The existing `Document.layer_manager` attribute now resolves to the layer
manager belonging to the currently selected frame, so existing layer-centric
tooling continues to operate without modification.

Canvas compositing and the interactive tools now consult
`Document.frame_manager.active_layer_manager` directly. This keeps previews,
temporary overlays, and destructive edits scoped to the active frame while you
work across an animation.
