"""
layermanager.py
Bhupendra Aole
1/19/2020
"""

import wx
from math import sqrt
from random import randrange

COLOR_BLANK = wx.Colour(0,0,0,0)

class Layer(wx.Bitmap):
    layerCount = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = self.GetWidth()
        self.height = self.GetHeight()
        
        self.name = "Layer "+str(Layer.layerCount)
        Layer.layerCount += 1
        
        self.visible = True
        
    def Copy(self, name=None):
        layer = Layer(self.GetSubBitmap(wx.Rect(0, 0, self.width, self.height)))
        layer.name = name if name else self.name
        return layer
        
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
        del mdcs
        del mdcd
        
        return bitmap

    def Clear(self, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(COLOR_BLANK))

        # gc.DrawRectangle(0, 0, *gc.GetSize())
        # weird bug ^^^ can't correctly draw a big rectangle in one go
        w, h = self.width, self.height
        for x in range(0, w, 60):
            for y in range(0, h, 60):
                gc.DrawRectangle(x, y, min(w, 60), min(h, 60))
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        
    def GetPixel(self, x, y):
        mdc = wx.MemoryDC(self)
        col = mdc.GetPixel(x, y)
        del mdc
        
        return col

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
        del mdc
        
    def ErasePixel(self, x, y, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(COLOR_BLANK))
        gc.DrawRectangle(int(x-size/2+.5), int(y-size/2+.5), size, size)
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        
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
        del mdc

    # BUG?? FloodFill is painting with alpha=0
    def FloodFill(self, x, y, color, clip=None):
        mdc = wx.MemoryDC(self)
        gcdc = wx.GCDC(mdc)
        
        replace = mdc.GetPixel(x, y)
        #print(replace)
        gcdc.SetBrush(wx.Brush(color))
        gcdc.FloodFill(x, y, replace)
        
        '''
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
        '''
        #mdc.SelectObject(wx.NullBitmap)
        #del gcdc
        #del mdc
        
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
        del mdc

    def EraseLine(self, x0, y0, x1, y1, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(COLOR_BLANK, size))
        gc.StrokeLine(x0, y0, x1, y1)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

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
        del mdc

    def EraseRectangle(self, x, y, w, h, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(COLOR_BLANK, size))
        gc.DrawRectangle(x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

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
        del mdc

    def EraseEllipse(self, x, y, w, h, size=1, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(COLOR_BLANK, size))
        gc.DrawEllipse(x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

    def FillGradient(self, x0, y0, x1, y1, stops, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        brush = gc.CreateLinearGradientBrush(x0, y0, x1, y1, stops)
        gc.SetBrush(brush)
        gc.DrawRectangle(0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        
    def FillRGradient(self, x0, y0, x1, y1, stops, clip=None):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        r = sqrt((x1-x0)**2 + (y1-y0)**2)
        brush = gc.CreateRadialGradientBrush(x0, y0, x0, y0, r, stops)
        gc.SetBrush(brush)
        gc.DrawRectangle(0, 0, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        
    def Blit(self, layer, x=0, y=0, w=0, h=0):
        if w == 0:
            w = layer.width
        if h == 0:
            h = layer.height

        #print('blit:',self.name,x,y,self.width, self.height,'from',layer.name, w, h)
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, x, y, w, h)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

    def Draw(self, layer, clip=None, x=0, y=0):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.DrawBitmap(layer, x, y, self.width, self.height)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

    def PasteSource(self, layer, clip=None, width=None, height=None):
        if not width:
            width = self.width
        if not height:
            height = self.height
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        if clip and not clip.IsEmpty():
            gc.Clip(clip)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.DrawBitmap(layer, 0, 0, width, height)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

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
        del mdc

class LayerManager:
    def __init__(self, width=0, height=0):
        self.layers = []
        self.currentLayer = -1
        self.width = width
        self.height = height
        
        self.surface = None
        if width>0 and height>0:
            self.surface = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
            
        self.compositeLayer = None
        
    def __iter__(self):
        for layer in self.layers:
            yield layer
            
    def __len__(self):
        return len(self.layers)
        
    def __getitem__(self, index):
        return self.layers[index]
        
    def AppendSelect(self, layer=None):
        if not layer:
            layer = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
            
        if self.currentLayer<0:
            self.currentLayer = 0
            
        self.layers.insert(self.currentLayer, layer)
    
        return layer
        
    def BlitFromSurface(self, x=0, y=0):
        self.layers[self.currentLayer].Blit(self.surface, x, y)
        
    def BlitToSurface(self):
        self.surface.Blit(self.layers[self.currentLayer])
        
    def Clear(self):
        self.surface.Clear()
        
    def Composite(self, mx=0, my=0, drawCurrent=True):
        if not self.compositeLayer:
            self.compositeLayer = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
        else:
            self.compositeLayer.Clear()
        
        for layer in reversed(self.layers):
            if not layer.visible:
                continue
                
            if layer == self.layers[self.currentLayer]:
                if drawCurrent:
                    self.compositeLayer.Draw(layer)
                self.compositeLayer.Draw(self.surface, x=mx, y=my)
            else:
                self.compositeLayer.Draw(layer)
                
        return self.compositeLayer
        
    def Count(self):
        return len(self.layers)

    def Copy(self):
        mgr = LayerManager()
        mgr.Resize(self)
        return mgr
        
    def CreateDummy(width, height, numlayers):
        lm = LayerManager(width, height)
        for i in range(numlayers):
            if not i:
                lm.AppendSelect(Layer(wx.Bitmap.FromRGBA(width, height, 255, 255, 255, 255)))
            else:
                lm.AppendSelect()
                lm.Clear()
                lm.Line(randrange(width), randrange(height), randrange(width), randrange(height), 
                        wx.Colour(randrange(256), randrange(256), randrange(256)), 4)
                lm.BlitFromSurface()
                
        return lm
        
    def Crop(self, lm, rect):
        self.width  = rect.width
        self.height = rect.height
        for layer in reversed(lm.layers):
            l = self.appendSelect()
            l.Draw(layer.GetSubBitmap(rect))
        self.currentLayer = lm.currentLayer
        self.surface = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
        self.compositeLayer = None
        
    def Current(self):
        return self.layers[self.currentLayer]
    
    def Ellipse(self, x, y, w, h, color, size=1, clip=None):
        self.surface.Ellipse(x, y, w, h, color, size, clip)
        
    def EraseEllipse(self, x, y, w, h, size=1, clip=None):
        self.surface.EraseEllipse(x, y, w, h, size, clip)
        
    def EraseLine(self, x0, y0, x1, y1, size=1, clip=None):
        self.surface.EraseLine(x0, y0, x1, y1, size, clip)
        
    def ErasePixel(self, x, y, size=1, clip=None):
        self.surface.ErasePixel(x, y, size, clip)
        
    def EraseRectangle(self, x, y, w, h, size=1, clip=None):
        self.surface.EraseRectangle(x, y, w, h, size, clip)
        
    def FillGradient(self, x0, y0, x1, y1, stops=None, clip=None):
        if not stops:
            stops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        self.surface.FillGradient(x0, y0, x1, y1, stops, clip)
        
    def FillRGradient(self, x0, y0, x1, y1, stops=None, clip=None):
        if not stops:
            stops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        self.surface.FillRGradient(x0, y0, x1, y1, stops, clip)
        
    def GetVisible(self):
        return self.layers[self.currentLayer].visible
        
    def Line(self, x0, y0, x1, y1, color, size=1, clip=None):
        self.surface.Line(x0, y0, x1, y1, color, size, clip)
        
    def Rectangle(self, x, y, w, h, color, size=1, clip=None):
        self.surface.Rectangle(x, y, w, h, color, size, clip)
        
    def Remove(self, layer=None):
        if len(self.layers)>1:
            if not layer:
                layer = self.layers[self.currentLayer]
            del self.layers[self.layers.index(layer)]
                
            if self.currentLayer>=len(self.layers):
                self.currentLayer = len(self.layers)-1
        
        return layer
        
    def RemoveAll(self):
        self.surface = None
        self.compositeLayer = None
        
        while self.layers:
            del self.layers[0]
        self.currentLayer = -1
        
    def Resize(self, lm, width=None, height=None):
        self.RemoveAll()
        self.width  = width if width else lm.width
        self.height = height if height else lm.height
        for layer in reversed(lm.layers):
            l = self.AppendSelect()
            l.PasteSource(layer, width=layer.width, height=layer.height)
            l.name = layer.name
            
        self.currentLayer = lm.currentLayer
        self.surface = Layer(wx.Bitmap.FromRGBA(self.width, self.height, 0, 0, 0, 0))
        self.compositeLayer = None
        
    def ReverseIndex(self):
        return (len(self.layers)-1)-self.currentLayer
        
    def Select(self, layer):
        self.currentLayer = self.layers.index(layer)
    
    def SelectedIndex(self):
        return self.currentLayer
        
    def SelectIndex(self, index):
        self.currentLayer = index
    
    def Set(self, layer):
        if self.currentLayer>=0:
            self.layers[self.currentLayer] = layer
        else:
            self.appendSelect(layer)
        
    def SetPixel(self, x, y, color, size=1, clip=None):
        self.surface.SetPixel(x, y, color, size, clip)
        
    def SetVisible(self, v=True):
        self.layers[self.currentLayer].visible = v
        
    def SourceFromSurface(self):
        self.layers[self.currentLayer].PasteSource(self.surface)
        
    def SourceToSurface(self):
        self.surface.PasteSource(self.layers[self.currentLayer])
        
    def Spline(self, pts, color):
        mdc = wx.MemoryDC(self.surface)
        gcdc = wx.GCDC(mdc)
        gc = gcdc.GraphicsContext
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gcdc.SetPen(wx.Pen(color, 1))
        gcdc.DrawSpline(pts)
        del gcdc
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        
    def ToggleVisible(self):
        self.layers[self.currentLayer].visible = not self.layers[self.currentLayer].visible
        