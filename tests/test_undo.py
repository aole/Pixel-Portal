from portal.undo import UndoManager
from unittest.mock import Mock

# Helper to create mock states
def create_mock_state(name):
    state = Mock()
    state.name = name
    state.clone.return_value = state # Clone returns the same mock
    return state

def test_add_undo_state():
    undo_manager = UndoManager()
    s1 = create_mock_state("state1")
    undo_manager.add_undo_state(s1)
    assert undo_manager.undo_stack == [s1]
    s2 = create_mock_state("state2")
    undo_manager.add_undo_state(s2)
    assert undo_manager.undo_stack == [s1, s2]

def test_undo():
    undo_manager = UndoManager()
    s1 = create_mock_state("state1")
    s2 = create_mock_state("state2")
    undo_manager.add_undo_state(s1)
    undo_manager.add_undo_state(s2)
    state = undo_manager.undo()
    assert state.name == "state1"
    assert undo_manager.undo_stack == [s1]
    assert undo_manager.redo_stack == [s2]

def test_redo():
    undo_manager = UndoManager()
    s1 = create_mock_state("state1")
    s2 = create_mock_state("state2")
    undo_manager.add_undo_state(s1)
    undo_manager.add_undo_state(s2)
    undo_manager.undo()
    state = undo_manager.redo()
    assert state.name == "state2"
    assert undo_manager.undo_stack == [s1, s2]
    assert undo_manager.redo_stack == []

def test_undo_redo_interleaved():
    undo_manager = UndoManager()
    s1 = create_mock_state("state1")
    s2 = create_mock_state("state2")
    s3 = create_mock_state("state3")
    undo_manager.add_undo_state(s1)
    undo_manager.add_undo_state(s2)
    undo_manager.add_undo_state(s3)

    state = undo_manager.undo()
    assert state.name == "state2"
    assert undo_manager.undo_stack == [s1, s2]
    assert undo_manager.redo_stack == [s3]

    state = undo_manager.undo()
    assert state.name == "state1"
    assert undo_manager.undo_stack == [s1]
    assert undo_manager.redo_stack == [s3, s2]

    state = undo_manager.redo()
    assert state.name == "state2"
    assert undo_manager.undo_stack == [s1, s2]
    assert undo_manager.redo_stack == [s3]

    state = undo_manager.redo()
    assert state.name == "state3"
    assert undo_manager.undo_stack == [s1, s2, s3]
    assert undo_manager.redo_stack == []

def test_add_after_undo():
    undo_manager = UndoManager()
    s1 = create_mock_state("state1")
    s2 = create_mock_state("state2")
    undo_manager.add_undo_state(s1)
    undo_manager.add_undo_state(s2)
    undo_manager.undo()
    s3 = create_mock_state("state3")
    undo_manager.add_undo_state(s3)
    assert undo_manager.undo_stack == [s1, s3]
    assert undo_manager.redo_stack == []

def test_undo_empty():
    undo_manager = UndoManager()
    state = undo_manager.undo()
    assert state is None
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []

def test_redo_empty():
    undo_manager = UndoManager()
    state = undo_manager.redo()
    assert state is None
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []
