# Pixel-Portal Image Editor

Pixel-Portal is a lightweight, cross-platform image editor built with Python and PySide6. It provides a simple yet powerful interface for image manipulation, featuring basic drawing tools, layer management, and cutting-edge AI-powered image generation capabilities.

## Key Features

- **Drawing Tools**: A variety of tools for drawing and painting, including Pen, Bucket, Ellipse, Line, and Rectangle.
- **Layer Management**: Full support for layers, allowing for complex image compositions. You can add, remove, reorder, and merge layers.
- **Selection Tools**: Tools for selecting parts of the image, including Rectangle, Circle, and Lasso selections.
- **Image Manipulation**: Resize, crop, and flip the canvas.
- **AI-Powered Image Generation**: Integrated with state-of-the-art AI models to generate images from text prompts.
- **Undo/Redo**: A robust undo/redo system to make editing easier and non-destructive.
- **Customizable Interface**: A simple and intuitive interface that can be customized to your liking.

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
