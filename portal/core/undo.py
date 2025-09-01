from portal.core.command import Command


class UndoManager:
    def __init__(self):
        self.undo_stack: list[Command] = []
        self.redo_stack: list[Command] = []

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

    def add_command(self, command: Command):
        """
        Adds a command to the undo stack.
        This is called after a command has been executed.
        """
        self.undo_stack.append(command)
        self.redo_stack.clear()

    def undo(self):
        """
        Undoes the last command.
        """
        if not self.undo_stack:
            return
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)

    def redo(self):
        """
        Redoes the last undone command.
        """
        if not self.redo_stack:
            return
        command = self.redo_stack.pop()
        command.execute()
        self.undo_stack.append(command)
