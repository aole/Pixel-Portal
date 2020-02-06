"""
#### Pixel Portal ####
### Bhupendra Aole ###

# dictionarydialog.py #
####  5-Feb-2020 #####
"""

import wx
from wx.lib.filebrowsebutton import FileBrowseButtonWithHistory

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
        
    def Set(self, prop, value):
        self.props[prop] = value
        
    def SpinnerChange(self, e):
        self.Set(e.GetEventObject().key, e.GetPosition())
        
    def TextChange(self, e):
        self.Set(e.GetEventObject().key, e.GetString())
        
if __name__ == '__main__':
    app = wx.App()
    dlg = DictionaryDialog(None, {'File': ImageOpenProperty('c:/temp/test.png'), 'Width':10, 'Height':10})
    if dlg.ShowModal()==wx.ID_OK:
        print(dlg.Get('File'), dlg.Get('Width'), dlg.Get('Height'))
        