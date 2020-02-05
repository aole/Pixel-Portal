"""
#### Pixel Portal ####
### Bhupendra Aole ###

# dictionarydialog.py #
####  5-Feb-2020 #####
"""

import wx

class DictionaryDialog(wx.Dialog):
    def __init__(self, parent, props):
        super().__init__(parent, title="Pixel Portal")
        
        self.props = props
        
        sizer = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        
        pos = 0
        for key, value in props.items():
            self.AddIntInput(key, value, sizer, pos)
            pos += 1
        
        self.SetSizerAndFit(sizer)
        
    def AddIntInput(self, key, value, sizer, pos):
        wsz = wx.BoxSizer()
        wsz.Add(wx.StaticText(self, label=key), 1, wx.EXPAND|wx.ALL, 2)
        
        ctl = wx.SpinCtrl(self, min=1, max=10000, initial=value)
        ctl.key = key
        ctl.Bind(wx.EVT_SPINCTRL, self.Spinner, id=ctl.GetId())
        wsz.Add(ctl, 2, wx.EXPAND|wx.ALL, 2)
        
        sizer.Insert(pos, wsz)
        
    def Get(self, prop):
        return self.props[prop]
        
    def Set(self, prop, value):
        self.props[prop] = value
        
    def Spinner(self, e):
        self.Set(e.GetEventObject().key, e.GetPosition())
        
if __name__ == '__main__':
    app = wx.App()
    dlg = NewDialog(None, {'Width':10, 'Height':10})
    if dlg.ShowModal()==wx.ID_OK:
        print(dlg.Get('Width'), dlg.Get('Height'))
        