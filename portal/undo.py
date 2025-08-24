class UndoManager:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

    def add_undo_state(self, state):
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack or len(self.undo_stack) == 1:
            return None
        state = self.undo_stack.pop()
        self.redo_stack.append(state)
        # Return a clone of the state to prevent modification
        return self.undo_stack[-1].clone()

    def redo(self):
        if not self.redo_stack:
            return None
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        # Return a clone of the state to prevent modification
        return state.clone()
