"""
undomanager.py
Bhupendra Aole
1/19/2020
"""

from wx import Command, Bitmap, CommandProcessor, Region

NUM_UNDOS = 100

class LayerCommand(Command):
    def __init__(self, layers, before, after):
        super().__init__(True)

        self.layers = layers
        self.before = before
        self.after = after

    def Do(self):
        self.layers.current().Blit(self.after)
        return True

    def Undo(self):
        self.layers.current().Blit(self.before)
        return True

class ResizeCommand(Command):
    def __init__(self, layers, before, after):
        super().__init__(True)

        self.layers = layers
        self.before = before
        self.after = after

    def Do(self):
        self.layers.width = self.after.width
        self.layers.height = self.after.height
        self.layers.surface = Layer(Bitmap.FromRGBA(self.after.width, self.after.height, 255, 255, 255, 255))
        self.layers.current().Draw(self.after)
        self.layers.set(Layer(Bitmap.FromRGBA(self.after.width, self.after.height, 0, 0, 0, 0)))
        return True

    def Undo(self):
        self.layers.width = self.before.width
        self.layers.height = self.before.height
        self.layers.surface = Layer(Bitmap.FromRGBA(self.before.width, self.before.height, 255, 255, 255, 255))
        self.layers.current().Draw(self.before)
        self.layers.set(Layer(Bitmap.FromRGBA(self.before.width, self.before.height, 0, 0, 0, 0)))
        return True

class SelectionCommand(Command):
    def __init__(self, canvas, before, after):
        super().__init__(True)
        
        self.canvas = canvas
        self.before = before
        self.after = after

    def Do(self):
        self.canvas.selection = Region(self.after)
        return True

    def Undo(self):
        self.canvas.selection = Region(self.before)
        return True

class UndoManager(CommandProcessor):
    def __init__(self):
        super().__init__(NUM_UNDOS)

    def Store(self, command):
        super().Store(command)
