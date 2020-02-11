"""
document.py
Bhupendra Aole
1/31/2020
"""

from pickle import loads, dumps
from zipfile import ZipFile, ZIP_LZMA

import os, tempfile

class Document:
    def __init__(self, width, height):
        self.layers = []
        self.currentLayer = -1
        self.width = width
        self.height = height
        
        self.currentFrame = 1
        self.fps = 8
        self.keys = {}
        self.totalFrames = 8

    def __repr__(self):
        return 'Document ('+str(self.width)+' '+str(self.height)+') '+str(len(self.layers))+' layers '+str(len(self.keys))+' keys'
        
    def Load(filename):
        with ZipFile(filename, compression=ZIP_LZMA) as zf:
            with zf.open('data') as data:
                data = loads(data.read())
        return data

    def Save(self, filename):
        with ZipFile(filename, 'w', ZIP_LZMA) as zf:
            data = dumps(self)
            zf.writestr('data', data)
        
if __name__ == '__main__':
    doc = Document(2,2)
    fd, file = tempfile.mkstemp(suffix='.aole', prefix='pxlprtl_')
    print(fd, file)
    doc.Save(file)
    print(Document.Load(file))
    os.close(fd)
    os.remove(file)
    