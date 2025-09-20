# Pixel-Portal Image Editor

Pixel-Portal is a lightweight, cross-platform image editor built with Python and PySide6. It provides a simple yet powerful interface for image manipulation, featuring basic drawing tools, layer management, and cutting-edge AI-powered image generation capabilities.

## Key Features

- **Drawing Tools**: A variety of tools for drawing and painting, including Pen, Bucket, Ellipse, Line, and Rectangle.
- **Layer Management**: Full support for layers, allowing for complex image compositions. You can add, remove, reorder, and merge layers.
- **Frame-aware Rendering**: Canvas compositing and drawing tools operate on the active frame so animation edits stay isolated.
- **Timeline Playback**: Play, pause, and loop your animation directly from the timeline, adjusting FPS and total frames without leaving the editor.
- **Onion Skinning**: Preview previous and next frames directly on the canvas with adjustable ranges for confident animation tweaks.
- **Selection Tools**: Tools for selecting parts of the image, including Rectangle, Circle, and Lasso selections.
- **Image Manipulation**: Resize, crop, and flip the canvas.
- **AI-Powered Image Generation**: Integrated with state-of-the-art AI models to generate images from text prompts.
- **Optional Background Removal**: Strip backgrounds from generated images using `rembg` (requires `onnxruntime`).
- **Background Options**: Choose checkered, solid colors, or a custom image for the canvas background.
- **Undo/Redo**: A robust undo/redo system to make editing easier and non-destructive.
- **Customizable Interface**: A simple and intuitive interface that can be customized to your liking.
- **Native Document Format**: Save and reopen complete projects with `.aole` files that preserve layers and animation frames.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.12 or higher
- pip

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/Pixel-Portal.git
   cd Pixel-Portal
   ```

2. **Create a virtual environment:**
   ```sh
   python -m venv .venv
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
