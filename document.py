"""
document.py
Bhupendra Aole
1/31/2020
"""

import sys
from pickle import load, dump

class Document:
    def __init__(self, width, height):
        self.layers = []
        self.currentLayer = -1
        self.width = width
        self.height = height
        
        self.currentFrame = 1
        self.fps = 8
        self.selectedSlot = [1, 0, 1]
        self.keys = {}
        self.totalFrames = 8

    def Save(self, filename):
        file = open(filename, 'wb') 
        dump(self, file)
        file.close()
        
    def Load(filename):
        file = open(filename, 'rb') 
        data = load(file)
        file.close()
        return data
            