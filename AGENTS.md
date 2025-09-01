# Instructions for AI Agents

## Running Tests

When running the test suite, you must set the `QT_QPA_PLATFORM` environment variable to `offscreen`. This is because the tests use PySide6, which requires a GUI, and the testing environment is headless.

Due to a segmentation fault that occurs when running the full test suite, the tests must be run on each file separately.

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
