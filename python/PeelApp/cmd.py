from PySide6.QtWidgets import QApplication
#from capture_device import CaptureDevice

g_mainWnd = None

class CaptureDevice:  #(QtCore.QObject)
    def __init__(self, name='Capture Device'):
        #super(CaptureDevice, self).__init__(parent)
        self.name = name
        self.deviceId = None
        self.pluginId = -1
        self.enabled = True
        self.status = None
        self.info = ""
        self.address = ''
        self.takes = []

    def set_enabled(self, value):
        """ Main app calls this to enable / disable the device.  Default behavior is to set self.enabled """
        self.enabled = value

    def __json__(self):
        return {
            "name": self.name,
            "deviceId": self.deviceId,
            "pluginId": self.pluginId,
            "enabled": self.enabled,
            "status": self.status,
            "info": self.info,
            "address": self.address
        }


#用来保存Json文件
def setDeviceData(json_str):
    print(json_str)

def getMainWindow():
    if g_mainWnd is not None:
        return g_mainWnd
    else:
        return QApplication.instance().topLevelWidgets()[0]
    
def getDataDirectory():
    return r"D:\CMCapture_Downloads"

def newDevice():
    return CaptureDevice()

def writeLog(log):
    print(log)

def updateDevice(device):
    # global g_mainWnd
    # if g_mainWnd is not None:
    #     QMessageBox.warning(g_mainWnd, "cmd", 'Update Device: ' + device.name + ' - ' + device.status + ' - ' + device.info)
    # else:
    # print('Update Device: ' + device.name + ' - ' + device.status + ' - ' + device.info)
    if g_mainWnd is not None:
        g_mainWnd.updateDevice(device)

def GetTakeInfo():
    if g_mainWnd is not None:
        return g_mainWnd.get_takelist_table()

def HighLightNotes(row):
    if g_mainWnd is not None:
        g_mainWnd.highlight_signal.emit(row)

def UpdateActionInfo(row, startFrame, endFrame):
    if g_mainWnd is not None:
        g_mainWnd.UpdateActionInfo(row, startFrame, endFrame)

def setDevices(devices):
    for d in devices:
        print('set device: ' + d.name)

    if g_mainWnd is not None:
        g_mainWnd.setDevices(devices)

#TODO
def getCurrentFile():
    return r"c:\abc.json"
