from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox
import pkgutil, inspect
import importlib
import os
import logging, sys
from factory_widget import QtWidgetFactory

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler(sys.stdout))

try:
    from PeelApp import cmd
    import PeelApp
except ImportError:
    print("Could not import peel app - this script needs to run with peel Capture")

from peel_devices import device_util
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket


class BaseDeviceWidget(QtWidgets.QWidget):
    """ Base class used as a widget when adding a new device """
    def __init__(self, settings):
        super(BaseDeviceWidget, self).__init__()
        self.settings = settings
        self.click_flag = False
        self.info_text = ""

    def do_add(self):
        if self.click_flag:
            return False
        self.click_flag = True
        return True

    def set_info(self, msg):
        self.info_text = msg


class SimpleDeviceWidget(BaseDeviceWidget):
    """ A basic dialog for a device that has a name and an optional IP argument """
    def __init__(self, settings, title, has_host, has_port, has_remotetool_port, has_listen_ip, has_listen_port):
        super(SimpleDeviceWidget, self).__init__(settings)
        self.form_layout = QtWidgets.QFormLayout()
        self.title = title

        self.setWindowTitle(title)
        self.setObjectName(title)

        self.name = QtWidgetFactory.create_QLineEdit(settings.value(title + "Name", title))
        self.form_layout.addRow(self.tr("Name"), self.name)

        self.host = None
        self.port = None
        self.remotetool_port = None

        self.listen_ip = None
        self.listen_port = None
        self.set_capture_folder = None

        if has_host:
            self.host = QtWidgetFactory.create_QLineEdit_IP(settings.value(title + "Host", "127.0.0.1"))
            self.form_layout.addRow(self.tr("Address"), self.host)

        if has_port:
            self.port = QtWidgetFactory.create_QLineEdit_port(settings.value(title + "Port", ""))
            self.form_layout.addRow(self.tr("Port"), self.port)

        if has_remotetool_port:
            self.remotetool_port = QtWidgetFactory.create_QLineEdit_port(settings.value(title + "RemoteToolPort", ""))
            self.form_layout.addRow(self.tr("RemoteTool Port"), self.remotetool_port)

        if has_listen_ip:
            self.listen_ip = QtWidgetFactory.create_QComboBox_IP(settings.value(title + "ListenIp", self.tr("--all--")))
            self.form_layout.addRow(self.tr("Listen IP"), self.listen_ip)

        if has_listen_port:
            self.listen_port = QtWidgetFactory.create_QLineEdit_port(settings.value(title + "ListenPort", ""))
            self.form_layout.addRow(self.tr("Listen Port"), self.listen_port)

        self.setLayout(self.form_layout)

    def populate_from_device(self, device):
        """ populate the gui using data from the provided  device object
        """
        self.name.setText(device.name)
        if self.host is not None:
            self.host.setText(device.device_ip)

        if self.port is not None:
            self.port.setText(str(device.device_port))

        if self.remotetool_port is not None:
            self.remotetool_port.setText(str(device.remotetool_port))

        if self.listen_ip is not None:
            self.listen_ip.setCurrentText(device.listen_ip)

        if self.listen_port is not None:
            self.listen_port.setText(str(device.listen_port))

        # if self.set_capture_folder is not None:
        #     self.set_capture_folder.setChecked(device.set_capture_folder is True)

    def update_device(self, device, data=None):

        """ Set the device properties from values in the ui
            device is the object to modify, by calling reconfigure
            data has any kwargs for reconfigure to be passed on
         """

        name = self.name.text()

        if data is None:
            data = {}

        if self.host is not None:
            data['host'] = self.host.text()

        if self.port is not None:
            try:
                data['port'] = int(self.port.text())
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, self.tr("Error"), self.tr("Invalid port"))
                return False
            
        if self.remotetool_port is not None:
            try:
                data['remotetool_port'] = int(self.remotetool_port.text())
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, self.tr("Error"), self.tr("Invalid remote tool port"))
                return False

        if self.listen_ip is not None:
            data['listen_ip'] = self.listen_ip.ip()

        if self.listen_port is not None:
            try:
                data['listen_port'] = int(self.listen_port.text())
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, self.tr("Error"), self.tr("Invalid Listen Port"))
                return False

        if self.set_capture_folder is not None:
            data['set_capture_folder'] = self.set_capture_folder.isChecked()

        device.reconfigure(name, **data)
        return True

    def do_add(self):
        """ The ui is asking for the device to be added - validate and save the settings
            returns true if the data is valid.   If returning false it's a good idea to pop up
            a message to the user to say what was wrong """
        # if not super().do_add():
        #     return False
        
        device_name_text = self.name.text().strip()
        if device_name_text is None or len(device_name_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device name can't empty."))
            return False
        self.settings.setValue(self.title + "Name", device_name_text)
        
        if self.host is not None:
            device_ip_text = self.host.text().strip()
            if device_ip_text is None or len(device_ip_text) == 0:
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Device IP can't empty."))
                return False
            
            if not device_util.check_ip_address(device_ip_text):
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Device IP is invaild."))
                return False

            self.settings.setValue(self.title + "Host", device_ip_text)
            
        if self.port is not None:
            device_port_text = self.port.text().strip()
            if device_port_text is None or len(device_port_text) == 0:
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Device port can't empty."))
                return False
            
            if not device_util.check_ip_port(device_port_text):
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Device port is invaild. Range by 1~65535"))
                return False

            self.settings.setValue(self.title + "Port", device_port_text)
        
        if self.remotetool_port is not None:
            remotetool_port_text = self.remotetool_port.text().strip()
            if remotetool_port_text is None or len(remotetool_port_text) == 0:
                QMessageBox.warning(self, self.tr("Add device"), self.tr("RemoteTool port can't empty."))
                return False

            if not device_util.check_ip_port(remotetool_port_text):
                QMessageBox.warning(self, self.tr("Add device"), self.tr("RemoteTool port is invaild. Range by 1~65535"))
                return False

            self.settings.setValue(self.title + "RemoteToolPort", remotetool_port_text)
        
        # no need check.
        if self.listen_ip is not None:
            listen_ip_text = self.listen_ip.currentText()
            self.settings.setValue(self.title + "ListenIp", listen_ip_text)

        if self.listen_port is not None:            
            listen_port_text = self.listen_port.text().strip()
            if listen_port_text is None or len(listen_port_text) == 0:
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Listen port can't empty."))
                return False
            
            if not device_util.check_ip_port(listen_port_text):
                QMessageBox.warning(self, self.tr("Add device"), self.tr("Listen port is invaild. Range by 1~65535"))
                return False

            self.settings.setValue(self.title + "ListenPort", listen_port_text)
        
        if self.set_capture_folder is not None:
            self.settings.setValue(self.title + "SetCaptureFolder", self.set_capture_folder.isChecked())

        return True


class PeelDeviceBase(QtCore.QObject):

    """ Base class for all devices """

    def __init__(self, name, parent=None):
        super(PeelDeviceBase, self).__init__(parent)
        self.name = name
        self.device_id = None
        self.plugin_id = -1
        self.enabled = True

    def __str__(self):
        return self.name

    def set_enabled(self, value):
        """ Main app calls this to enable / disable the device.  Default behavior is to set self.enabled """
        self.enabled = value

    @staticmethod
    def device():
        """ returns the string name for this device type """
        raise NotImplementedError

    def as_dict(self):
        """ Returns the constructor fields and values for this instance.  Used to
            recreate the instance between application sessions """
        raise NotImplementedError

    def reconfigure(self, name, **kwargs):
        """ Called by the SimpleDevice dialog to set the device settings.  Does not
            need to be overridden if a different dialog is being used.
            The kwargs need to match the parameters specified in SimpleDeviceWidget
            constructor, ie if has_host is True, kwargs will have a "host" parameter. """
        raise NotImplementedError

    def teardown(self):
        """ Called when the app is shutting down - tell all threads to stop and return """
        raise NotImplementedError

    def thread_join(self):
        """ Called when the app is shutting down - block till threads are stopped """
        raise NotImplementedError

    def command(self, command, argument):
        """
        Command, Argument may be:

        - record *takename*
        - play *takename* or "" for last recorded
        - stop
        - transport *stop | next | prev*
        - notes *note* - sent when the notes are changed, relevant for the last take
        - timecode *timecode* - called when recording starts
        - selectedTake *take* - sent when a user selects a take, passes the take name

        The following are called when take information needs to be updated, ie the take name has changed or when
        recording starts:

        - takeName *n*
        - shotName *name*
        - shotTag *tag*
        - takeNumber *n*
        - description *description*
        - takeId *id*

        """
        raise NotImplementedError

    def get_state(self):
        """ devices should return "OFFLINE", "ONLINE", "RECORDING", "PLAYING" or "ERROR" """
        raise NotImplementedError

    def get_info(self):
        """ Return the text to put in the main ui next to the device name """
        return ""

    def device_ref(self, state=None, info=None):
        """ Create a PeelApp.Device() object that contains the information needed
            to update the main ui.  The Device() object is implemented in c++ to
            make it easier to pass around inside the main app.

            This function does not need to be overridden for subclasses, the default
            should be okay for most uses.

            See the note in update_state() about populating state and info values when
            calling this from get_state() or get_info()
        """

        print(f"ref {self.name} {len(self.list_takes())}")

        if state is None:
            state = self.get_state()
        if info is None:
            info = self.get_info()

        device = PeelApp.cmd.newDevice()  # CPP class from parent app
        device.deviceId = self.device_id
        device.pluginId = self.plugin_id
        device.name = self.name
        device.status = state
        device.info = info
        device.enabled = self.enabled
        device_address = ''
        device_dict = self.as_dict()
        if 'device_ip' in device_dict and 'device_port' in device_dict:
            device_address = device_dict['device_ip'] + ':' + str(device_dict['device_port'])

        device.address = device_address

        # Get the list of files the device says it has recorded.  This data is used in the
        # take table of the main ui to show how many files are recorded for each take.
        try:
            device.takes = self.list_takes()
        except NotImplementedError:
            device.takes = []

        # print(device.name, device.status)
        return device

    def update_state(self, state=None, info=None):
        """ Call this to push a status update to the main app.

            Note that device_ref() may call get_state() and get_info() for the device,
            so it's important that any calls to this function inside of get_state() or
            get_info() populate state and info fields to avoid a loop/lockup.

            This function is usually called in response to a device thread or socket
            changing state or having new info to update in the ui to avoid the need for
            polling devices.
        """
        if self.device_id is None:
            # print("No device id")
            return
        cmd.writeLog(f"State: {self.name} {state} {info}\n")
        cmd.updateDevice(self.device_ref(state, info))

    def GetTakeInfo(self):
        return cmd.GetTakeInfo()

    def HighLightNotes(self, row):
        return cmd.HighLightNotes(row)

    def UpdateActionInfo(self, row, startFrame, endFrame):
        return cmd.UpdateActionInfo(row, startFrame, endFrame)

    @staticmethod
    def dialog(settings):
        """ Static method to create the UI for this device.  It should return
            an blank instance of this device type.
        """
        raise NotImplementedError

    @staticmethod
    def dialog_callback(widget):
        """ Static method to populate the device from the creation widget """
        raise NotImplementedError

    def edit(self, settings):
        """ Create the UI to edit this device.  It should return an populated
            instance of this device object.
        """
        raise NotImplementedError

    def has_harvest(self):
        """ Return True if the device supports the ability to download files from
            the device to local storage
        """
        return False

    def harvest(self, directory):
        """ Download the takes to the local storage directory
        """
        raise NotImplementedError

    def list_takes(self):
        """ list the take files currently on the device
        """
        raise NotImplementedError

    def data_directory(self):
        """ returns the current data directory for this device """
        return cmd.getDataDirectory() + "/" + self.name
    
    def start_services(self):
        pass


class DeviceCollection(QtCore.QObject):
    def __init__(self, parent=None):
        super(DeviceCollection, self).__init__(parent)
        self.devices = []
        self.current_id = 0

    @staticmethod
    def all_classes():
        for device_module in pkgutil.iter_modules([os.path.split(__file__)[0]]):
            dm = importlib.import_module("peel_devices." + device_module.name)
            for name, klass in inspect.getmembers(dm, inspect.isclass):
                if issubclass(klass, PeelDeviceBase):
                    try:
                        klass.device()
                    except NotImplementedError:
                        continue
                    yield klass

        # Search for valid classes in peel_user_devices module, if it exists
        try:
            dm = importlib.import_module("peel_user_devices")
            for i in pkgutil.iter_modules(dm.__path__):
                klass = importlib.import_module("peel_user_devices." + i.name)
                for name, klass in inspect.getmembers(klass, inspect.isclass):
                    if issubclass(klass, PeelDeviceBase):
                        try:
                            klass.device()
                        except NotImplementedError:
                            continue
                        yield klass

        except ModuleNotFoundError:
            pass

    def add_device(self, device):

        print("Adding Device")

        if not isinstance(device, PeelDeviceBase):
            raise ValueError("Not a device while adding: " + str(device))
        
        if self.is_device_existed(device):
            return False

        device.device_id = self.current_id
        self.current_id += 1
        self.devices.append(device)

        print("Added device: %s (%s)" % (device.name, device.device()))
        return True

    # 判断新加的设备与已存在设备配置是否相同
    def is_device_existed(self, new_device):
        for d in self.devices:
            if self.is_same_device(d, new_device):
                return True
        return False
    
    def is_same_device(self, device1, device2):
        if device1.name == device2.name:
            return True
        
        if device1.device_ip == device2.device_ip and device1.device_port == device2.device_port:
            return True
        
        if hasattr(device1, 'remotetool_port') and hasattr(device2, 'remotetool_port'):
            if device1.device_ip == device2.device_ip and device1.remotetool_port == device2.remotetool_port:
                return True

        if hasattr(device1, 'listen_port') and hasattr(device2, 'listen_port'):
            if device1.listen_ip == device2.listen_ip and device1.listen_port == device2.listen_port:
                return True
            
        return False

    def remove_all(self):
        for d in self.devices:
            d.teardown()
        self.devices = []

    def remove(self, device_id):
        for d in self.devices:
            if d.device_id == device_id:
                d.teardown()
                self.devices.remove(d)
                break

    def start_services(self):
        for d in self.devices:
            d.start_services()

    def update_all(self):
        cmd.setDevices([i.device_ref() for i in self.devices])

    def teardown(self):
        for d in self.devices:
            try:
                d.teardown()
            except NotImplementedError as e:
                print("Incomplete device  (teardown): " + d.name)

    def get_data(self):
        data = []
        for d in self.devices:
            try:
                data.append((d.device(), d.as_dict()))
            except NotImplementedError as e:
                print("Incomplete device (as_dict): " + d.name)

        return data
    
    def get_device_config_data(self):
        """获取设备配置数据（不包含takes）"""
        data = []
        for d in self.devices:
            try:
                device_dict = d.as_dict()
                # 移除takes数据
                if 'takes' in device_dict:
                    device_dict = device_dict.copy()
                    del device_dict['takes']
                data.append((d.device(), device_dict))
            except NotImplementedError as e:
                print("Incomplete device (as_dict): " + d.name)

        return data

    def unique_name(self, device_name):
        name = device_name
        i = 1
        while name in [i.name for i in self.devices]:
            name = device_name + str(i)
            i += 1
        return name

    def from_id(self, id):
        for d in self.devices:
            if d.device_id == id:
                return d

    def __len__(self):
        return len(self.devices)

    def __getitem__(self, item):
        return self.devices[item]

    def has_device(self, device_name, name):
        for i in self.devices:
            if i.device() == device_name and i.name == name:
                return True

        return False

    def load_json(self, data, mode):
        if mode == "replace":
            self.remove_all()

        klass = dict([(i.device(), i) for i in self.all_classes()])
        if "devices" in data:
            for name, device_data in data["devices"]:

                if not isinstance(device_data, dict):
                    print("Not a dict while reading device data:" + str(device_data))
                    continue

                if name not in klass:
                    print("Could not find device class for: " + name)
                    continue

                if mode == "merge" and self.has_device(name, device_data["name"]):
                    continue

                try:
                    d = klass[name](**device_data)
                    self.add_device(d)
                except TypeError as e:
                    print("Error recreating class: " + str(name))
                    print(str(e))
                    print(str(device_data))


class FileItem(object):
    def __init__(self, remote_project, remote_file, local_project, local_file):
        self.remote_project = remote_project
        self.remote_file = remote_file
        self.local_project = local_project
        self.local_file = local_file
        self.file_size = None   
        self.data_size = None
        self.error = None
        self.complete = False
        
class DownloadThread(QtCore.QThread):

    tick = QtCore.Signal(float)  # 0.0 - 1.0 progress done
    file_done = QtCore.Signal(str, int, str)  # Name, CopyState, error string
    all_done = QtCore.Signal()
    message = QtCore.Signal(str)

    COPY_FAIL = 0
    COPY_OK = 1
    COPY_SKIP = 2

    STATUS_NONE = 0
    STATUS_RUNNING = 1
    STATUS_STOP = 2
    STATUS_FINISHED = 3

    def __init__(self):
        super(DownloadThread, self).__init__()
        self.status = self.STATUS_NONE
        self.current_file = None

    def __del__(self):
        self.terminate()

    def log(self, message):
        self.message.emit(message)

    def teardown(self):
        cmd.writeLog(f"Teardown {str(self)}\n")
        self.status = self.STATUS_STOP
        self.wait(1000)

    def set_finished(self):
        self.status = self.STATUS_FINISHED
        self.tick.emit(0.0)
        self.all_done.emit()

    def set_started(self):
        self.status = self.STATUS_RUNNING
        self.tick.emit(0.0)

    def set_current(self, value):
        self.current_file = value

    def file_ok(self, name):
        self.file_done.emit(name, self.COPY_OK, None)

    def file_fail(self, name, err):
        self.file_done.emit(name, self.COPY_FAIL, err)
        
    def file_skip(self, name):
        self.file_done.emit(name, self.COPY_SKIP, None)

    def is_running(self):
        return self.status is self.STATUS_RUNNING
