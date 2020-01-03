
#### Pixel Art ####
## Bhupendra Aole #

import numpy as np
import random
import wx

from PIL import Image

DEFAULT_DOC_SIZE = (32, 32)
NUM_UNDOS = 100
TOOLS = {"Pen":wx.CURSOR_PENCIL,    "Line":wx.CURSOR_CROSS,         "Ellipse":wx.CURSOR_CROSS,
         "Move":wx.CURSOR_SIZING,   "Bucket":wx.CURSOR_PAINT_BRUSH, "Picker":wx.CURSOR_RIGHT_ARROW}

app = None

class Layer (wx.Bitmap):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = self.GetWidth()
        self.height = self.GetHeight()
        
    def Scaled(self, factor):
        bitmap = wx.Bitmap.FromRGBA(self.width*factor, self.height*factor, 0, 0, 0, 0)
        mdcd = wx.MemoryDC(bitmap)
        mdcs = wx.MemoryDC(self)
        mdcd.StretchBlit(0, 0,
                       self.width*factor, self.height*factor,
                       mdcs,
                       0,
                       0,
                       self.width, self.height)
        
        return bitmap
        
    def Clear(self, color):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        
        #gc.DrawRectangle(0, 0, *gc.GetSize())
        # weird bug ^^^ can't correctly draw a big rectangle in one go
        for x in range(0, self.width, 60):
            for y in range(0, self.height, 60):
                gc.DrawRectangle(x, y, 60, 60)
        
    def GetPixel(self, x, y):
        mdc = wx.MemoryDC(self)
        return mdc.GetPixel(x, y)
        
    def SetPixel(self, x, y, color):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        gc.DrawRectangle(x, y, 1, 1)
        
    def SetPixels(self, pixels, color):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetBrush(wx.TheBrushList.FindOrCreateBrush(color))
        for x,y in pixels:
            gc.DrawRectangle(x, y, 1, 1)
        
    def Line(self, x0, y0, x1, y1, color):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color))
        gc.StrokeLine(x0,y0,x1,y1)
        
    def Ellipse(self, x, y, w, h, color):
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(color))
        gc.DrawEllipse(x, y, w, h)
        
    def Blit(self, layer, x=0, y=0, w=0, h=0):
        if w==0:
            w = layer.width
        if h==0:
            h = layer.height
        
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.DrawBitmap(layer, x, y, w, h)
        
    def Load(self, name):
        bitmap = wx.Bitmap()
        bitmap.LoadFile(name)
        
        mdc = wx.MemoryDC(self)
        gc = wx.GraphicsContext.Create(mdc)
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.DrawBitmap(bitmap, 0, 0, self.width, self.height)
        
class LayerCommand(wx.Command):
    def __init__(self, layer, before, after):
        super().__init__(True)
        
        self.layer = layer
        self.before = before
        self.after = after
        
    def Do(self):
        self.layer.Blit(self.after)
        return True
        
    def Undo(self):
        self.layer.Blit(self.before)
        return True
        
