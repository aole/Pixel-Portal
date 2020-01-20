"""
layermanager.py
Bhupendra Aole
1/19/2020
"""

import wx


class Layer(wx.Bitmap):
    layerCount = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = self.GetWidth()
        self.height = self.GetHeight()
        self.name = "Layer "+str(Layer.layerCount)
        Layer.layerCount += 1
        
    def Scaled(self, factor):
        bitmap = wx.Bitmap.FromRGBA(self.width * factor, self.height * factor, 0, 0, 0, 0)
        mdcd = wx.MemoryDC(bitmap)
        mdcs = wx.MemoryDC(self)
        mdcd.StretchBlit(0, 0,
                         self.width * factor, self.height * factor,
                         mdcs,
                         0,
                         0,
                         self.width, self.height)
        mdcd.SelectObject(wx.NullBitmap)
        mdcs.SelectObject(wx.NullBitmap)

        return bitmap

    def Clear(self, color=wx.Colour(0,0,0,0), clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))

        # gc.DrawRectangle(0, 0, *gc.GetSize())
        # weird bug ^^^ can't correctly draw a big rectangle in one go
        w, h = self.width, self.height
        for x in range(0, w, 60):
            for y in range(0, h, 60):
                gc.DrawRectangle(x, y, min(w, 60), min(h, 60))
        mdc.SelectObject(wx.NullBitmap)

    def GetPixel(self, x, y):
        mdc = wx.MemoryDC(self)
        return mdc.GetPixel(x, y)

    def SetPixel(self, x, y, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        gc.DrawRectangle(int(x-size/2+.5), int(y-size/2+.5), size, size)
        mdc.SelectObject(wx.NullBitmap)
        
    def SetPixels(self, pixels, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        for x, y in pixels:
            gc.DrawRectangle(x, y, 1, 1)
        mdc.SelectObject(wx.NullBitmap)

    # BUG?? FloodFill is painting with alpha=0
    def FloodFill(self, x0, y0, color, clip=None):
        pdc = wx.adv.PseudoDC()
        mdc = wx.MemoryDC(self)
        replace = mdc.GetPixel(x0, y0)
        
        mdc.SetBrush(wx.Brush(color))
        mdc.FloodFill(x0, y0, replace)
        return 
        
        gc = wx.GraphicsContext.Create(mdc)
        region = wx.Region(self, replace)
        w, h = self.width, self.height
        if not region.IsEmpty():
            region.Xor(0, 0, w, h)
            if clip and not clip.IsEmpty():
                region.Intersect(clip)
            gc.Clip(region)
            gc.SetBrush(wx.Brush(color))
            gc.SetPen(wx.NullPen)
            for x in range(0, w, 60):
                for y in range(0, h, 60):
                    gc.DrawRectangle(x, y, min(w, 60), min(h, 60))
            #gc.DrawRectangle(0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)
        
    def Line(self, x0, y0, x1, y1, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.StrokeLine(x0, y0, x1, y1)
        mdc.SelectObject(wx.NullBitmap)

    def Rectangle(self, x, y, w, h, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.DrawRectangle(x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)

    def Ellipse(self, x, y, w, h, color, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color, size))
        gc.DrawEllipse(x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)

    def Blit(self, layer, x=0, y=0, w=0, h=0):
        if w == 0:
            w = layer.width
        if h == 0:
            h = layer.height

        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)

    def Draw(self, layer, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, 0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)

    def Load(self, name):
        bitmap = wx.Bitmap()
        bitmap.LoadFile(name)

        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(bitmap, 0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)

class LayerManager:
    def __init__(self):
        self.layers = []
        self.currentLayer = -1
        self.width = 0
        self.height = 0
        self.surface = None
        self.compositeLayer = None
        
    def appendSelect(self, layer=None):
        if not layer:
            layer = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
            
        if self.currentLayer<0:
            self.currentLayer = 0
            
        self.layers.insert(self.currentLayer, layer)
    
    def select(self, layer):
        self.currentLayer = self.layers.index(layer)
    
    def selectIndex(self, index):
        self.currentLayer = index
    
    def selectedIndex(self):
        return self.currentLayer
        
    def reverseIndex(self):
        return (len(self.layers)-1)-self.currentLayer
        
    def current(self):
        return self.layers[self.currentLayer]
    
    def composite(self):
        if not self.compositeLayer:
            self.compositeLayer = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
        else:
            self.compositeLayer.Clear()
            
        for layer in reversed(self.layers):
            self.compositeLayer.Draw(layer)
        
        return self.compositeLayer
        
    def set(self, layer):
        if self.currentLayer>=0:
            self.layers[self.currentLayer] = layer
        else:
            self.appendSelect(layer)
        
    def remove(self, layer=None):
        if len(self.layers)>1:
            if layer:
                del self.layers[self.layers.index(layer)]
            else:
                del self.layers[self.currentLayer]
                
            if self.currentLayer>=len(self.layers):
                self.currentLayer = len(self.layers)-1
    
    