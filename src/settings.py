"""
settings.py
Bhupendra Aole
1/31/2020
"""

import wx
import wx.propgrid

import configparser

global_settings = {}

def InitSettings():
    global global_settings
    
    nos = wx.propgrid.UIntProperty('Number of Undos', value=100)
    nos.SetHelpString('[Restart Required]')
    
    global_settings['General'] = {'Number Of Undos': nos,
                           'Mirror Around Pixel Center': wx.propgrid.BoolProperty('Mirror around Pixel Center', value=False)}
                           
    global_settings['New Document'] = {'Document Width': wx.propgrid.UIntProperty('Document Width', value=80),
                                'Document Height': wx.propgrid.UIntProperty('Document Height', value=80),
                                'Pixel Size': wx.propgrid.UIntProperty('Pixel Size', value=5),
                                'Number Of Layers': wx.propgrid.UIntProperty('Number of Layers', value=2),
                                'First Layer Fill Color': wx.propgrid.ColourProperty('First Layer Fill Color', value=wx.WHITE)}
                                
    global_settings['Animation'] = {'FPS': wx.propgrid.UIntProperty('Frames/Second (FPS)', value=12),
                             'Total Frames': wx.propgrid.UIntProperty('Total Frames', value=12),
                             'Move To Next Frame': wx.propgrid.BoolProperty('Move To Next Frame when Key added', value=True),
                             'Hide Current Layer': wx.propgrid.BoolProperty('Hide Current Layer when Key added', value=False),
                             'Duplicate Layer': wx.propgrid.BoolProperty('Duplicate Current Layer when Key added', value=False),
                             'Insert Layer': wx.propgrid.BoolProperty('Insert New Layer when Key added', value=False)}

    model_prop = wx.propgrid.FileProperty('Model', value='')
    model_prop.SetAttribute("Wildcard", "SafeTensor files (*.safetensors)|*.safetensors")
    model_prop.SetHelpString('Path to the SDXL model file.')

    lora_prop = wx.propgrid.FileProperty('Lora', value='')
    lora_prop.SetAttribute("Wildcard", "SafeTensor files (*.safetensors)|*.safetensors")
    lora_prop.SetHelpString('Path to the LoRA file.')

    global_settings['AI'] = {'Model': model_prop,
                           'Lora': lora_prop}
                             
def GetSetting(section, property):
    global global_settings
    
    if section not in global_settings:
        return None
    if property not in global_settings[section]:
        return None
        
    return global_settings[section].get(property).GetValue()
    
def LoadSettings(file):
    global global_settings
    
    config = configparser.RawConfigParser()
    config.optionxform = lambda option: option
    config.read(file)
    
    for section in config.sections():
        for prop_name in config[section]:
            value = config[section][prop_name]
            if section not in global_settings:
                global_settings[section] = {}
            if not prop_name in global_settings[section]:
                global_settings[section][prop_name] = wx.propgrid.StringProperty(prop_name, value=value)
            else:
                prop = global_settings[section][prop_name]
                if isinstance(prop, wx.propgrid.FileProperty):
                    # Normalize path before setting it, to handle cross-platform settings files.
                    value = value.replace('\\', '/')
                prop.SetValueFromString(value)
    
def SaveSettings(file):
    global global_settings
    
    config = configparser.RawConfigParser()
    # case sensitive
    config.optionxform = lambda option: option
    # first read all
    config.read(file)
    # then update
    for sec, props in global_settings.items():
        if not sec in config:
            config[sec] = {}
        section = config[sec]
        for key, value in props.items():
            value = value.GetValueAsString()
            section[key] = value
            
    with open(file, 'w') as configfile:
        config.write(configfile)
    
class Settings(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Pixel Portal Settings", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizerb = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
        
        self.pgm = wx.propgrid.PropertyGridManager(self, size=wx.Size(400, 400),
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
        self.CreateGrid()
        
        self.pgm.SetDescBoxHeight(50)
        self.pgm.SetSplitterLeft()
        
        self.SetSizerAndFit(sizerb)
        
    def CreateGrid(self):
        global global_settings
        
        page = self.pgm.AddPage("General")
        for section, props in global_settings.items():
            page.Append(wx.propgrid.PropertyCategory(section))
            for prop, value in props.items():
                page.Append(value)
                
    def ShowModal(self):
        if super().ShowModal()==wx.ID_OK:
            SaveSettings('settings.ini')
            return True
        else:
            LoadSettings('settings.ini')
            return False
            
if __name__ == '__main__':
    app = wx.App()
    InitSettings()
    LoadSettings('settings.ini')
    s = Settings(None)
    print(GetSetting('New Document', 'First Layer Fill Color'))
    s.ShowModal()
    print(GetSetting('New Document', 'First Layer Fill Color'))
    s.Destroy()
    