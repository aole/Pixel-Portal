from unittest.mock import MagicMock
from portal.undo import UndoManager

def test_add_command():
    """Test that a command is added to the undo stack and that the redo stack is cleared."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)

    assert len(undo_manager.undo_stack) == 1
    assert undo_manager.undo_stack[0] == mock_command
    assert len(undo_manager.redo_stack) == 0

def test_undo():
    """Test that the last command is undone and moved to the redo stack."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)

    undo_manager.undo()

    mock_command.undo.assert_called_once()
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 1
    assert undo_manager.redo_stack[0] == mock_command

def test_redo():
    """Test that the last undone command is redone and moved to the undo stack."""
    undo_manager = UndoManager()
    mock_command = MagicMock()
    undo_manager.add_command(mock_command)
    undo_manager.undo()

    undo_manager.redo()

    mock_command.execute.assert_called_once()
    assert len(undo_manager.undo_stack) == 1
    assert undo_manager.undo_stack[0] == mock_command
    assert len(undo_manager.redo_stack) == 0
