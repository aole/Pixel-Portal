"""
document.py
Bhupendra Aole
1/31/2020
"""

from pickle import load, dump

class Document:
    def __init__(self, width, height):
        self.layers = []
        self.currentLayer = -1
        self.width = width
        self.height = height
        
        self.currentFrame = 0
        self.fps = 8
        self.selectedSlot = [1, 0, 1]
        self.keys = {}
        self.totalFrames = 8

    def Save(self, filename):
        file = open(filename, 'w') 
        dump(self, file)
    
    def Load(filename):
        file = open(filename, 'r') 
        return load(file)
        