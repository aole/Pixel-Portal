from portal.undo import UndoManager

def test_add_undo_state():
    undo_manager = UndoManager()
    undo_manager.add_undo_state("state1")
    assert undo_manager.undo_stack == ["state1"]
    undo_manager.add_undo_state("state2")
    assert undo_manager.undo_stack == ["state1", "state2"]

def test_undo():
    undo_manager = UndoManager()
    undo_manager.add_undo_state("state1")
    undo_manager.add_undo_state("state2")
    state = undo_manager.undo()
    assert state == "state1"
    assert undo_manager.undo_stack == ["state1"]
    assert undo_manager.redo_stack == ["state2"]

def test_redo():
    undo_manager = UndoManager()
    undo_manager.add_undo_state("state1")
    undo_manager.add_undo_state("state2")
    undo_manager.undo()
    state = undo_manager.redo()
    assert state == "state2"
    assert undo_manager.undo_stack == ["state1", "state2"]
    assert undo_manager.redo_stack == []

def test_undo_redo_interleaved():
    undo_manager = UndoManager()
    undo_manager.add_undo_state("state1")
    undo_manager.add_undo_state("state2")
    undo_manager.add_undo_state("state3")

    state = undo_manager.undo()
    assert state == "state2"
    assert undo_manager.undo_stack == ["state1", "state2"]
    assert undo_manager.redo_stack == ["state3"]

    state = undo_manager.undo()
    assert state == "state1"
    assert undo_manager.undo_stack == ["state1"]
    assert undo_manager.redo_stack == ["state3", "state2"]

    state = undo_manager.redo()
    assert state == "state2"
    assert undo_manager.undo_stack == ["state1", "state2"]
    assert undo_manager.redo_stack == ["state3"]

    state = undo_manager.redo()
    assert state == "state3"
    assert undo_manager.undo_stack == ["state1", "state2", "state3"]
    assert undo_manager.redo_stack == []

def test_add_after_undo():
    undo_manager = UndoManager()
    undo_manager.add_undo_state("state1")
    undo_manager.add_undo_state("state2")
    undo_manager.undo()
    undo_manager.add_undo_state("state3")
    assert undo_manager.undo_stack == ["state1", "state3"]
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
