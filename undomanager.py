"""
undomanager.py
Bhupendra Aole
1/19/2020
"""

from wx import Command, Bitmap, CommandProcessor, Region

NUM_UNDOS = 100

class PaintCommand(Command):
    def __init__(self, layermgr, index, before, after):
        super().__init__(True)

        self.layermgr = layermgr
        self.index = index
        self.before = before
        self.after = after

    def Do(self):
        self.layermgr.layers[self.index].PasteSource(self.after)
        return True

    def Undo(self):
        self.layermgr.layers[self.index].PasteSource(self.before)
        return True

class AddLayerCommand(Command):
    def __init__(self, layermgr, index, layer):
        super().__init__(True)

        self.layermgr = layermgr
        self.index = index
        self.layer = layer
        
    def Do(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.appendSelect(self.layer)
        return True

    def Undo(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.remove()
        return True

class RemoveLayerCommand(Command):
    def __init__(self, layermgr, index, layer):
        super().__init__(True)

        self.layermgr = layermgr
        self.index = index
        self.layer = layer
        
    def Do(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.remove()
        return True

    def Undo(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.appendSelect(self.layer)
        return True

class ResizeCommand(Command):
    def __init__(self, layermgr, blayermgr, alayermgr):
        super().__init__(True)

        self.layermgr = layermgr
        self.blayermgr = blayermgr
        self.alayermgr = alayermgr

    def Do(self):
        self.layermgr.Resize(self.alayermgr)
        return True

    def Undo(self):
        self.layermgr.Resize(self.blayermgr)
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
