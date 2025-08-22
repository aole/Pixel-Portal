"""
#### Pixel Portal ####
### Bhupendra Aole ###
"""

import wx

class GenerateImageDialog(wx.Dialog):
    def __init__(self, parent, props):
        super().__init__(parent, title="Generate Image from Prompt", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.props = props

        sizerb = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        sizer = wx.GridBagSizer(2, 20)
        sizerb.Insert(0, sizer, 1, wx.EXPAND|wx.ALL, 5)

        self.ctrls = {}
        self.scaled_labels = {}

        row = 0
        for key, value in props.items():
            if isinstance(value, int):
                self.AddIntInput(key, value, sizer, row)
                if key in ['Width', 'Height']:
                    self.scaled_labels[key] = wx.StaticText(self, label=f"x 8 = {value*8}")
                    sizer.Add(self.scaled_labels[key], pos=(row, 4))
                row += 1
            elif isinstance(value, str):
                self.AddStringInput(key, value, sizer, row)
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

    def AddIntInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        ctrl = wx.SpinCtrl(self, min=1, max=10000, initial=value)
        ctrl.key = key
        ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())
        self.ctrls[key] = ctrl
        self.AddControls(sizer, row, lbl, 1, ctrl, 1)

    def AddStringInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        ctrl = wx.TextCtrl(self, value=value, size=(300, 100), style=wx.TE_MULTILINE)
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
        key = e.GetEventObject().key
        if key in self.scaled_labels:
            self.scaled_labels[key].SetLabel(f"x 8 = {e.GetPosition()*8}")

    def TextChange(self, e):
        self.Set(e.GetEventObject().key, e.GetString())

class GenerateLayerDialog(wx.Dialog):
    def __init__(self, parent, props):
        super().__init__(parent, title="Generate Layer from Prompt", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.props = props

        sizerb = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        sizer = wx.GridBagSizer(2, 20)
        sizerb.Insert(0, sizer, 1, wx.EXPAND|wx.ALL, 5)

        row = 0
        for key, value in props.items():
            if isinstance(value, int):
                self.AddIntInput(key, value, sizer, row, readonly=True)
                row += 1
            elif isinstance(value, str):
                self.AddStringInput(key, value, sizer, row)
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

    def AddIntInput(self, key, value, sizer, row, readonly=False):
        lbl = self.GetLabel(key)
        ctrl = wx.SpinCtrl(self, min=1, max=10000, initial=value)
        if readonly:
            ctrl.Disable()
        else:
            ctrl.key = key
            ctrl.Bind(wx.EVT_SPINCTRL, self.SpinnerChange, id=ctrl.GetId())

        self.AddControls(sizer, row, lbl, 1, ctrl, 1)

    def AddStringInput(self, key, value, sizer, row):
        lbl = self.GetLabel(key)
        ctrl = wx.TextCtrl(self, value=value, size=(300, 100), style=wx.TE_MULTILINE)
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
