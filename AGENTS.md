# Instructions for AI Agents

## Environment Setup for Unix/Test/Headless Runs

Use `requirements-headless.txt` when preparing a Unix, CI, or other headless/testing environment. This trimmed requirements file omits AI-specific dependencies (such as PyTorch and the diffusion stack) that are not required for automated testing. Install it with:

```bash
pip install -r requirements-headless.txt
```

## Running Tests

**Important:** Do not run any tests unless explicitly asked to do so.

When running the test suite, you must set the `QT_QPA_PLATFORM` environment variable to `offscreen`. This is because the tests use PySide6, which requires a GUI, and the testing environment is headless.

Due to a segmentation fault that occurs when running the full test suite, the tests must be run on each file separately.

If a test file consistently fails with a segmentation fault, even on the `main` branch, it should be skipped.

Example:
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_core.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_dialogs.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_document_and_layers.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_drawing_tools.py
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_selection_tools.py
```

## Committing Changes

When committing changes, please do not commit changes to `settings.ini` if the only change is to the `last_directory` setting. This is a user-specific setting and should not be part of the repository's history.

## AI Features

The AI features in this application require a specific hardware and software environment (e.g., a CUDA-enabled GPU and large model files) that may not be available in the testing environment. Therefore, any tests related to AI functionality should be skipped.