class Canvas(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        
        self.full_redraw = True
        
        self.panx = 20
        self.pany = 20
        
        self.prevx, self.prevy = 0, 0
        self.origx, self.origy = 0, 0
        
        self.movex, self.movey = 0, 0
        
        self.mouseState = 0
        
        self.current_tool = "Pen"
        self.mirrorx = False
        
        self.pixel_size = 10
        
        self.penColor = 1 #
        self.eraserColor = 2 #
        self.palette = None
        
        self.layers = {}
        
        # UNDO / REDO
        self.history = wx.CommandProcessor(NUM_UNDOS)
        self.beforeLayer = None
        
        self.SetCursor(wx.Cursor(TOOLS[self.current_tool]))
        
        self.listeners = []
        
    def Blit(self, source, destination, x=0, y=0):
        self.layers[destination].Blit(self.layers[source], x, y)
        
    def ClearCurrentLayer(self):
        self.beforeLayer = Layer(self.layers["current"])
        
        self.layers["current"].Clear(self.palette[self.eraserColor])
        
        self.history.Store(LayerCommand(self.layers["current"], self.beforeLayer, Layer(self.layers["current"])))
        self.beforeLayer = None
        self.Refresh()
        
    def DrawGrid(self, gc):
        w, h = self.GetClientSize()
        
        # minor lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#55555555'))
        path = gc.CreatePath()
        for x in range(self.panx, min(self.panx+self.layers["width"]*self.pixel_size+1, w), self.pixel_size):
            path.MoveToPoint(x, self.pany)
            path.AddLineToPoint(x, min(self.pany+self.layers["height"]*self.pixel_size, h))
        for y in range(self.pany, min(self.pany+self.layers["height"]*self.pixel_size+1, h), self.pixel_size):
            path.MoveToPoint(self.panx, y)
            path.AddLineToPoint(min(self.panx+self.layers["width"]*self.pixel_size, w), y)
        gc.StrokePath(path)
        
        midpx = self.pixel_size*int(self.layers["width"]/2)
        midpy = self.pixel_size*int(self.layers["height"]/2)
        
        # major lines
        gc.SetPen(wx.ThePenList.FindOrCreatePen('#22222255'))
        path = gc.CreatePath()
        if midpx:
            for x in range(self.panx, min(self.panx+self.layers["width"]*self.pixel_size+1, w), midpx):
                path.MoveToPoint(x, self.pany)
                path.AddLineToPoint(x, min(self.pany+self.layers["height"]*self.pixel_size, h))
        if midpy:
            for y in range(self.pany, min(self.pany+self.layers["height"]*self.pixel_size+1, h), midpy):
                path.MoveToPoint(self.panx, y)
                path.AddLineToPoint(min(self.panx+self.layers["width"]*self.pixel_size, w), y)
        gc.StrokePath(path)
        
    def DrawPixel(self, layer, x, y, color):
        self.layers[layer].SetPixel(x, y, self.palette[color])
        
    def FloodFill(self, layer, x, y, color):
        if x<0 or y<0 or x>self.layers["width"]-1 or y>self.layers["height"]-1:
            return
            
        color = wx.Colour(self.palette[color])
        
        l = self.layers[layer]
        replace = l.GetPixel(x, y)
        
        queue = {(x,y)}
        while queue:
            # replace current pixel
            x, y = queue.pop()
            l.SetPixel(x, y, color)
            
            #north
            if y>0 and l.GetPixel(x, y-1)==replace and l.GetPixel(x, y-1)!=color:
                queue.add((x, y-1))
            #east
            if x<self.layers["width"]-1 and l.GetPixel(x+1, y)==replace and l.GetPixel(x+1,y)!=color:
                queue.add((x+1, y))
            #south
            if y<self.layers["height"]-1 and l.GetPixel(x, y+1)==replace and l.GetPixel(x, y+1)!=color:
                queue.add((x, y+1))
            #west
            if x>0 and l.GetPixel(x-1, y)==replace and l.GetPixel(x-1, y)!=color:
                queue.add((x-1, y))
            
    def DrawLine(self, layer, x0, y0, x1, y1, color):
        self.layers[layer].Line(x0, y0, x1, y1, self.palette[color])
        
    def DrawEllipse(self, layer, x0, y0, x1, y1, color):
        self.layers[layer].Ellipse(min(x0, x1), min(y0, y1), abs(x1-x0), abs(y1-y0), self.palette[color])
        
    def GetPenColor(self):
        return self.palette[self.penColor]
        
    def GetEraserColor(self):
        return self.palette[self.eraserColor]
        
    def SetPenColor(self, color):
        color = color+"FF"
        if color not in self.palette:
            self.penColor = len(self.palette)
            self.palette.append(color)
        else:
            self.penColor = self.palette.index(color)
            
    def SetEraserColor(self, color):
        color = color+"FF"
        if color not in self.palette:
            self.eraserColor = len(self.palette)
            self.palette.append(color)
        else:
            self.eraserColor = self.palette.index(color)
        
    def PixelAtPosition(self, x, y):
        return (int((x - self.panx)/self.pixel_size),
                int((y - self.pany)/self.pixel_size))
        
    def ChangePenColor(self, color):
        self.penColor = self.ColorIndex(color.GetAsString(wx.C2S_HTML_SYNTAX))
        for l in self.listeners:
            l.PenColorChanged(color)
            
    def OnMouseMove(self, e):
        x, y = e.GetPosition()
        gx, gy = self.PixelAtPosition(x, y)
        
        # draw with 1st color
        if self.mouseState == 1:
            if self.current_tool == "Pen":
                self.DrawPixel("drawing", gx, gy, self.penColor)
                if self.mirrorx:
                    self.DrawPixel("drawing", *self.GetMirror(gx, gy), self.penColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), gx, gy, self.penColor)
            elif self.current_tool == "Move":
                self.movex, self.movey = x-self.origx, y-self.origy
                # move in grid spaces
                self.movex -= self.movex % self.pixel_size
                self.movey -= self.movey % self.pixel_size
            elif self.current_tool == "Picker":
                color = self.layers["current"].GetPixel(*self.PixelAtPosition(self.prevx, self.prevy))
                self.ChangePenColor(color)
                
            self.Refresh()
        
        # draw with 2nd color
        elif self.mouseState == 2:
            if self.current_tool == "Pen":
                self.DrawPixel("drawing", gx, gy, self.eraserColor)
                if self.mirrorx:
                    self.DrawPixel("drawing", *self.GetMirror(gx, gy), self.eraserColor)
            elif self.current_tool == "Line":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawLine("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y), self.eraserColor)
            elif self.current_tool == "Ellipse":
                self.layers["drawing"].Clear(self.palette[0])
                self.DrawEllipse("drawing", *self.PixelAtPosition(self.origx, self.origy), *self.PixelAtPosition(x, y), self.eraserColor)
            
            self.Refresh()
            
        elif self.mouseState == 3:
            self.panx += x - self.prevx
            self.pany += y - self.prevy
            
            self.full_redraw = True
            self.Refresh()
            
        self.prevx, self.prevy = x, y
        
    def GetMirror(self, x, y):
        h = int(self.layers["width"]/2)
        return ((x+1-h)*-1)+h, y
        
    def OnLeftDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 1
        gx, gy = self.PixelAtPosition(self.prevx, self.prevy)
        
        self.noUndo = False
        # store a copy of the before picture
        self.beforeLayer = Layer(self.layers["current"])
        
        if self.current_tool == "Pen":
            self.DrawPixel("drawing", gx, gy, self.penColor)
            if self.mirrorx:
                self.DrawPixel("drawing", *self.GetMirror(gx, gy), self.penColor)
        elif self.current_tool == "Move":
            self.Blit("current", "drawing")
            self.layers["current"].Clear(self.palette[self.eraserColor])
        elif self.current_tool == "Bucket":
            self.Blit("current", "drawing")
            self.layers["current"].Clear(self.palette[self.eraserColor])
            self.FloodFill("drawing", x, y, self.penColor)
        elif self.current_tool == "Picker":
            self.noUndo = True
            color = self.layers["current"].GetPixel(x, y)
            self.ChangePenColor(color)
            
        if not self.HasCapture():
            self.CaptureMouse()
            
        self.Refresh()
    
    def OnLeftUp(self, e):
        x, y = e.GetPosition()
        self.mouseState = 0
        
        if self.HasCapture():
            # to avoid
            # wx._core.wxAssertionError: C++ assertion "!wxMouseCapture::stack.empty()"
            self.ReleaseMouse()
        
        # transfer from drawing layer to current_layer
        if self.current_tool in ("Pen", "Line", "Ellipse", "Bucket"):
            self.Blit("drawing", "current")
        elif self.current_tool == "Move":
            self.Blit("drawing", "current", int(self.movex/self.pixel_size), int(self.movey/self.pixel_size))
            
        self.movex, self.movey = 0, 0
        
        self.layers["drawing"].Clear(self.palette[0])
        
        # create an undo command
        if not self.noUndo:
            self.history.Store(LayerCommand(self.layers["current"], self.beforeLayer, Layer(self.layers["current"])))
        self.beforeLayer = None
        
        self.Refresh()
        
    def OnRightDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 2
        
        # store a copy of the before picture
        self.beforeLayer = Layer(self.layers["current"])
        
        # put a dot
        if self.current_tool=="Eraser":
            self.DrawPixel("drawing", *self.PixelAtPosition(self.prevx, self.prevy), self.eraserColor)
        
        if not self.HasCapture():
            self.CaptureMouse()
            
        self.Refresh()
        
    def OnRightUp(self, e):
        self.OnLeftUp(e)
        
    def OnMiddleDown(self, e):
        self.prevx, self.prevy = e.GetPosition()
        self.origx, self.origy = e.GetPosition()
        self.mouseState = 3
        
    def OnMiddleUp(self, e):
        self.mouseState = 0
        
    def FullRedraw(self):
        self.full_redraw = True
        self.Refresh()
        
    def OnPaint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        if self.full_redraw:
            dc.SetBackground(wx.TheBrushList.FindOrCreateBrush("#999999FF"))
            dc.Clear()
            self.full_redraw = False
        
        # clip only to the document
        dc.SetClippingRegion(self.panx, self.pany, self.layers["width"]*self.pixel_size, self.layers["height"]*self.pixel_size)
        
        mdc = wx.MemoryDC(self.layers["current"])
        dc.StretchBlit(self.panx, self.pany,
                       self.layers["width"]*self.pixel_size, self.layers["height"]*self.pixel_size,
                       mdc,
                       0,
                       0,
                       self.layers["width"], self.layers["height"])
        
        mdc = wx.MemoryDC(self.layers["drawing"])
        dc.StretchBlit(self.panx+self.movex, self.pany+ self.movey,
                       self.layers["width"]*self.pixel_size, self.layers["height"]*self.pixel_size,
                       mdc,
                       0,
                       0,
                       self.layers["width"], self.layers["height"])
        
        gc = wx.GraphicsContext.Create(dc)
        self.DrawGrid(gc)
        
    def Undo(self):
        self.history.Undo()
        self.Refresh()
        
    def Redo(self):
        self.history.Redo()
        self.Refresh()
        
    def IsDirty(self):
        return self.history.IsDirty()
        
    def New(self, width, height):
        self.palette = ["#00000000", "#000000FF", "#FFFFFFFF"]
        self.penColor = 1 #
        self.eraserColor = 2 #
        
        # to ensure alpha
        current_layer = Layer(wx.Bitmap.FromRGBA(width, height, 255, 255, 255, 255))
        drawing_layer = Layer(wx.Bitmap.FromRGBA(width, height, 0, 0, 0, 0))
        
        self.layers = {"width":     width,
                       "height":    height,
                       "drawing":   drawing_layer,
                       "current":   current_layer}
                       
        self.history.ClearCommands()
        
    def ColorIndex(self, color):
        if len(color)==7:
            color += "FF"
        if color not in self.palette:
            self.palette.append(color)
            return len(self.palette)-1
        else:
            return self.palette.index(color)
        
    def Load(self, filename):
        image = wx.Image(filename)
        width, height = int(image.GetWidth()/self.pixel_size), int(image.GetHeight()/self.pixel_size)
        
        self.New(width, height)
        
        self.layers["current"].Load(filename)
        
        self.history.ClearCommands()
        
    def Save(self, filename):
        self.layers["current"].Scaled(self.pixel_size).SaveFile(filename, wx.BITMAP_TYPE_PNG)
        self.history.MarkAsSaved()
        
    def SaveGif(self, filename):
        images = []
        wxImage = self.history.GetCommands()[0].before.Scaled(self.pixel_size).ConvertToImage()
        pilImage = Image.new( 'RGB', (wxImage.GetWidth(), wxImage.GetHeight()) )
        pilImage.frombytes( np.array(wxImage.GetDataBuffer() ))
        images.append(pilImage)
        
        for cmd in self.history.GetCommands():
            wxImage = cmd.after.Scaled(self.pixel_size).ConvertToImage()
            pilImage = Image.new( 'RGB', (wxImage.GetWidth(), wxImage.GetHeight()) )
            pilImage.frombytes( np.array(wxImage.GetDataBuffer() ))
            images.append(pilImage)
        images[0].save(filename, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)
        
    def SetTool(self, tool):
        self.current_tool = tool
        self.SetCursor(wx.Cursor(TOOLS[tool]))
        
class Frame(wx.Frame):
    def __init__(self):
        super().__init__(None, title = 'Pixel Art', size=(440,500))
        
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        self.canvas = Canvas(self)
        self.canvas.New(*DEFAULT_DOC_SIZE)
        self.canvas.listeners.append(self)
        
        tb = self.CreateToolBar()
        self.AddToolButton(tb, 'Clear', self.OnClear)
        
        self.txtWidth = wx.TextCtrl(tb, value=str(DEFAULT_DOC_SIZE[0]))
        self.AddToolControl(tb, self.txtWidth)
        self.txtHeight = wx.TextCtrl(tb, value=str(DEFAULT_DOC_SIZE[1]))
        self.AddToolControl(tb, self.txtHeight)
        
        self.AddToolButton(tb, 'New', self.OnNew)
        self.AddToolButton(tb, 'Load', self.OnLoad)
        self.AddToolButton(tb, 'Save', self.OnSave)
        self.AddToolButton(tb, 'Gif', self.OnSaveGif)
        
        self.colorbtn = wx.ColourPickerCtrl(tb, colour=self.canvas.GetPenColor())
        self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnColor, id=self.colorbtn.GetId())
        self.AddToolControl(tb, self.colorbtn)
        
        self.eraserbtn = wx.ColourPickerCtrl(tb, colour=self.canvas.GetEraserColor())
        self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnEraser, id=self.eraserbtn.GetId())
        self.AddToolControl(tb, self.eraserbtn)
        
        toolbtn = wx.ComboBox(tb, value="Pen", choices=list(TOOLS.keys()), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnTool, id=toolbtn.GetId())
        self.AddToolControl(tb, toolbtn)
        toolbtn.SetSize(wx.DefaultCoord, wx.DefaultCoord, 60, wx.DefaultCoord)
        
        self.AddToggleButton(tb, 'MX', self.OnMirrorX)
        
        tb.Realize()
        
        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.canvas, wx.ID_ANY, wx.EXPAND | wx.ALL, 2)
        self.SetSizer(bs)
        
        self.FirstTimeResize = True
        
    def PenColorChanged(self, color):
        self.colorbtn.SetColour(color)
        
    def AddToolButton(self, tb, label, function):
        btn = wx.Button(tb, wx.ID_ANY, label=label)
        self.AddToolControl(tb, btn)
        btn.SetSize(wx.DefaultCoord, wx.DefaultCoord, 40, wx.DefaultCoord)
        self.Bind(wx.EVT_BUTTON, function, id=btn.GetId())
        
    def AddToggleButton(self, tb, label, function):
        btn = wx.ToggleButton(tb, wx.ID_ANY, label=label)
        self.AddToolControl(tb, btn)
        btn.SetSize(wx.DefaultCoord, wx.DefaultCoord, 40, wx.DefaultCoord)
        self.Bind(wx.EVT_TOGGLEBUTTON, function, id=btn.GetId())
        
    def AddToolControl(self, tb, control):
        control.SetCanFocus(False)
        control.SetSize(wx.DefaultCoord, wx.DefaultCoord, 30, wx.DefaultCoord)
        tb.AddControl(control)
        
    def OnClear(self, e):
        self.canvas.ClearCurrentLayer()
        
    def CheckDirty(self):
        if self.canvas.IsDirty():
            diag = wx.GenericMessageDialog(self, 'Save Changes?', style=wx.YES_NO|wx.CANCEL)
            ret = diag.ShowModal()
            if ret==wx.ID_YES:
                self.OnSave(None)
                return True
            elif ret==wx.ID_CANCEL:
                return False
            
        return True
        
    def OnLoad(self, e):
        if not self.CheckDirty():
            return
            
        ret = wx.LoadFileSelector("Pixel Art", "png", parent=self)
        if ret:
            self.canvas.Load(ret)
            self.canvas.FullRedraw()
        
    def OnMirrorX(self, e):
        self.canvas.mirrorx = e.IsChecked()
        
    def OnNew(self, e):
        if not self.CheckDirty():
            return
            
        try:
            self.colorbtn.SetColour("#000000FF")
            self.eraserbtn.SetColour("#FFFFFFFF")
            width = int(self.txtWidth.GetValue())
            height = int(self.txtHeight.GetValue())
            self.canvas.New(width, height)
            self.canvas.FullRedraw()
        except:
            print('error')
        
    def OnSave(self, e):
        ret = wx.SaveFileSelector("Pixel Art", "png", parent=self)
        if ret:
            self.canvas.Save(ret)
        
    def OnSaveGif(self, e):
        ret = wx.SaveFileSelector("Pixel Art", "gif", parent=self)
        if ret:
            self.canvas.SaveGif(ret)
        
    def OnColor(self, e):
        self.canvas.SetPenColor(e.Colour.GetAsString(wx.C2S_HTML_SYNTAX))
        
    def OnEraser(self, e):
        self.canvas.SetEraserColor(e.Colour.GetAsString(wx.C2S_HTML_SYNTAX))
        
    def OnKeyDown(self, e):
        keycode = e.GetUnicodeKey()
        
        passEvent = True
        if keycode == ord('Z'):
            if e.ControlDown():
                passEvent = False
                if e.ShiftDown():
                    self.canvas.Redo()
                else:
                    self.canvas.Undo()
        
        if passEvent:
            e.Skip()
        
    def OnTool(self, e):
        self.canvas.SetTool(e.GetString())
        
    def OnResize(self, e):
        if self.FirstTimeResize:
            pass
        self.canvas.FullRedraw()
        e.Skip()
        
def CreateWindows():
    global app
    
    app = wx.App()
    
    Frame().Show()
    
def RunProgram():
    app.MainLoop()

CreateWindows()
RunProgram()
