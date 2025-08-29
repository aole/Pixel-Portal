from portal.undo import UndoManager
from portal.command import Command

class MockCommand(Command):
    def __init__(self):
        self.executed = 0
        self.undone = 0

    def execute(self):
        self.executed += 1

    def undo(self):
        self.undone += 1

def test_add_command():
    undo_manager = UndoManager()
    c1 = MockCommand()
    undo_manager.add_command(c1)
    assert undo_manager.undo_stack == [c1]
    c2 = MockCommand()
    undo_manager.add_command(c2)
    assert undo_manager.undo_stack == [c1, c2]

def test_undo():
    undo_manager = UndoManager()
    c1 = MockCommand()
    c2 = MockCommand()
    undo_manager.add_command(c1)
    undo_manager.add_command(c2)

    undo_manager.undo()

    assert c2.undone == 1
    assert c1.undone == 0
    assert undo_manager.undo_stack == [c1]
    assert undo_manager.redo_stack == [c2]

def test_redo():
    undo_manager = UndoManager()
    c1 = MockCommand()
    c2 = MockCommand()
    undo_manager.add_command(c1)
    undo_manager.add_command(c2)
    undo_manager.undo()

    c2.executed = 0 # Reset execute count
    undo_manager.redo()

    assert c2.executed == 1
    assert undo_manager.undo_stack == [c1, c2]
    assert undo_manager.redo_stack == []

def test_undo_redo_interleaved():
    undo_manager = UndoManager()
    c1 = MockCommand()
    c2 = MockCommand()
    c3 = MockCommand()
    undo_manager.add_command(c1)
    undo_manager.add_command(c2)
    undo_manager.add_command(c3)

    undo_manager.undo()
    assert c3.undone == 1
    assert undo_manager.undo_stack == [c1, c2]
    assert undo_manager.redo_stack == [c3]

    undo_manager.undo()
    assert c2.undone == 1
    assert undo_manager.undo_stack == [c1]
    assert undo_manager.redo_stack == [c3, c2]

    c2.executed = 0
    undo_manager.redo()
    assert c2.executed == 1
    assert undo_manager.undo_stack == [c1, c2]
    assert undo_manager.redo_stack == [c3]

    c3.executed = 0
    undo_manager.redo()
    assert c3.executed == 1
    assert undo_manager.undo_stack == [c1, c2, c3]
    assert undo_manager.redo_stack == []

def test_add_after_undo():
    undo_manager = UndoManager()
    c1 = MockCommand()
    c2 = MockCommand()
    undo_manager.add_command(c1)
    undo_manager.add_command(c2)
    undo_manager.undo()

    c3 = MockCommand()
    undo_manager.add_command(c3)

    assert undo_manager.undo_stack == [c1, c3]
    assert undo_manager.redo_stack == []

def test_undo_empty():
    undo_manager = UndoManager()
    undo_manager.undo() # Should not raise error
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []

def test_redo_empty():
    undo_manager = UndoManager()
    undo_manager.redo() # Should not raise error
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []
