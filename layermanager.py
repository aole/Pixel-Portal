"""
layermanager.py
Bhupendra Aole
1/19/2020
"""

class LayerManager:
    def __init__(self):
        self.layers = []
        self.currentLayer = -1
        self.width = 0
        self.height = 0
        
    def appendSelect(self, layer):
        self.currentLayer = len(self.layers)
        self.layers.append(layer)
    
    def select(self, layer):
        self.currentLayer = self.layers.index(layer)
    
    def selectIndex(self, index):
        self.currentLayer = index
    
    def current(self):
        return self.self.layers[self.currentLayer]
    
    def remove(self, layer):
        if len(self.layers)>1:
            del self.layers[self.layers.index(layer)]
    
    