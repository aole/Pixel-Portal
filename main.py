"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

from math import ceil

from shapely.geometry   import Polygon, MultiPolygon, LineString
from shapely.ops        import unary_union

import wx
import wx.lib.agw.genericmessagedialog as GMD
from wx.adv import BitmapComboBox
from wx.lib.agw.cubecolourdialog import CubeColourDialog

from PIL import Image, ImageDraw, ImageSequence

import numpy as np

from undomanager import *
from layermanager import *
from gradienteditor import *
from layercontrol import *
from animationcontrol import *
from document import *
from settings import *
from dialogs.dictionarydialog import *

PROGRAM_NAME = "Pixel Portal"
WINDOW_SIZE = (800, 700)

DEFAULT_DOC_SIZE = (80, 80)
DEFAULT_PIXEL_SIZE = 5

TOOLS = {"Pen":             (wx.CURSOR_PENCIL,      "toolpen.png"),
         "Select":          (wx.CURSOR_CROSS,       "toolselectrect.png"),
         "Line":            (wx.CURSOR_CROSS,       "toolline.png"),
         "Rectangle":       (wx.CURSOR_CROSS,       "toolrect.png"),
         "Ellipse":         (wx.CURSOR_CROSS,       "toolellipse.png"),
         "Move":            (wx.CURSOR_SIZING,      "toolmove.png"),
         "Bucket":          (wx.CURSOR_PAINT_BRUSH, "toolbucket.png"),
         "Picker":          (wx.CURSOR_RIGHT_ARROW, "toolpicker.png"),
         "Gradient":        (wx.CURSOR_CROSS,       "toolgradient.png"),
         "Radial Gradient": (wx.CURSOR_CROSS,       "toolrgradient.png"),
         "Helper":          (wx.CURSOR_CROSS,       "toolhelper.png")}

#Debug
RENDER_CURRENT_LAYER = True
RENDER_PREVIEW = True
RENDER_BRUSH_OUTLINE = True
PRINT_UNDO_REDO = True

app = None

def minmax(a, b):
    if b < a:
        return b, a
    else:
        return a, b

def nvl(v, nv):
    return v if v else nv
    
