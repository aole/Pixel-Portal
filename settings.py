"""
settings.py
Bhupendra Aole
1/31/2020
"""

import wx
import wx.propgrid

import configparser

settings = {}

def GetSetting(section, property, value):
    global settings
    
    lp = property.lower()
    if section not in settings:
        settings[section] = {}
    if lp not in settings[section]:
        settings[section][property] = value
        return value
        
    return settings[section].get(lp).GetValue()
        
class Settings(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Pixel Portal Settings", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizerb = self.CreateSeparatedButtonSizer(wx.OK)
        
        self.pgm = wx.propgrid.PropertyGridManager(self, size=wx.Size(400,300),
            # These and other similar styles are automatically
            # passed to the embedded wx.PropertyGrid.
            style = wx.propgrid.PG_BOLD_MODIFIED|wx.propgrid.PG_SPLITTER_AUTO_CENTER|
            # Include toolbar.
            wx.propgrid.PG_TOOLBAR |
            # Include description box.
            wx.propgrid.PG_DESCRIPTION |
            # Plus defaults.
            wx.propgrid.PGMAN_DEFAULT_STYLE)
            
        sizerb.Insert(0, self.pgm, 1, wx.EXPAND|wx.ALL, 2)
            
        self.pgm.SetDescBoxHeight(40)
        
        self.LoadSettings('settings.ini')
        
        self.SetSizerAndFit(sizerb)
        
    def GetProperty(typ, prop, value):
        typ = typ.lower()
        if typ=='uint':
            return wx.propgrid.UIntProperty(prop, value=int(value))
        elif typ=='int':
            return wx.propgrid.IntProperty(prop, value=int(value))
        elif typ in ('color', 'colour'):
            return wx.propgrid.ColourProperty(prop, value=wx.Colour(value))
        elif typ in ('bool', 'boolean'):
            return wx.propgrid.BoolProperty(prop, value=eval(value.title()))
        elif typ in ('string', 'char'):
            return wx.propgrid.StringProperty(prop, value=value)
        
        return wx.propgrid.StringProperty(prop, value=value)
        
    def LoadSettings(self, file):
        global settings
        
        config = configparser.ConfigParser()
        config.read(file)
        
        settings.clear()
        page = self.pgm.AddPage("General")
        for section in config.sections():
            page.Append(wx.propgrid.PropertyCategory(section))
            settings[section] = {}
            for prop in config[section]:
                value = config[section][prop]
                prop, typ = prop.split('/')
                prop = prop.strip()
                gp = Settings.GetProperty(typ.strip(), prop.title(), value)
                settings[section][prop] = gp
                page.Append(gp)
    
    def SaveSettings(self, file):
        global settings
        
        config = configparser.ConfigParser()
        for sec, props in settings.items():
            config[sec] = {}
            section = config[sec]
            for key, value in props.items():
                if isinstance(value, wx.propgrid.IntProperty):
                    key += '/int'
                elif isinstance(value, wx.propgrid.UIntProperty):
                    key += '/uint'
                elif isinstance(value, wx.propgrid.ColourProperty):
                    key += '/color'
                elif isinstance(value, wx.propgrid.BoolProperty):
                    key += '/bool'
                elif isinstance(value, wx.propgrid.StringProperty):
                    key += '/string'
                else:
                    print('error')
                value = value.GetValueAsString()
                section[key] = value
                
        with open(file, 'w') as configfile:
            config.write(configfile)
    
    def ShowModal(self):
        super().ShowModal()
        self.SaveSettings('settings.ini')
        
if __name__ == '__main__':
    app = wx.App()
    s = Settings(None)
    print(GetSetting('New Document', 'Document Width', 80))
    s.ShowModal()
    print(GetSetting('New Document', 'Document Width', 80))
    s.Destroy()
    