"""
#### Pixel Portal ####
### Bhupendra Aole ###

# dictionarydialog.py #
####  5-Feb-2020 #####
"""

import wx

FILE_DIALOG_FILTERS = "supported|*.aole;*.tif;*.png|aole files (*.aole)|*.aole|tif files (*.tif)|*.tif|png files (*.png)|*.png"

class ImageOpenProperty:
    def __init__(self, filename):
        self.filename = filename
        
class DictionaryDialog(wx.Dialog):
    def __init__(self, parent, props):
        super().__init__(parent, title="Pixel Portal", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        self.props = props
        
        sizerb = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        sizer = wx.GridBagSizer(2, 20)
        sizerb.Insert(0, sizer, 1, wx.EXPAND|wx.ALL, 5)
        
        row = 0
        for key, value in props.items():
            if isinstance(value, int):
                self.AddIntInput(key, value, sizer, row)
                row += 1
            elif isinstance(value, str):
                self.AddStringInput(key, value, sizer, row)
                row += 1
            elif isinstance(value, ImageOpenProperty):
                self.AddImageOpenInput(key, value.filename, sizer, row)
                row += 1
            
        self.SetSizerAndFit(sizerb)
        
    def AddControls(self, sizer, row, ctrl1, span1, ctrl2, span2):
        col = 0
        if ctrl1:
            sizer.Add(ctrl1, wx.GBPosition(row, col), wx.GBSpan(1, span1))
            col += span1
        if ctrl2:
            sizer.Add(10, 0, wx.GBPosition(row, col))
            sizer.Add(ctrl2, wx.GBPosition(row, col+1), wx.GBSpan(1, span2))
            col += 2
            
    def AddImageOpenInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        
        sz = wx.BoxSizer(wx.HORIZONTAL)
        tctrl = wx.TextCtrl(self, value=value)
        tctrl.Bind(wx.EVT_TEXT, self.TextChange, id=tctrl.GetId())
        tctrl.key = key
        
        bitmap = wx.Image('../icons/load.png').Rescale(16,16).ConvertToBitmap()
        bctrl = wx.BitmapButton(self, bitmap=bitmap)
        bctrl.tctrl = tctrl
        self.Bind(wx.EVT_BUTTON, self.OnFileOpen, id=bctrl.GetId())
        
        sz.Add(tctrl, 3, wx.EXPAND|wx.ALL, 0)
        sz.Add(bctrl, 1, 0, 0)
        
        self.AddControls(sizer, row, lbl, 1, sz, 1)
        
    def AddIntInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        ctrl = wx.SpinCtrl(self, min=1, max=10000, initial=value)
        ctrl.key = key
        ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())
        
        self.AddControls(sizer, row, lbl, 1, ctrl, 1)
        
    def AddStringInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        ctrl = wx.TextCtrl(self, value=value)
        ctrl.key = key
        ctrl.Bind(wx.EVT_TEXT, self.TextChange, id=ctrl.GetId())
        
        self.AddControls(sizer, row, lbl, 1, ctrl, 1)
        
    def Get(self, prop):
        return self.props[prop]
        
    def GetLabel(self, key):
        lbl = wx.StaticText(self, label=key, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        return lbl
        
    def OnFileOpen(self, e):
        with wx.FileDialog(self, "Pixel Portal",
                           wildcard=FILE_DIALOG_FILTERS,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            
            e.GetEventObject().tctrl.SetValue(fd.GetPath())
        
    def Set(self, prop, value):
        self.props[prop] = value
        
    def SpinnerChange(self, e):
        self.Set(e.GetEventObject().key, e.GetPosition())
        
    def TextChange(self, e):
        self.Set(e.GetEventObject().key, e.GetString())
        
class ChangePixelDialog(wx.Dialog):
    def __init__(self, parent, bitmap):
        super().__init__(parent, title="Pixel Portal - Adjust Pixel Size", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.bitmap = bitmap
        self.pixel = pixel = 5
        
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        
        ctrlsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        spinsizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label='Pixel Size:')
        spinsizer.Add(lbl, 1, wx.EXPAND|wx.ALL, 2)
        ctrl = wx.SpinCtrl(self, min=1, max=1000, initial=pixel)
        ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())
        spinsizer.Add(ctrl, 2, wx.EXPAND|wx.ALL, 2)
        ctrlsizer.Add(spinsizer, 1, wx.EXPAND|wx.ALL, 2)
        
        self.lblWidth = wx.StaticText(self, label='Width: '+str(bitmap.Width//pixel))
        ctrlsizer.Add(self.lblWidth, 1, wx.EXPAND|wx.ALL, 2)
        
        self.lblHeight = wx.StaticText(self, label='Height: '+str(bitmap.Height//pixel))
        ctrlsizer.Add(self.lblHeight, 1, wx.EXPAND|wx.ALL, 2)
        
        mainsizer.Add(ctrlsizer, 0, wx.EXPAND|wx.ALL, 2)
        
        self.panel = wx.StaticBitmap(self, bitmap=self.ProcessBitmap(bitmap, pixel))
        mainsizer.Add(self.panel, 1, wx.EXPAND|wx.ALL, 2)
        
        self.SetSizerAndFit(mainsizer)
        
    def GetPixelSize(self):
        return self.pixel
        
    def ProcessBitmap(self, bitmap, size):
        if size<2:
            return bitmap
            
        pb = wx.Bitmap(bitmap.Width, bitmap.Height, 32)
        mdc = wx.MemoryDC(pb)
        gc = wx.GraphicsContext.Create(mdc)
        gc.DrawBitmap(bitmap, 0, 0, pb.Width, pb.Height)
        
        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)
        gc.SetInterpolationQuality(wx.INTERPOLATION_NONE)
        gc.SetPen(wx.ThePenList.FindOrCreatePen(wx.Colour(0,0,0,50), 1))
        for y in range(0, pb.Height+1, size):
            gc.StrokeLine(0, y, pb.Width, y)
        for x in range(0, pb.Width+1, size):
            gc.StrokeLine(x, 0, x, pb.Height)
        mdc.SelectObject(wx.NullBitmap)
        
        return pb
        
    def SpinnerChange(self, e):
        self.pixel = p = e.GetPosition()
        self.panel.SetBitmap(self.ProcessBitmap(self.bitmap, p))
        self.lblWidth.SetLabel('Width: '+str(self.bitmap.Width//p))
        self.lblHeight.SetLabel('Height: '+str(self.bitmap.Height//p))
        self.Refresh()
        
class ResizeDialog(wx.Dialog):
    def __init__(self, parent, bitmap, pixel):
        super().__init__(parent, title="Pixel Portal - Resize Document", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.bitmap = bitmap
        self.pixel = pixel
        self.prop = {'Width':bitmap.Width, 'Height':bitmap.Height}
        
        sizerb = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        sizerb.Insert(0, mainsizer, 1, wx.EXPAND|wx.ALL, 5)
        
        ctrlsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        spinsizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label='Width:')
        spinsizer.Add(lbl, 1, wx.EXPAND|wx.ALL, 2)
        ctrl = wx.SpinCtrl(self, min=1, max=10000, initial=bitmap.Width)
        ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())
        ctrl.prop = 'Width'
        spinsizer.Add(ctrl, 2, wx.EXPAND|wx.ALL, 2)
        ctrlsizer.Add(spinsizer, 1, wx.EXPAND|wx.ALL, 2)
        
        spinsizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, label='Height:')
        spinsizer.Add(lbl, 1, wx.EXPAND|wx.ALL, 2)
        ctrl = wx.SpinCtrl(self, min=1, max=10000, initial=bitmap.Height)
        ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())
        ctrl.prop = 'Height'
        spinsizer.Add(ctrl, 2, wx.EXPAND|wx.ALL, 2)
        ctrlsizer.Add(spinsizer, 1, wx.EXPAND|wx.ALL, 2)
        
        mainsizer.Add(ctrlsizer, 0, wx.EXPAND|wx.ALL, 2)
        
        self.panel = wx.StaticBitmap(self, bitmap=self.ProcessBitmap(bitmap))
        self.panel.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        mainsizer.Add(self.panel, 1, wx.EXPAND|wx.ALL, 10)
        
        self.SetSizerAndFit(sizerb)
    
    def GetHeight(self):
        return self.prop['Height']
        
    def GetWidth(self):
        return self.prop['Width']
        
    def OnMouseWheel(self, e):
        amt = e.GetWheelRotation()
        if amt > 0:
            self.pixel += 1
        else:
            self.pixel -= 1
            if self.pixel < 1:
                self.pixel = 1
        self.panel.SetBitmap(self.ProcessBitmap(self.bitmap))
        self.Refresh()
        self.Fit()
        
    def ProcessBitmap(self, bitmap):
        width, height = self.prop['Width']*self.pixel, self.prop['Height']*self.pixel
        pb = wx.Bitmap(width, height, 32)
        mdc = wx.MemoryDC(pb)
        
        mdc.SetPen(wx.NullPen)
        mdc.SetBrush(wx.TheBrushList.FindOrCreateBrush(wx.BLACK))
        mdc.DrawRectangle(0, 0, width, height)
        
        bdc = wx.MemoryDC(bitmap)
        mdc.StretchBlit(0, 0,
                       bitmap.Width*self.pixel, bitmap.Height*self.pixel,
                       bdc,
                       0, 0,
                       bitmap.Width, bitmap.Height)
        
        bdc.SelectObject(wx.NullBitmap)
        mdc.SelectObject(wx.NullBitmap)
        
        return pb
        
    def SpinnerChange(self, e):
        self.prop[e.GetEventObject().prop] = e.GetPosition()
        self.panel.SetBitmap(self.ProcessBitmap(self.bitmap))
        self.Fit()
        self.Refresh()
        
if __name__ == '__main__':
    app = wx.App()
    '''
    dlg = DictionaryDialog(None, {'Width':10, 'Height':10})
    dlg.ShowModal()
    
    dlg = ChangePixelDialog(None, wx.Bitmap('C:/Users/baole/Downloads/test.jpg'))
    dlg.ShowModal()
    print(dlg.GetPixelSize())
    '''
    dlg = ResizeDialog(None, wx.Bitmap('C:/Users/baole/Downloads/test.jpg'), 2)
    if dlg.ShowModal()==wx.ID_OK:
        print('ok')
    