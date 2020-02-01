"""
document.py
Bhupendra Aole
1/31/2020
"""

import sys
from pickle import loads, dumps
from zipfile import ZipFile, ZIP_LZMA

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
        with ZipFile(filename, 'w', ZIP_LZMA) as zf:
            data = dumps(self)
            zf.writestr('data', data)
        
    def Load(filename):
        with ZipFile(filename, compression=ZIP_LZMA) as zf:
            with zf.open('data') as data:
                data = loads(data.read())
        return data
            