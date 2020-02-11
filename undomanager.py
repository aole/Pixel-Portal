"""
undomanager.py
Bhupendra Aole
1/19/2020
"""

from wx import Command, Bitmap, CommandProcessor, Region

from settings import *

class AddLayerCommand(Command):
    def __init__(self, layermgr, index, layer):
        super().__init__(True)

        self.layermgr = layermgr
        self.index = index
        self.layer = layer
        
    def Do(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.AppendSelect(self.layer)
        return True

    def Undo(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.Remove()
        return True

    def __str__(self):
        return "Add "+self.layer.name
        
class DuplicateLayerCommand(Command):
    def __init__(self, layermgr, oldidx, newidx):
        super().__init__(True)

        self.layermgr = layermgr
        self.oldidx = oldidx
        self.newidx = newidx
        
    def Do(self):
        self.layermgr.currentLayer = self.oldidx
        self.layermgr.DuplicateAndSelectCurrent()
        return True

    def Undo(self):
        self.layermgr.currentLayer = self.newidx
        self.layermgr.Remove()
        return True

    def __str__(self):
        return "Duplicate "+self.layermgr[self.oldidx].name

class FlipCommand(Command):
    def __init__(self, layermgr, horizontal=True):
        super().__init__(True)
        self.layermgr = layermgr
        self.horizontal = horizontal
        
    def Do(self):
        self.layermgr.Flip(self.horizontal)
        return True

    def Undo(self):
        self.layermgr.Flip(self.horizontal)
        return True

    def __str__(self):
        return "Flip "+("Horizontally" if self.horizontal else "Vertically")

class KeyDeleteCommand(Command):
    def __init__(self, anim, frame, key):
        super().__init__(True)
        self.anim = anim
        self.frame = frame
        self.key = key
    
    def Do(self):
        self.anim.DeleteKey(self.frame)
        return True

    def Undo(self):
        self.anim.InsertKey(self.frame, self.key)
        return True

    def __str__(self):
        return "Delete Key @"+str(self.frame)

class KeyInsertCommand(Command):
    def __init__(self, anim, frame, key):
        super().__init__(True)
        self.anim = anim
        self.frame = frame
        self.key = key
        
    def Do(self):
        self.anim.InsertKey(self.frame, self.key)
        return True

    def Undo(self):
        self.anim.DeleteKey(self.frame)
        return True

    def __str__(self):
        return "Insert Key @"+str(self.frame)

class KeyMoveCommand(Command):
    def __init__(self, anim, tofrm, frmfrm):
        super().__init__(True)
        self.anim = anim
        self.frmfrm = frmfrm
        self.tofrm = tofrm
        
    def Do(self):
        key = self.anim.DeleteKey(self.frmfrm)
        self.anim.InsertKey(self.tofrm, key)
        return True

    def Undo(self):
        key = self.anim.DeleteKey(self.tofrm)
        self.anim.InsertKey(self.frmfrm, key)
        return True

    def __str__(self):
        return "Move Key: "+str(self.frmfrm)+" to "+str(self.tofrm)

class MergeDownLayerCommand(Command):
    def __init__(self, layermgr, idx, layerAbove, layerBelow):
        super().__init__(True)

        self.layermgr = layermgr
        self.idx = idx
        self.layerAbove = layerAbove
        self.layerBelow = layerBelow
        
    def Do(self):
        self.layermgr.SelectIndex(self.idx)
        self.layermgr.MergeDown()
        return True

    def Undo(self):
        self.layermgr.SelectIndex(self.idx)
        self.layermgr.RemoveSelected(True)
        self.layermgr.AppendSelect(self.layerBelow.Copy())
        self.layermgr.AppendSelect(self.layerAbove.Copy())
        return True

    def __str__(self):
        return "Merge "+self.layerAbove.name+" + "+self.layerBelow.name

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

    def __str__(self):
        return self.before.name+" -> paint -> "+ self.after.name
       
class RearrangeLayerCommand(Command):
    def __init__(self, layermgr, frmpos, topos):
        super().__init__(True)

        self.layermgr = layermgr
        self.frmpos = frmpos
        self.topos = topos
        
    def Do(self):
        self.layermgr.RearrangeIndex(self.frmpos, self.topos)
        return True

    def Undo(self):
        self.layermgr.RearrangeIndex(self.topos, self.frmpos)
        return True

    def __str__(self):
        return "Rearrange "+str(self.frmpos)+' -> '+str(self.topos)
        
class RemoveLayerCommand(Command):
    def __init__(self, layermgr, index, layer):
        super().__init__(True)

        self.layermgr = layermgr
        self.index = index
        self.layer = layer
        
    def Do(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.Remove()
        return True

    def Undo(self):
        self.layermgr.currentLayer = self.index
        self.layermgr.AppendSelect(self.layer)
        return True

    def __str__(self):
        return "Remove "+self.layer.name
        
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

    def __str__(self):
        return str(self.blayermgr.width)+", "+str(self.blayermgr.height)+" -> Resize -> "+str(self.alayermgr.width)+", "+str(self.alayermgr.height)
        
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
        super().__init__(GetSetting('General', 'Number Of Undos'))

    def Store(self, command):
        super().Store(command)