class Canvas(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)

        self.panx = 20
        self.pany = 20

        self.prevx, self.prevy = 0, 0
        self.origx, self.origy = 0, 0
        self.prevgx, self.prevgy = -1, -1
        self.linePoints = []
        self.smoothLine = False
        
        self.movex, self.movey = 0, 0
        self.selection = wx.Region()
        self.lastSelection = None
        
        self.mouseState = 0
        self.doubleClick = False
        
        self.current_tool = "Pen"
        self.original_tool = self.current_tool
        self.mirrorx = False
        self.mirrory = False
        self.gridVisible = True

        self.pixelSize = DEFAULT_PIXEL_SIZE

        self.penSize = 1
        self.penColor = wx.BLACK
        self.palette = None
        
        self.gradientStops = wx.GraphicsGradientStops(wx.BLACK, wx.WHITE)
        self.gradientStops.Add(wx.GraphicsGradientStop(wx.BLACK, 0))
        self.gradientStops.Add(wx.GraphicsGradientStop(wx.WHITE, 1))
        
        self.refAlpha = 0.3
        self.refScale = 1
        self.reference = None
        
        self.helper = None
        self.helperSegments = 1
        
        self.document = LayerManager()
        
        self.alphabg = wx.Bitmap("alphabg.png").ConvertToImage().AdjustChannels(1,1,1, .3).ConvertToBitmap()

        # UNDO / REDO
        self.history = UndoManager()
        self.beforeLayer = None
        self.noUndo = False

        self.SetCursor(wx.Cursor(TOOLS[self.current_tool][0]))

        self.listeners = []

    def AddLayer(self):
        index = self.document.currentLayer
        layer = self.document.AppendSelect().Copy()
        self.history.Store(AddLayerCommand(self.document, index, layer))
        
    def AdjustBrushSize(self, amount):
        self.penSize += amount
        if self.penSize<1:
            self.penSize = 1
            
        self.Refresh()
        
    def CenterCanvasInPanel(self, size):
        self.panx = int(size[0] / 2 - self.document.width * self.pixelSize / 2)
        self.pany = int(size[1] / 2 - self.document.height * self.pixelSize / 2)

        if self.panx < 30:
            self.panx = 30
        if self.pany < 30:
            self.pany = 30

    def ChangePenColor(self, color):
        self.penColor = color
        for l in self.listeners:
            l.PenColorChanged(color)

    def ClearCurrentLayer(self):
        self.beforeLayer = self.document.Current().Copy()

        self.document.Current().Clear(clip=self.selection)

        self.history.Store(PaintCommand(self.document, self.document.currentLayer, self.beforeLayer, self.document.Current().Copy()))
        self.beforeLayer = None
        self.Refresh()

    def Deselect(self):
        if self.selection and not self.selection.IsEmpty(): # Deselection
            self.lastSelection = self.selection
        self.selection = wx.Region()
        
    def DrawBrushOnCanvas(self, gc, px, py):
        gc.Clip(self.panx, self.pany, self.document.width*self.pixelSize, self.document.height*self.pixelSize)
        
        gc.SetPen(wx.ThePenList.FindOrCreatePen(self.penColor))
        gc.SetBrush(wx.NullBrush)
        x, y = int(px-self.penSize/2+.5), int(py-self.penSize/2+.5)
        sz = self.penSize*self.pixelSize
        gc.DrawRectangle(self.panx+x*self.pixelSize, self.pany+y*self.pixelSize, sz, sz)
        
        gc.ResetClip()
        
    def DrawEllipse(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            x = min(x0, x1)
            y = min(y0, y1)
            w = abs(x1 - x0)
            h = abs(y1 - y0)
            
            if center:
                xc = x0
                yc = y0
            if equal and w!=h:
                w = h = min(w,h)
                if x0>x1:
                    x = x0-w
                if y0>y1:
                    y = y0-w
                    
            if w==0 or h==0:
                if w==0 and h==0:
                    self.document.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
                else:
                    self.document.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            elif center:
                self.document.Ellipse(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
            else:
                self.document.Ellipse(x, y, w, h, color, size=self.penSize, clip=self.selection)
            
            if canmirrorx and self.mirrorx:
                self.DrawEllipse(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
            if canmirrory and self.mirrory:
                self.DrawEllipse(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def DrawGrid(self, gc):
        w, h = self.GetClientSize()

        # minor lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#55555555'))
        path = gc.CreatePath()
        for x in range(self.panx, min(self.panx + self.document.width * self.pixelSize + 1, w), self.pixelSize):
            path.MoveToPoint(x, self.pany)
            path.AddLineToPoint(x, min(self.pany + self.document.height * self.pixelSize, h))
        for y in range(self.pany, min(self.pany + self.document.height * self.pixelSize + 1, h), self.pixelSize):
            path.MoveToPoint(self.panx, y)
            path.AddLineToPoint(min(self.panx + self.document.width * self.pixelSize, w), y)
        gc.StrokePath(path)

        midpx = self.pixelSize * int(self.document.width / 2)
        midpy = self.pixelSize * int(self.document.height / 2)

        # major lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#22222255'))
        path = gc.CreatePath()
        if midpx:
            path.MoveToPoint(midpx+self.panx, self.pany)
            path.AddLineToPoint(midpx+self.panx, min(self.pany + self.document.height * self.pixelSize, h))
            if self.mirrorx:
                path.MoveToPoint(midpx+self.panx-self.pixelSize, self.pany)
                path.AddLineToPoint(midpx+self.panx-self.pixelSize, min(self.pany + self.document.height * self.pixelSize, h))
        if midpy:
            path.MoveToPoint(self.panx, midpy+self.pany)
            path.AddLineToPoint(min(self.panx + self.document.width * self.pixelSize, w), midpy+self.pany)
            if self.mirrory:
                path.MoveToPoint(self.panx, midpy+self.pany-self.pixelSize)
                path.AddLineToPoint(min(self.panx + self.document.width * self.pixelSize, w), midpy+self.pany-self.pixelSize)
        gc.StrokePath(path)

    def DrawLine(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            self.document.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            if canmirrorx and self.mirrorx:
                self.DrawLine(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True)
            if canmirrory and self.mirrory:
                self.DrawLine(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False)

    def DrawPixel(self, x, y, color, canmirrorx=True, canmirrory=True):
        self.document.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.DrawPixel(self.GetXMirror(x), y, color, False, True)
        if canmirrory and self.mirrory:
            self.DrawPixel(x, self.GetYMirror(y), color, False, False)

    def DrawRectangle(self, x0, y0, x1, y1, color, canmirrorx=True, canmirrory=True, equal=False, center=False):
        if x0==x1 and y0==y1:
            self.DrawPixel(x0, y0, color, canmirrorx, canmirrory)
        else:
            x = min(x0, x1)
            y = min(y0, y1)
            w = abs(x1 - x0)
            h = abs(y1 - y0)
            
            if center:
                xc = x0
                yc = y0
            if equal and w!=h:
                w = h = min(w,h)
                if x0>x1:
                    x = x0-w
                if y0>y1:
                    y = y0-w
                    
            if w==0 or h==0:
                if w==0 and h==0:
                    self.document.SetPixel(x, y, color, size=self.penSize, clip=self.selection)
                else:
                    self.document.Line(x0, y0, x1, y1, color, size=self.penSize, clip=self.selection)
            elif center:
                self.document.Rectangle(xc-w, yc-h, w*2, h*2, color, size=self.penSize, clip=self.selection)
            else:
                self.document.Rectangle(x, y, w, h, color, size=self.penSize, clip=self.selection)
            
            if canmirrorx and self.mirrorx:
                self.DrawRectangle(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, color, False, True, equal, center)
            if canmirrory and self.mirrory:
                self.DrawRectangle(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), color, False, False, equal, center)

    def DuplicateLayer(self):
        oldidx = self.document.currentLayer
        self.document.DuplicateAndSelectCurrent()
        self.history.Store(DuplicateLayerCommand(self.document, oldidx, self.document.currentLayer))
        
    def EraseEllipse(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True, equal=False, center=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        
        if center:
            xc = x0
            yc = y0
        if equal and w!=h:
            w = h = min(w,h)
            if x0>x1:
                x = x0-w
            if y0>y1:
                y = y0-w
                
        if w==0 or h==0:
            if w==0 and h==0:
                self.document.ErasePixel(x, y, size=self.penSize, clip=self.selection)
            else:
                self.document.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        elif center:
            self.document.EraseEllipse(xc-w, yc-h, w*2, h*2, size=self.penSize, clip=self.selection)
        else:
            self.document.EraseEllipse(x, y, w, h, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.EraseEllipse(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.EraseEllipse(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False, equal, center)

    def EraseLine(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True):
        self.document.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.EraseLine(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True)
        if canmirrory and self.mirrory:
            self.EraseLine(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False)

    def ErasePixel(self, x, y, canmirrorx=True, canmirrory=True):
        self.document.ErasePixel(x, y, size=self.penSize, clip=self.selection)
        if canmirrorx and self.mirrorx:
            self.ErasePixel(self.GetXMirror(x), y, False, True)
        if canmirrory and self.mirrory:
            self.ErasePixel(x, self.GetYMirror(y), False, False)

    def EraseRectangle(self, x0, y0, x1, y1, canmirrorx=True, canmirrory=True, equal=False, center=False):
        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        
        if center:
            xc = x0
            yc = y0
        if equal and w!=h:
            w = h = min(w,h)
            if x0>x1:
                x = x0-w
            if y0>y1:
                y = y0-w
                
        if w==0 or h==0:
            if w==0 and h==0:
                self.document.ErasePixel(x, y, size=self.penSize, clip=self.selection)
            else:
                self.document.EraseLine(x0, y0, x1, y1, size=self.penSize, clip=self.selection)
        elif center:
            self.document.EraseRectangle(xc-w, yc-h, w*2, h*2, size=self.penSize, clip=self.selection)
        else:
            self.document.EraseRectangle(x, y, w, h, size=self.penSize, clip=self.selection)
        
        if canmirrorx and self.mirrorx:
            self.EraseRectangle(self.GetXMirror(x0), y0, self.GetXMirror(x1), y1, False, True, equal, center)
        if canmirrory and self.mirrory:
            self.EraseRectangle(x0, self.GetYMirror(y0), x1, self.GetYMirror(y1), False, False, equal, center)

    def FillGradient(self, x0, y0, x1, y1):
        self.document.FillGradient(x0, y0, x1, y1, self.gradientStops, clip=self.selection)
        
    def FillRGradient(self, x0, y0, x1, y1):
        self.document.FillRGradient(x0, y0, x1, y1, self.gradientStops, clip=self.selection)
        
    def FloodFill(self, x, y, color, boundaryonly=False):
        w, h = self.document.width, self.document.height
        
        def bpos(xp, yp):
            return yp*w*4+xp*4
            
        def car(a, b):
            return a[0]==b[0] and a[1]==b[1] and a[2]==b[2] and a[3]==b[3]
            
        if x < 0 or y < 0 or x > w - 1 or y > h - 1:
            return
            
        selection = wx.Region(self.selection)
        if not selection.IsEmpty() and not selection.Contains(x, y):
            return

        if not selection or selection.IsEmpty():
            selection = wx.Region(0,0,w,h)
            
        buf = bytearray(w*h*4)
        self.document.surface.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
        i = bpos(x,y)
        replace = buf[i:i+4]
        
        rgba = color.Get()
        
        visited = set()
        boundary = set()
        queue = {(x, y)}
        while queue:
            # replace current pixel
            xy = queue.pop()
            x,y = xy
            i = bpos(x,y)
            
            # north
            isboundary = False
            d = bpos(x,y-1)
            if y > 0 and car(buf[d:d+4], replace) and selection.Contains(x, y-1):
                if (x,y-1) not in visited:
                    queue.add((x, y - 1))
            else:
                isboundary = True
            # east
            d = bpos(x+1,y)
            if x < w - 1 and car(buf[d:d+4], replace) and selection.Contains(x+1, y):
                if (x+1,y) not in visited:
                    queue.add((x + 1, y))
            else:
                isboundary = True
            # south
            d = bpos(x,y+1)
            if y < h - 1 and car(buf[d:d+4], replace) and selection.Contains(x, y+1):
                if (x,y+1) not in visited:
                    queue.add((x, y + 1))
            else:
                isboundary = True
            # west
            d = bpos(x-1, y)
            if x > 0 and car(buf[d:d+4], replace) and selection.Contains(x-1, y):
                if (x-1,y) not in visited:
                    queue.add((x - 1, y))
            else:
                isboundary = True
                
            # set this pixel
            visited.add(xy)
            if boundaryonly:
                if isboundary:
                    boundary.add((x,y))
            else:
                buf[i] = rgba[0]
                buf[i+1] = rgba[1]
                buf[i+2] = rgba[2]
                buf[i+3] = rgba[3]
                    
        if boundaryonly:
            for x,y in boundary:
                i = bpos(x,y)
                buf[i] = rgba[0]
                buf[i+1] = rgba[1]
                buf[i+2] = rgba[2]
                buf[i+3] = rgba[3]
                
        self.document.surface.CopyFromBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
    def GetGradientStops(self):
        return self.gradientStops
        
    def GetMirror(self, bitmap, horizontally=True):
        return bitmap.ConvertToImage().Mirror(horizontally).ConvertToBitmap()

    def GetPenColor(self):
        return self.penColor

    def GetPolyCoords(self, x, y, w, h):
        return (x,y), (x,y+h), (x+w, y+h), (x+w,y)
        
    def GetXMirror(self, x):
        w = int(self.document.width / 2)
        return ((x + 1 - w) * -1) + w - 1

    def GetYMirror(self, y):
        h = int(self.document.height / 2)
        return ((y + 1 - h) * -1) + h - 1

    def IsDirty(self):
        return self.history.IsDirty()

    def Load(self, pixel, filename):
        if filename[-4:]=="aole":
            self.document = Document.Load(filename)
            width, height = self.document.width, self.document.height
        elif filename[-3:] in ("png", "jpg", "jpeg"):
            image = wx.Image(filename)
            self.pixelSize = pixel
            width, height = int(image.GetWidth() / pixel), int(image.GetHeight() / pixel)

            self.New(pixel, width, height)

            self.document.Current().Load(filename)
        elif filename[-3:]=="tif" or filename[-4:]=="tiff":
            im = Image.open(filename)
            width, height = int(im.width/pixel), int(im.height/pixel)
            self.document.Init(width, height)
            for frame in ImageSequence.Iterator(im):
                bitmap = wx.Bitmap.FromBufferRGBA(im.width, im.height, frame.convert("RGBA").tobytes("raw"))
                self.document.InsertBottom(Layer(Layer(bitmap).Scaled(1/pixel)))
            self.document.currentLayer = 0
            
        self.history.ClearCommands()
        self.Deselect()

    def LoadRefImage(self, filename):
        image = Image.open(filename)
        image.putalpha(int(self.refAlpha*255))
        
        self.reference = Layer(wx.Bitmap.FromBufferRGBA(*image.size, image.tobytes()))

    def MergeDown(self):
        curidx = self.document.currentLayer
        if curidx<self.document.Count()-1 and self.document.Current().visible:
            self.history.Store(MergeDownLayerCommand(self.document, curidx, self.document.Current().Copy(), self.document[curidx+1].Copy()))
            self.document.MergeDown()
        
    def New(self, pixel, width, height):
        self.pixelSize = pixel

        # to ensure alpha
        bglayer = Layer.CreateLayer(width, height, wx.WHITE)
        bglayer.name = "background"
        
        self.document.width = width
        self.document.height = height
        self.document.RemoveAll()
        self.document.surface = Layer.CreateLayer(width, height)
        self.document.surface.name = 'Surface'
        self.document.AppendSelect(bglayer)
        self.document.AppendSelect()

        self.history.ClearCommands()
        self.Deselect()
        
    def OnCropToSelection(self, e):
        if not self.selection or self.selection.IsEmpty():
            return
        
        rect = self.selection.GetBox()
        old = self.document
        self.document = LayerManager()
        self.document.Crop(old, rect)
        
        self.history.ClearCommands()
        self.Deselect()

        for l in self.listeners:
            l.ImageSizeChanged(rect.width, rect.height)
            
        self.Refresh()
        
    def OnFlipH(self, e):
        before = self.document.Current().Copy()
        after = self.GetMirror(before)
        after.name = before.name+' mirror'

        self.history.Store(PaintCommand(self.document, self.document.currentLayer, before, after.Copy()))
        self.document.Current().Draw(after)

        self.Refresh()

    def OnFloodFill(self, e):
        x,y = wx.GetMousePosition()
        x,y = self.ScreenToClient(x,y)
        gx, gy = self.PixelAtPosition(x,y)
        if gx<0 or gx>self.document.width or gy<0 or gy>self.document.height:
            return False
            
        beforeLayer = self.document.Current().Copy()
        self.document.BlitToSurface()
        self.document.Current().Clear()
        self.FloodFill(gx, gy, self.penColor, boundaryonly=e.AltDown())
        self.document.BlitFromSurface()
        self.document.surface.Clear()
        
        self.history.Store(PaintCommand(self.document, self.document.currentLayer, beforeLayer, self.document.Current().Copy()))
        self.Refresh()
        return True
        
    def OnLeftDClick(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        if self.current_tool=="Select":
            self.SelectBoundary(gx, gy, e.ControlDown(), e.AltDown())
        
        self.doubleClick = True
        
    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 1
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = self.document.Current().Copy()

        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.document.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                if self.smoothLine:
                    self.linePoints.append((gx, gy))
                self.DrawPixel(gx, gy, self.penColor)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.document.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.DrawPixel(gx, gy, self.penColor)
        elif self.current_tool == "Move":
            self.document.surface.Draw(self.document.Current(), clip=self.selection)
            if not e.ControlDown():
                self.document.Current().Clear(clip=self.selection)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.document.Composite().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.document.BlitToSurface()
                self.document.Current().Clear()
                self.FloodFill(gx, gy, self.penColor, boundaryonly=e.AltDown())
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.document.Composite().GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Select":
            if not e.ControlDown() and not e.AltDown():
                self.Select(wx.Region())
        elif self.current_tool == "Helper":
            self.helper = [(self.origx-self.panx)/self.pixelSize,
                           (self.origy- self.pany)/self.pixelSize, 
                           (self.origx- self.panx)/self.pixelSize, 
                           (self.origy- self.pany)/self.pixelSize]
            
        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnLeftUp(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.mouseState = 0

        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool == "Pen":
            # smooth line
            if self.smoothLine:
                self.document.surface.Clear()
                line = LineString(self.linePoints)
                self.linePoints.clear()
                smoothline = line.simplify(1, True)
                self.Spline(smoothline.coords, self.penColor)
            self.document.BlitFromSurface()
            
        elif self.current_tool in ("Line", "Ellipse", "Rectangle", "Gradient", "Radial Gradient"):
            self.document.BlitFromSurface()
        elif self.current_tool == "Bucket":
            self.document.BlitFromSurface()
        elif self.current_tool == "Move":
            self.document.BlitFromSurface(self.movex, self.movey)
            if not self.selection.IsEmpty():
                ox, oy = self.PixelAtPosition(self.origx, self.origy)
                self.selection.Offset(self.movex, self.movey)
        elif self.current_tool == "Select" and not self.doubleClick:
            self.UpdateSelection(x, y, self.origx, self.origy, e.AltDown())
            self.doubleClick = False
        elif self.current_tool == "Helper":
            if self.helper[0]==self.helper[2] and self.helper[1]==self.helper[3]:
                self.helper = None
            self.noUndo = True
            
        self.movex, self.movey = 0, 0

        self.document.surface.Clear()

        # create an undo command
        if not self.noUndo:
            self.history.Store(PaintCommand(self.document, self.document.currentLayer, self.beforeLayer, self.document.Current().Copy()))
        self.beforeLayer = None

        self.noUndo = False
        self.current_tool = self.original_tool

        self.doubleClick = False
        self.Refresh()
        
        for l in self.listeners:
            l.RefreshLayers()

    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 3
        self.noUndo = False

    def OnMiddleUp(self, e):
        self.mouseState = 0
        self.noUndo = False

    def OnMirrorTR(self, e):
        before = self.document.Current().Copy()
        after = Layer(self.GetMirror(before))
        after.name = before.name+' mirror'
        after.Draw(before, wx.Region(0, 0, int(before.width / 2), before.height))

        self.history.Store(PaintCommand(self.document, self.document.currentLayer, before, after.Copy()))
        self.document.Set(after)

        self.Refresh()

    def OnMirrorTB(self, e):
        before = self.document.Current().Copy()
        after = Layer(self.GetMirror(before, False))
        after.name = before.name+' mirror'
        after.Draw(before, wx.Region(0, 0, before.width, int(before.height / 2)))

        self.history.Store(PaintCommand(self.document, self.document.currentLayer, before, after.Copy()))
        self.document.Set(after)

        self.Refresh()

    def OnMouseEnter(self, e):
        self.SetFocus()
        
    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.prevgx, self.prevgy = gx, gy

        # draw with 1st color
        if self.mouseState == 1:
            if self.current_tool == "Pen":
                if self.smoothLine:
                    self.linePoints.append((gx, gy)) # for smoothing later
                self.DrawLine(*self.PixelAtPosition(self.prevx, self.prevy), gx, gy, self.penColor)
            elif self.current_tool == "Line":
                self.document.surface.Clear()
                self.DrawLine(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Rectangle":
                self.document.surface.Clear()
                self.DrawRectangle(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor, equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.document.surface.Clear()
                self.DrawEllipse(*self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor,
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Move":
                self.movex, self.movey = int((x - self.origx)/ self.pixelSize), int((y - self.origy)/ self.pixelSize)
            elif self.current_tool == "Picker":
                color = self.document.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
            elif self.current_tool == "Gradient":
                self.document.surface.Clear()
                self.FillGradient(*self.PixelAtPosition(self.origx, self.origy), gx, gy)
            elif self.current_tool == "Radial Gradient":
                self.document.surface.Clear()
                self.FillRGradient(*self.PixelAtPosition(self.origx, self.origy), gx, gy)
            elif self.current_tool == "Helper":
                self.helper[2] = (x - self.panx)/self.pixelSize
                self.helper[3] = (y - self.pany)/self.pixelSize
        # draw with 2nd color
        elif self.mouseState == 2:
            if self.current_tool == "Pen":
                self.EraseLine(*self.PixelAtPosition(self.prevx, self.prevy), gx, gy)
            elif self.current_tool == "Line":
                self.document.BlitToSurface()
                self.EraseLine(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y))
            elif self.current_tool == "Rectangle":
                self.document.BlitToSurface()
                self.EraseRectangle(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Ellipse":
                self.document.BlitToSurface()
                self.EraseEllipse(*self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y),
                                 equal=e.ShiftDown(), center=e.ControlDown())
            elif self.current_tool == "Select":
                px, py = self.PixelAtPosition(self.prevx, self.prevy)
                if not self.selection.IsEmpty():
                    self.selection.Offset(gx - px, gy - py)
            elif self.current_tool == "Helper":
                self.helper[0] += (x - self.prevx)/self.pixelSize
                self.helper[1] += (y - self.prevy)/self.pixelSize
                self.helper[2] += (x - self.prevx)/self.pixelSize
                self.helper[3] += (y - self.prevy)/self.pixelSize

        elif self.mouseState == 3:
            self.panx += x - self.prevx
            self.pany += y - self.prevy

        self.prevx, self.prevy = x, y

        self.Refresh()

    def OnMouseWheel(self, e):
        amt = e.GetWheelRotation()
        if self.current_tool == "Helper":
            if amt > 0:
                self.helperSegments += 1
            else:
                self.helperSegments -= 1
                if self.helperSegments < 2:
                    self.helperSegments = 2
        else:
            if amt > 0:
                self.pixelSize += 1
            else:
                self.pixelSize -= 1
                if self.pixelSize < 1:
                    self.pixelSize = 1

        self.Refresh()

    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        alphadc = wx.MemoryDC(self.alphabg)
        
        skipCurrent = self.mouseState == 2 or (self.mouseState==1 and self.current_tool in ("Move"))
        composite = self.document.Composite(self.movex, self.movey,
                                          drawCurrent=not skipCurrent,
                                          drawSurface=self.mouseState != 0)
        compositedc = wx.MemoryDC(composite)
        
        lw, lh = self.document.width, self.document.height
        plw, plh = self.document.width*self.pixelSize, self.document.height*self.pixelSize
        
        # PAINT WHOLE CANVAS BACKGROUND
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.Clear()

        # PAINT RULERS --------------
        dc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
        dc.DrawRectangle(self.panx-10, 0, lw*self.pixelSize+20, 25)
        dc.DrawRectangle(0, self.pany-10, 25, lh*self.pixelSize+20)
        
        dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
        for rx in range(0, lw+1):
            if self.prevgx==rx and rx<lw:
                dc.SetBrush(wx.TheBrushList.FindOrCreateBrush("#CCCCCC"))
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
                dc.DrawRectangle(self.panx + rx * self.pixelSize, 0, 5, 5)
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
                dc.SetBrush(wx.NullBrush)
                
            rh = 10 if rx%5==0 else 5
            dc.DrawLine(self.panx + rx * self.pixelSize, 0, self.panx + rx * self.pixelSize, rh)
            if rx%5==0:
                rsz = int(dc.GetTextExtent(str(rx)).width/2)
                dc.DrawText(str(rx), self.panx + rx * self.pixelSize - rsz, rh)
                
        for ry in range(0, lh+1):
            if self.prevgy==ry and ry<lh:
                dc.SetBrush(wx.TheBrushList.FindOrCreateBrush("#CCCCCC"))
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE)))
                dc.DrawRectangle(0, self.pany + ry * self.pixelSize, 5, 5)
                dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK))
                dc.SetBrush(wx.NullBrush)
                
            rw = 10 if ry%5==0 else 5
            dc.DrawLine(0, self.pany + ry * self.pixelSize, rw, self.pany + ry * self.pixelSize)
            if ry%5==0:
                rsz = int(dc.GetTextExtent(str(ry)).height/2)
                dc.DrawText(str(ry), rw, self.pany + ry * self.pixelSize - rsz)
            
        # CLIP TO DOCUMENT
        #dc.SetClippingRegion(self.panx, self.pany, self.document.width * self.pixelSize,
        #                     self.document.height * self.pixelSize)

        # ALPHA BACKGROUND
        abgw, abgh = self.alphabg.GetWidth(), self.alphabg.GetHeight()
        dc.StretchBlit(self.panx, self.pany,
                       plw, plh,
                       alphadc,
                       0, 0,
                       abgw, abgh)
        
        # RENDER LAYERS
        if RENDER_CURRENT_LAYER:
            dc.StretchBlit(self.panx, self.pany,
                           self.document.width * self.pixelSize, self.document.height * self.pixelSize,
                           compositedc,
                           0, 0,
                           lw, lh)

        gc = wx.GraphicsContext.Create(dc)

        # BRUSH PREVIEW
        if RENDER_BRUSH_OUTLINE and self.mouseState != 1 and self.current_tool in ["Pen", "Line", "Rectangle", "Ellipse"]:
            self.DrawBrushOnCanvas(gc, self.prevgx, self.prevgy)
            
        # REFERENCE
        if self.reference:
            w, h = int(self.reference.width*self.refScale), int(self.reference.height*self.refScale)
            ar = w/h
            cw, ch = self.document.width * self.pixelSize, self.document.height * self.pixelSize
            gc.DrawBitmap(self.reference, self.panx, self.pany, min(cw, ch*ar), min(cw/ar,ch))
            
        # GRID
        if self.gridVisible and self.pixelSize > 2:
            self.DrawGrid(gc)

        # DOCUMENT BORDER
        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW), 2))
        gc.StrokeLine(self.panx, self.pany, self.panx + plw, self.pany)
        gc.StrokeLine(self.panx, self.pany, self.panx, self.pany + plh)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_ACTIVEBORDER), 2))
        gc.StrokeLine(self.panx, self.pany + plh, self.panx + plw, self.pany + plh)
        gc.StrokeLine(self.panx + plw, self.pany, self.panx + plw, self.pany + plh)
        
        # SELECTION
        display_selection_rect = True
        if self.mouseState == 1 and self.current_tool in ("Move"):
            display_selection_rect = False
        
        # XOR ADD CLEAR not supported on windows
        # print(gc.SetCompositionMode(wx.COMPOSITION_CLEAR))
        gc.SetBrush(wx.NullBrush)
        if self.mouseState == 1 and self.current_tool == "Select":
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22443388", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawRectangle(min(self.prevx, self.origx), min(self.prevy, self.origy), abs(self.prevx - self.origx),
                             abs(self.prevy - self.origy))
                             
        # TODO: Performance, precalculate shapely MultiPolygon union
        if self.selection and not self.selection.IsEmpty() and display_selection_rect:
            spoly = []
            for r in self.selection:
                poly = Polygon([*self.GetPolyCoords(r.x * self.pixelSize + self.panx,
                                 r.y * self.pixelSize + self.pany,
                                 r.width * self.pixelSize,
                                 r.height * self.pixelSize)])
                spoly.append(poly)
            spoly = unary_union(spoly)
            if not isinstance(spoly, MultiPolygon):
                spoly = MultiPolygon([spoly])
            # can have multiple disjoint polygons boundaries
            expath = gc.CreatePath()
            inpath = gc.CreatePath()
            for poly in spoly:
                moveto = True
                for x,y in poly.exterior.coords:
                    if moveto:
                        expath.MoveToPoint(x,y)
                        moveto = False
                    else:
                        expath.AddLineToPoint(x,y)
                expath.CloseSubpath()
                
                # each exterior boundary can have multiple interior holes
                for interior in poly.interiors:
                    moveto = True
                    for x,y in interior.coords:
                        if moveto:
                            inpath.MoveToPoint(x,y)
                            moveto = False
                        else:
                            inpath.AddLineToPoint(x,y)
                    inpath.CloseSubpath()
                    
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#66887788", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawPath(inpath)
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#22443388", 2, wx.PENSTYLE_LONG_DASH))
            gc.DrawPath(expath)
        
        # HELPER
        if self.helper:
            gc.SetBrush(wx.NullBrush)
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#111111AA", 1))
            x0, y0, x1, y1 = self.helper
            dx = (x1-x0)/self.helperSegments
            dy = (y1-y0)/self.helperSegments
            #d = numpy.linalg.norm((dx, dy))/self.helperSegments
            sx = x0
            sy = y0
            for i in range(self.helperSegments+1):
                gc.DrawEllipse((sx-1)*self.pixelSize+self.panx, (sy-1)*self.pixelSize+self.pany, 2*self.pixelSize, 2*self.pixelSize)
                sx += dx
                sy += dy
            gc.SetPen(wx.ThePenList.FindOrCreatePen("#111111AA", 3, wx.PENSTYLE_SHORT_DASH))
            gc.StrokeLine(x0*self.pixelSize+self.panx,
                          y0*self.pixelSize+self.pany,
                          x1*self.pixelSize+self.panx,
                          y1*self.pixelSize+self.pany)
        # PREVIEW
        if RENDER_PREVIEW:
            dc.DestroyClippingRegion()
            w, h = e.GetEventObject().GetSize()
            # BUG? dc.GetSize provide does not reduce in size if the window is expanded and them reduced.
            dc.StretchBlit(w-lw, 0,
                           lw, lh,
                           alphadc,
                           0, 0,
                           abgw, abgh)
            dc.StretchBlit(w-lw, 0,
                           lw, lh,
                           compositedc,
                           0, 0,
                           lw, lh)
        # PREVIEW BORDER
        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_ACTIVEBORDER), 2))
        gc.StrokeLine(w-lw, lh, w-lw + lw, lh)
        gc.StrokeLine(w-lw + lw, 0, w-lw + lw, lh)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW), 2))
        gc.StrokeLine(w-lw, 0, w-lw + lw, 0)
        gc.StrokeLine(w-lw, 0, w-lw, lh)
        
        alphadc.SelectObject(wx.NullBitmap)
        del alphadc
        
    def OnRightDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)
        self.mouseState = 2

        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = self.document.Current().Copy()

        # put a dot
        if self.current_tool == "Pen":
            if e.AltDown():
                self.noUndo = True
                color = self.document.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.document.BlitToSurface()
                self.ErasePixel(gx, gy)
        elif self.current_tool in ["Line", "Ellipse", "Rectangle"]:
            if e.AltDown():
                self.noUndo = True
                color = self.document.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.document.BlitToSurface()
                self.ErasePixel(gx, gy)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.document.Current().GetPixel(gx, gy)
            self.ChangePenColor(color)
        elif self.current_tool == "Bucket":
            if e.AltDown():
                self.noUndo = True
                color = self.document.Current().GetPixel(gx, gy)
                self.ChangePenColor(color)
                self.current_tool = "Picker"
            else:
                self.document.BlitToSurface()
                self.document.Current().Clear()
                self.FloodFill(gx, gy, wx.Colour(0,0,0,0))
        elif self.current_tool == "Select":
            self.noUndo = True
            if not self.selection.Contains(gx, gy):
                self.Select(wx.Region())

        if not self.HasCapture():
            self.CaptureMouse()

        self.Refresh()

    def OnRightUp(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        self.mouseState = 0

        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()

        # transfer from drawing layer to current_layer
        if self.current_tool in ("Pen", "Line", "Rectangle", "Ellipse", "Bucket"):
            self.document.SourceFromSurface()

        self.movex, self.movey = 0, 0

        self.document.surface.Clear()

        # create an undo command
        if not self.noUndo:
            self.history.Store(PaintCommand(self.document, self.document.currentLayer, self.beforeLayer, self.document.Current().Copy()))
            self.noUndo = True
            
        self.current_tool = self.original_tool
        self.beforeLayer = None
        self.Refresh()
        
        for l in self.listeners:
            l.RefreshLayers()

    def PixelAtPosition(self, x, y, func=int):
        return (func((x - self.panx) / self.pixelSize),
                func((y - self.pany) / self.pixelSize))

    def RearrangeLayer(self, layer, position):
        idx = self.document.GetIndex(layer)
        if idx!=position:
            if self.document.RearrangeIndex(idx, position):
                self.history.Store(RearrangeLayerCommand(self.document, idx, position))
            
    def Redo(self):
        self.history.Redo()
        self.Refresh()
        for l in self.listeners:
            l.Redid()
            
    def RemoveLayer(self):
        index = self.document.currentLayer
        layer = self.document.Remove().Copy()
        self.history.Store(RemoveLayerCommand(self.document, index, layer))
        
    def RemoveRefImage(self, e):
        self.reference = None
        self.Refresh()

    def Reselect(self):
        if not self.selection or self.selection.IsEmpty():
            self.selection = self.lastSelection
            self.lastSelection = None
            
    def Rotate90(self, e, clockwise=True):
        before = self.document.Current().Copy()
        image = before.ConvertToImage()
        image = image.Rotate90(clockwise)
        after = image.ConvertToBitmap()

        self.history.Store(PaintCommand(self.document, self.document.currentLayer, before, after.Copy()))
        self.document.Current().Draw(after)

        self.Refresh()

    def Resize(self, width, height):
        if width == self.document.width and height == self.document.height:
            return
        old = self.document.Copy()
        #self.document = LayerManager()
        self.document.Resize(old, width, height)
        self.history.Store(ResizeCommand(self.document, old, self.document.Copy()))
        
        self.Refresh()

    def Save(self, filename):
        if filename[-4:]=="aole":
            self.document.Save(filename)
        elif filename[-3:]=="png":
            self.document.Composite().Scaled(self.pixelSize).SaveFile(filename, wx.BITMAP_TYPE_PNG)
        elif filename[-3:]=="tif":
            tifimgs = []
            w,h = self.document.width*self.pixelSize, self.document.height*self.pixelSize
            for layer in self.document:
                buf = np.zeros(w*h*4)
                layer.Scaled(self.pixelSize).CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
                tifimg = Image.new('RGBA', (w,h))
                tifimg.frombytes(buf)
                tifimgs.append(tifimg)
            tifimgs[0].save(filename, compression="tiff_deflate", save_all=True,
               append_images=tifimgs[1:])
                
        self.history.MarkAsSaved()

    def SaveGif(self, filename):
        images = []
        wxImage = self.history.GetCommands()[0].before.Scaled(self.pixelSize).ConvertToImage()
        pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
        pilImage.frombytes(array(wxImage.GetDataBuffer()))
        images.append(pilImage)

        for cmd in self.history.GetCommands():
            wxImage = cmd.after.Scaled(self.pixelSize).ConvertToImage()
            pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
            pilImage.frombytes(array(wxImage.GetDataBuffer()))
            images.append(pilImage)
        images[0].save(filename, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)

    def Select(self, region=None):
        self.lastSelection = None
        if not region: # Select All
            self.selection = wx.Region(0,0,self.document.width, self.document.height)
        else:
            if self.selection and not self.selection.IsEmpty(): # Deselection
                self.lastSelection = self.selection
            self.selection = region
            
    def SelectBoundary(self, x, y, add=False, sub=False):
        layer = self.document.Current()
        w, h = layer.width, layer.height
        
        def bpos(xp, yp):
            return yp*w*4+xp*4
            
        def car(a, b):
            return a[0]==b[0] and a[1]==b[1] and a[2]==b[2] and a[3]==b[3]
            
        buf = bytearray(w*h*4)
        layer.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        
        i = bpos(x,y)
        color = buf[i:i+4]
        
        queue = {(x, y)}
        col = set()
        selection = wx.Region()
        
        while queue:
            x, y = queue.pop()
            col.add((x,y))
            selection.Union(x,y, 1,1)
            # north
            d = bpos(x,y-1)
            if y > 0 and car(buf[d:d+4], color) and (x,y-1) not in col:
                queue.add((x, y - 1))
            # east
            d = bpos(x+1,y)
            if x < w - 1 and car(buf[d:d+4], color) and (x+1,y) not in col:
                queue.add((x + 1, y))
            # south
            d = bpos(x,y+1)
            if y < h - 1 and car(buf[d:d+4], color) and (x,y+1) not in col:
                queue.add((x, y + 1))
            # west
            d = bpos(x-1,y)
            if x > 0 and car(buf[d:d+4], color) and (x-1,y) not in col:
                queue.add((x - 1, y))
                    
        if add:
            self.selection.Union(selection)
        elif sub:
            self.selection.Subtract(selection)
        else:
            self.selection = selection
        
    def SelectInvert(self):
        s = wx.Region(0, 0, self.document.width, self.document.height)
        s.Subtract(self.selection)
        self.selection = s
        
    def SetGradientStops(self, stops):
        self.gradientStops = stops
        
    def SetPenColor(self, color):
        self.penColor = color

    def SetTool(self, tool):
        self.current_tool = tool
        self.original_tool = tool
        self.SetCursor(wx.Cursor(TOOLS[tool][0]))

    def Spline(self, pts, color, canmirrorx=True, canmirrory=True):
        self.document.Spline(pts, color, size=self.penSize)
        if canmirrorx and self.mirrorx:
            mpts = [(self.GetXMirror(x), y) for x,y in pts]
            self.Spline(mpts, color, False, True)
        if canmirrory and self.mirrory:
            mpts = [(x, self.GetYMirror(y)) for x,y in pts]
            self.Spline(mpts, color, False, False)

    def Undo(self):
        self.history.Undo()
        self.Refresh()
        for l in self.listeners:
            l.Undid()
            
    def UpdateSelection(self, x0, y0, x1, y1, sub=False):
        minx, maxx = minmax(x0, x1)
        miny, maxy = minmax(y0, y1)
        minx, miny = self.PixelAtPosition(minx, miny)
        maxx, maxy = self.PixelAtPosition(maxx, maxy, ceil)
        if sub:
            self.selection.Subtract(wx.Rect(minx, miny, maxx - minx, maxy - miny))
        else:
            self.selection.Union(minx, miny, maxx - minx, maxy - miny)
            
        self.selection.Intersect(0, 0, self.document.width, self.document.height)
        
class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, size=WINDOW_SIZE)

        self.SetIcon(wx.Icon('icons/application.png'))
        self.FirstTimeResize = True
        self.saveFile = None
        
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        self.canvas = Canvas(self)
        self.canvas.listeners.append(self)

        # MENU
        self.menuid = 20001

        mbar = wx.MenuBar()

        mfile = wx.Menu()
        mbar.Append(mfile, "&File")
        
        self.AddMenuItem(mfile, "New\tCtrl+N", self.OnNew)
        self.AddMenuItem(mfile, "Open\tCtrl+O", self.OnOpen)
        self.AddMenuItem(mfile, "Save\tCtrl+S", self.OnSave)
        self.AddMenuItem(mfile, "Save As\tCtrl+Alt+S", self.OnSaveAs)
        self.AddMenuItem(mfile, "Export Animation\tCtrl+E", self.OnExportAnimation)
        self.AddMenuItem(mfile, "Export History as Animation", self.OnExportHistory)
        mfile.AppendSeparator()
        self.AddMenuItem(mfile, "Exit\tAlt+F4", self.OnClose)
        
        medit = wx.Menu()
        mbar.Append(medit, "&Edit")
        self.AddMenuItem(medit, "Flip Horizontal", self.canvas.OnFlipH)
        self.AddMenuItem(medit, "Mirror to Right", self.canvas.OnMirrorTR)
        self.AddMenuItem(medit, "Mirror Down", self.canvas.OnMirrorTB)
        self.AddMenuItem(medit, "Reference Image ...", self.OnRefImage)
        self.AddMenuItem(medit, "Remove Reference Image", self.canvas.RemoveRefImage)
        self.AddMenuItem(medit, "Rotate 90 CW", self.canvas.Rotate90)
        self.AddMenuItem(medit, "Crop to Selection", self.canvas.OnCropToSelection)
        medit.AppendSeparator()
        self.AddMenuItem(medit, "Settings ...", self.OnSettings)
        
        mselect = wx.Menu()
        mbar.Append(mselect, "&Selection")
        self.AddMenuItem(mselect, "Select &All\tCtrl+A", self.OnSelectAll)
        self.AddMenuItem(mselect, "&Deselect\tCtrl+D", self.OnDeselect)
        self.AddMenuItem(mselect, "&Reselect\tCtrl+Shift+D", self.OnReselect)
        self.AddMenuItem(mselect, "&Invert Selection\tCtrl+Shift+I", self.OnSelectInvert)

        menu = wx.Menu()
        mbar.Append(menu, "&Layer")
        self.AddMenuItem(menu, "&Add Layer\tCtrl+Shift+N", self.OnAddLayer)
        self.AddMenuItem(menu, "&Duplicate Layer\tCtrl+J", self.OnDuplicateLayer)
        self.AddMenuItem(menu, "&Remove Layer", self.OnRemoveLayer)
        self.AddMenuItem(menu, "&Merge Down\tCtrl+E", self.OnMergeDown)
        menu.AppendSeparator()
        self.AddMenuItem(menu, "&Clear\tDelete", self.OnClear)
        
        menu = wx.Menu()
        mbar.Append(menu, "&Help")
        self.AddMenuItem(menu, "&About", self.OnAbout)
        
        self.SetMenuBar(mbar)

        # TOOLBAR
        self.toolbar = tb = self.CreateToolBar()
        tb.SetToolBitmapSize((32, 32))
        
        self.AddToolButton(tb, 'Clear', self.OnClear, icon=wx.Bitmap("icons/clear.png"))
        self.AddToolButton(tb, 'Resize', self.OnDocResize, icon=wx.Bitmap("icons/resize.png"))

        self.AddToolButton(tb, 'New', self.OnNew, icon=wx.Bitmap("icons/new.png"))
        self.AddToolButton(tb, 'Load', self.OnOpen, icon=wx.Bitmap("icons/load.png"))
        self.AddToolButton(tb, 'Save', self.OnSave, icon=wx.Bitmap("icons/save.png"))
        self.AddToolButton(tb, 'Gif', self.OnSaveGif, icon=wx.Bitmap("icons/gif.png"))
        tb.AddSeparator()
        
        self.colorbtn = self.AddToolButton(tb, 'Foreground Color', self.OnColor, icon=wx.Bitmap("icons/forecolor.png"))
        
        # Tool combo box
        bcb = BitmapComboBox(tb, style=wx.CB_READONLY)
        for k, v in TOOLS.items():
            bcb.Append(k, wx.Bitmap("icons/"+v[1]))
        self.Bind(wx.EVT_COMBOBOX, self.OnTool, id=bcb.GetId())
        bcb.SetSelection(0)
        tb.AddControl(bcb)
        
        # Gradient editor
        gbtn = wx.BitmapButton(tb, bitmap=wx.Bitmap("icons/gradient.png"))
        self.Bind(wx.EVT_BUTTON, self.OnGradient, id=gbtn.GetId())
        tb.AddControl(gbtn)
        
        self.AddToggleButton(tb, 'Grid', self.OnToggleGrid, icon=wx.Bitmap("icons/grid.png"), default=True)
        self.AddToggleButton(tb, 'Mirror X', self.OnMirrorX, icon=wx.Bitmap("icons/mirrorx.png"))
        self.AddToggleButton(tb, 'Mirror Y', self.OnMirrorY, icon=wx.Bitmap("icons/mirrory.png"))
        self.AddToggleButton(tb, 'Smooth Line', self.OnSmoothLine, icon=wx.Bitmap("icons/smooth.png"))
        self.AddToolButton(tb, 'Center', self.OnCenter, icon=wx.Bitmap("icons/center.png"))
        
        tb.Realize()

        bstop = wx.BoxSizer(wx.VERTICAL)
        # add CANVAS
        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.canvas, 2, wx.EXPAND | wx.ALL, 2)
        
        # RIGHT PANEL
        layerPanel = wx.Panel(self, size=(200,-1))
        bs.Add(layerPanel, 0, wx.EXPAND|wx.ALL, 2)
        bstop.Add(bs, 1, wx.EXPAND|wx.ALL, 2)
        
        # ANIMATION CONTROL
        self.animControl = AnimationControl(self, self.canvas.document)
        self.animControl.Bind(EVT_VISIBILITY_CHANGED_EVENT, self.OnLayerVisibilityFromKey)
        self.animControl.Bind(EVT_KEY_INSERT_EVENT, self.OnAnimationKeyInsert)
        bstop.Add(self.animControl, 0, wx.EXPAND|wx.ALL, 2)
        
        # LAYERS PANEL
        bsp = wx.BoxSizer(wx.VERTICAL)
        self.lyrctrl = LayerControl(layerPanel)
        self.lyrctrl.UpdateLayers(self.canvas.document)
        self.lyrctrl.Bind(EVT_LAYER_CLICKED_EVENT, self.OnLayerClicked)
        self.lyrctrl.Bind(EVT_LAYER_VISIBILITY_EVENT, self.OnLayerVisibility)
        self.lyrctrl.Bind(EVT_LAYER_ALPHA_EVENT, self.OnLayerAlphaChange)
        self.lyrctrl.Bind(EVT_LAYER_DROP_EVENT, self.OnLayerDrop)
        bsp.Add(self.lyrctrl, 1, wx.EXPAND | wx.ALL, 3)
        
        # LAYER CONTROLS
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        conpanel = wx.Panel(layerPanel)
        but = wx.BitmapButton(conpanel, bitmap=wx.Bitmap('icons/layernew.png'))
        but.SetToolTip('Add new layer')
        self.Bind(wx.EVT_BUTTON, self.OnAddLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)
        
        sizer.AddSpacer(10)
        but = wx.BitmapButton(conpanel, bitmap=wx.Bitmap('icons/layerdelete.png'))
        but.SetToolTip('Delete layer')
        self.Bind(wx.EVT_BUTTON, self.OnRemoveLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)
        
        sizer.AddSpacer(10)
        but = wx.BitmapButton(conpanel, bitmap=wx.Bitmap('icons/layerduplicate.png'))
        but.SetToolTip('Duplicate layer')
        self.Bind(wx.EVT_BUTTON, self.OnDuplicateLayer, id=but.GetId())
        sizer.Add(but, 0, 0, 1)
        
        sizer.AddSpacer(10)
        but = wx.BitmapButton(conpanel, bitmap=wx.Bitmap('icons/layermerge.png'))
        but.SetToolTip('Merge down')
        self.Bind(wx.EVT_BUTTON, self.OnMergeDown, id=but.GetId())
        sizer.Add(but, 0, 0, 1)
        sizer.AddSpacer(10)
        conpanel.SetSizer(sizer)
        bsp.Add(conpanel, 0, wx.EXPAND | wx.ALL, 2)
        
        self.OnNew(None, *DEFAULT_DOC_SIZE, False)
        
        layerPanel.SetSizer(bsp)
        layerPanel.FitInside()
        self.SetSizer(bstop)
        self.UpdateTitle()

    def AddMenuItem(self, menu, name, func):
        menu.Append(self.menuid, name)
        menu.Bind(wx.EVT_MENU, func, id=self.menuid)
        self.menuid += 1

    def AddToggleButton(self, tb, label, function, icon, default=False):
        btn = tb.AddCheckTool(wx.ID_ANY, label, icon, shortHelp=label)
        tb.ToggleTool(btn.GetId(), default)
        self.Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn
        
    def AddToolButton(self, tb, label, function, icon):
        btn = tb.AddTool(wx.ID_ANY, label, icon, shortHelp=label)
        self.Bind(wx.EVT_TOOL, function, id=btn.GetId())
        return btn
        
    def AddToolControl(self, tb, control):
        control.SetSize(wx.DefaultCoord, wx.DefaultCoord, 30, wx.DefaultCoord)
        tb.AddControl(control)

    def CheckDirty(self):
        if self.canvas.IsDirty():
            diag = wx.GenericMessageDialog(self, 'Save Changes?', style=wx.YES_NO | wx.CANCEL)
            ret = diag.ShowModal()
            if ret == wx.ID_YES:
                self.OnSave(None)
                return True
            elif ret == wx.ID_CANCEL:
                return False

        return True

    def OnAbout(self, e):
        msg = 'Pixel Portal\n' \
              'Version 1.0\n' \
              'Bhupendra Aole\n' \
              'https://github.com/aole/Pixel-Portal'
        dlg = GMD.GenericMessageDialog(self, msg, "About Pixel Portal",
                               agwStyle=wx.ICON_INFORMATION | wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
    def OnAddLayer(self, e):
        self.canvas.AddLayer()
        self.canvas.Refresh()
        self.RefreshLayers()
    
    def OnAnimationKeyInsert(self, e):
        print(e)
        self.canvas.document.Current().visible = False
        self.canvas.document.DuplicateAndSelect()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnCenter(self, e):
        self.canvas.CenterCanvasInPanel(self.canvas.Size)
        self.canvas.Refresh()

    def OnClear(self, e):
        self.canvas.ClearCurrentLayer()
        self.RefreshLayers()

    def OnClose(self, e):
        if not self.CheckDirty():
            return
            
        self.Destroy()
        
    def OnColor(self, e):
        data = wx.ColourData()
        data.SetColour(self.canvas.GetPenColor())
        dlg = CubeColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            self.canvas.SetPenColor(color)
            
            bitmap = self.colorbtn.GetBitmap()
            mdc = wx.MemoryDC(bitmap)
            
            clip = wx.Region(0,0,32,32)
            clip.Subtract(wx.Rect(9, 9, 14, 14))
            mdc.SetDeviceClippingRegion(clip)
            
            mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
            mdc.SetPen(wx.NullPen)
            mdc.DrawRectangle(0,0,32,32)
            
            mdc.SelectObject(wx.NullBitmap)
            del mdc
            
            self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)
        
    def OnDeselect(self, e):
        self.canvas.Select(wx.Region())
        self.Refresh()
        
    def OnDocResize(self, e):
        dlg = ResizeDialog(self, self.canvas.document.Composite(), self.canvas.pixelSize)
        if dlg.ShowModal()==wx.ID_OK:
            width = dlg.GetWidth()
            height = dlg.GetHeight()
            self.canvas.Resize(width, height)

    def OnDuplicateLayer(self, e):
        self.canvas.DuplicateLayer()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnExportAnimation(self, e):
        filename = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if filename:
            frames = self.animControl.GetAnimationFrames()
            if frames:
                fps = self.animControl.GetFPS()
                images = []
                for frame in frames:
                    wxImage = frame.Scaled(self.GetPixelSize()).ConvertToImage()
                    pilImage = Image.new('RGB', (wxImage.GetWidth(), wxImage.GetHeight()))
                    pilImage.frombytes(np.array(wxImage.GetDataBuffer()))
                    images.append(pilImage)
                images[0].save(filename, save_all=True, append_images=images[1:], optimize=False, duration=1000/fps, loop=0)
            
    def OnExportHistory(self, e):
        print('OnExportHistory')
        
    def OnGradient(self, e):
        dlg = GradientEditor(self, self.canvas.GetGradientStops())
        if dlg.ShowModal() == wx.ID_OK:
            stops = dlg.GetStops()
            self.canvas.SetGradientStops(stops)
            
            bitmap = e.GetEventObject().GetBitmap()
            mdc = wx.MemoryDC(bitmap)
            gc = wx.GraphicsContext.Create(mdc)
            
            clip = wx.Region(2,2,60,28)
            mdc.SetDeviceClippingRegion(clip)
            
            brush = gc.CreateLinearGradientBrush(0, 0, 64, 0, stops)
            gc.SetBrush(brush)
            gc.SetPen(wx.NullPen)
            gc.DrawRectangle(0,0,64,32)
            
            mdc.SelectObject(wx.NullBitmap)
            del mdc
            
            e.GetEventObject().SetBitmap(bitmap)
        dlg.Destroy()
        
    def OnKeyDown(self, e):
        keycode = e.GetUnicodeKey()

        if keycode == ord('Z'):
            if e.ControlDown():
                if e.ShiftDown():
                    self.canvas.Redo()
                else:
                    self.canvas.Undo()
            else:
                # skip for other controls (eg renaming layer)
                e.Skip()
        elif keycode == ord('['):
            self.canvas.AdjustBrushSize(-1)
        elif keycode == ord(']'):
            self.canvas.AdjustBrushSize(1)
        elif keycode == ord('F'):
            if not self.canvas.OnFloodFill(e):
                e.Skip()
        else:
            e.Skip()

    def OnLayerAlphaChange(self, e):
        self.canvas.document.SetAlpha(e.alpha)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnLayerClicked(self, e):
        self.canvas.document.SelectIndex(e.index)
        self.RefreshLayers()
        
    def OnLayerDrop(self, e):
        self.canvas.RearrangeLayer(e.layer, e.position)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnLayerVisibility(self, e):
        self.canvas.document.ToggleVisible(e.index)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnLayerVisibilityFromKey(self, e):
        self.canvas.document.SetVisibleExclusive(e.key)
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnMergeDown(self, e):
        self.canvas.MergeDown()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnMirrorX(self, e):
        self.canvas.mirrorx = e.IsChecked()
        self.canvas.Refresh()

    def OnMirrorY(self, e):
        self.canvas.mirrory = e.IsChecked()
        self.canvas.Refresh()

    def OnNew(self, e, width=None, height=None, showDialog=True):
        if not self.CheckDirty():
            return

        self.saveFile = None
        if showDialog:
            dlg = DictionaryDialog(self, {'Width':nvl(width, 80), 'Height':nvl(height, 80)})
            if dlg.ShowModal() == wx.ID_OK:
                width = dlg.Get('Width')
                height = dlg.Get('Height')
            else:
                return
                
        if width and height:
            self.canvas.New(5, width, height)
            self.canvas.Refresh()
            self.RefreshLayers()
        
    def OnOpen(self, e):
        if not self.CheckDirty():
            return

        with wx.FileDialog(self, "Open Image file",
                           wildcard=FILE_DIALOG_FILTERS,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
                
            self.saveFile = fd.GetPath()
            ps = 1
            if self.saveFile[-5:]!='.aole': # not native format as we already know the pixel size
                cpd = ChangePixelDialog(self, wx.Bitmap(self.saveFile))
                cpd.ShowModal()
                ps = cpd.GetPixelSize()
            
            self.canvas.Load(ps, self.saveFile)
            self.canvas.Refresh()
            self.animControl.SetDocument(self.canvas.document)
            self.RefreshLayers()

    def OnRefImage(self, e):
        with wx.FileDialog(self, "Open Reference Image file",
                           wildcard=REF_FILE_DIALOG_FILTERS,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
                
            self.canvas.LoadRefImage(fd.GetPath())
            self.canvas.Refresh()

    def OnRemoveLayer(self, e):
        self.canvas.RemoveLayer()
        self.canvas.Refresh()
        self.RefreshLayers()
        
    def OnReselect(self, e):
        self.canvas.Reselect()
        self.Refresh()
        
    def OnResize(self, e):
        if self.FirstTimeResize:
            self.OnCenter(e)
            self.FirstTimeResize = False
        self.canvas.Refresh()
        e.Skip()

    def OnSave(self, e):
        if not self.saveFile:
            with wx.FileDialog(self, "Save Image file", wildcard = FILE_DIALOG_FILTERS,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
                if fd.ShowModal() == wx.ID_CANCEL:
                    return
                    
                self.saveFile = fd.GetPath()
            
        self.canvas.Save(self.saveFile)
        self.UpdateTitle()

    def OnSaveAs(self, e):
        with wx.FileDialog(self, "Save Image file", wildcard = FILE_DIALOG_FILTERS,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
                
            self.saveFile = fd.GetPath()
            
            self.canvas.Save(self.saveFile)
            self.UpdateTitle()

    def OnSaveGif(self, e):
        ret = wx.SaveFileSelector(PROGRAM_NAME, "gif", parent=self)
        if ret:
            self.canvas.SaveGif(ret)

    def OnSelectAll(self, e):
        self.canvas.Select()
        self.Refresh()
        
    def OnSelectInvert(self, e):
        self.canvas.SelectInvert()
        self.Refresh()
    
    def OnSettings(self, e):
        Settings(self).ShowModal()
        
    def OnSmoothLine(self, e):
        self.canvas.smoothLine = e.IsChecked()
        self.canvas.Refresh()

    def OnToggleGrid(self, e):
        self.canvas.gridVisible = e.IsChecked()
        self.canvas.Refresh()

    def OnTool(self, e):
        self.canvas.SetTool(e.GetString())

    def PenColorChanged(self, color):
        bitmap = self.colorbtn.GetBitmap()
        mdc = wx.MemoryDC(bitmap)
        clip = wx.Region(0,0,32,32)
        clip.Subtract(wx.Rect(9, 9, 14, 14))
        mdc.SetDeviceClippingRegion(clip)
        mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        mdc.SetPen(wx.NullPen)
        mdc.DrawRectangle(0,0,32,32)
        mdc.SelectObject(wx.NullBitmap)
        del mdc
        self.toolbar.SetToolNormalBitmap(self.colorbtn.GetId(), bitmap)

    def Redid(self):
        self.Undid()
        
    def RefreshLayers(self):
        self.lyrctrl.UpdateLayers(self.canvas.document)
        self.lyrctrl.FitInside()
        self.UpdateTitle()
        
    def Undid(self):
        self.RefreshLayers()
        
    def UpdateTitle(self):
        if not self.saveFile:
            title = PROGRAM_NAME+ ' - [Unsaved]'
        else:
            title = PROGRAM_NAME+ ' - ' + self.saveFile
            if self.canvas.IsDirty():
                title += ' *'
                
        self.SetTitle(title)
            
def CreateWindows():
    global app

    app = wx.App()

    Frame().Show()

def RunProgram():
    app.MainLoop()

CreateWindows()
RunProgram()
