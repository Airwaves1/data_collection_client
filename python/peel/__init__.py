from peel_devices import DeviceCollection
from peel import harvest
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import QCoreApplication
from PeelApp import cmd
import app_const
from factory_widget import QtWidgetFactory

try:
    import peel_user_startup
except ImportError:
    peel_user_startup = None

import os.path
import json


DEVICES = DeviceCollection()
SUBJECTS = {}
SETTINGS = None


def startup():
    global SETTINGS
    print("Starting device services - Python api v0.1")

    SETTINGS = QtCore.QSettings(app_const.CompanyName, app_const.AppName)

    if peel_user_startup is not None:
        peel_user_startup.startup()

def teardown():
    print("Shutting down")
    # DEVICES.teardown()
    DEVICES.remove_all()

def set_device_data():
    """ Pass the json data for the devices to the main app so it can include it
    when saving the peelcap file at regular intervals (e.g. when hitting record/stop) """
    global DEVICES
    cmd.setDeviceData(json.dumps(DEVICES.get_data()))

def get_devices_data():
    global DEVICES
    return DEVICES.get_data()

def get_device_config_data():
    """获取设备配置数据（不包含takes）"""
    global DEVICES
    return DEVICES.get_device_config_data()

def get_devices_count():
    return len(DEVICES)

def get_settings():
    global SETTINGS
    return SETTINGS

def load_data(file_path, mode):

    """ Load the device data from a .peelcap file """

    print("Loading Json file: " + file_path + " with mode: " + mode)

    if not os.path.isfile(file_path):
        print("Could not find json file for devices: " + file_path)
        return

    with open(file_path, encoding="utf8") as fp:
        DEVICES.load_json(json.load(fp), mode)
    
    DEVICES.start_services()
    DEVICES.update_all()

class AddDeviceDialog(QtWidgets.QDialog):

    """ The add device dialog - swaps the middle panel out for each device setting """

    def __init__(self, parent):
        super(AddDeviceDialog, self).__init__(parent)
        self.setWindowTitle(app_const.AppName)
        item_select = self.tr("--select--")
        device_candidate = [item_select]

        self.device_list = []
        self.current_widget = None
        self.current_device = None

        self.device_list = sorted(DeviceCollection.all_classes(), key=lambda k: k.device())
        for klass in self.device_list:
            device_candidate.append(klass.device())

        self.combo = QtWidgetFactory.create_QComboBox(device_candidate, item_select)
        self.combo.currentIndexChanged.connect(self.device_select)

        self.confirm_button = QtWidgets.QPushButton("Create")
        self.confirm_button.pressed.connect(self.accept)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.top_widget = QtWidgets.QWidget()
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_widget.setLayout(self.top_layout)

        label = QtWidgets.QLabel(self.tr("New Device:"))
        label.setStyleSheet("font-size: 11pt;color:white;")
        self.top_layout.addWidget(label)
        self.top_layout.addWidget(self.combo)
        self.top_layout.addStretch(1)
        self.top_widget.setStyleSheet("background: #111")

        self.device_widget = QtWidgets.QWidget()
        self.device_layout = QtWidgets.QHBoxLayout()
        self.device_widget.setLayout(self.device_layout)

        self.info_widget = QtWidgets.QTextBrowser()
        self.info_widget.setOpenExternalLinks(True)
        self.info_widget.setStyleSheet("background: #a6a6a6; color: #000; ")
        self.info_widget.document().setDefaultStyleSheet("a { color: #ccf}")

        self.low_widget = QtWidgets.QWidget()
        self.low_layout = QtWidgets.QHBoxLayout()
        self.low_widget.setLayout(self.low_layout)
        self.low_widget.setStyleSheet("background: #111")

        self.cancel_button = QtWidgets.QPushButton(self.tr("Cancel"))
        self.cancel_button.setStyleSheet("color: white; background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010); ")
        self.cancel_button.pressed.connect(self.do_close)
        self.low_layout.addWidget(self.cancel_button)

        self.low_layout.addStretch(1)

        self.add_button = QtWidgets.QPushButton(self.tr("Add"))
        self.add_button.setStyleSheet("color: white; background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010); ")
        self.add_button.released.connect(self.do_add)
        self.low_layout.addWidget(self.add_button)

        self.main_layout.addWidget(self.top_widget, 0)
        self.main_layout.addWidget(self.device_widget, 1)
        self.main_layout.addWidget(self.info_widget, 1)
        self.main_layout.addWidget(self.low_widget, 0)

        self.resize(350, 400)

        self.setLayout(self.main_layout)

        self.show()

    def device_select(self, index):
        if index == 0:
            return

        ret = self.device_widget.layout().takeAt(0)
        if ret is not None:
            ret.widget().deleteLater()

        self.current_device = self.device_list[index-1]
        self.current_widget = self.current_device.dialog(SETTINGS)
        if self.current_widget is None:
            raise RuntimeError("Invalid widget from device")
        self.device_widget.layout().addWidget(self.current_widget)
        self.info_widget.setHtml(self.current_widget.info_text)

    def do_add(self):
        if self.current_widget is None:
            return

        device = self.current_device.dialog_callback(self.current_widget)
        if not device:
            # input invaild value, don't close dialog
            print("Device did not return anything")
            return
        else:
            print("Adding: " + str(device))
            
            result_add = DEVICES.add_device(device)
            if result_add == False:
                msg = self.tr("Added Device config is conflict: ")
                QMessageBox.warning(self, self.tr("Add Device"), msg + device.name)
                return
            
            device.start_services()

            DEVICES.update_all()

        self.close()
        self.deleteLater()

    def do_close(self):
        self.close()
        self.deleteLater()

    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Enter or evt.key() == QtCore.Qt.Key_Return:
            return
        super().keyPressEvent(evt)


class EditDeviceDialog(QtWidgets.QDialog):

    """ The add device dialog - swaps the middle panel out for each device setting """

    def __init__(self, parent, n):
        super(EditDeviceDialog, self).__init__(parent)
        self.setWindowTitle("CMCapture")
        self.device_index = n
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.edit_widget = DEVICES[n].edit(SETTINGS)
        if self.edit_widget is None:
            raise RuntimeError("Invalid widget")

        layout.addWidget(self.edit_widget)
        button = QtWidgets.QPushButton(self.tr("Okay"))
        button.pressed.connect(self.do_edit)
        layout.addWidget(button)

        self.show()

    def do_edit(self):
        if not DEVICES[self.device_index].edit_callback(self.edit_widget):
            return

        DEVICES.update_all()

        self.close()
        self.deleteLater()


    def do_close(self):
        self.close()
        self.deleteLater()

    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Enter or evt.key() == QtCore.Qt.Key_Return:
            return
        super().keyPressEvent(evt)

DIALOG_LOCK = False

def add_device():

    """ Called by main window to create a new device """

    global DIALOG_LOCK
    if DIALOG_LOCK:
        return

    DIALOG_LOCK = True
    d = AddDeviceDialog(cmd.getMainWindow())
    d.setModal(True)
    d.exec()
    DIALOG_LOCK = False


def device_info(n):

    """ Called when the user double clicks on an item.  Id of the item is passed.
        Add functionality to edit the device here """
    modify = False
    global DEVICES

    if n < 0 or n >= len(DEVICES):
        return

    global DIALOG_LOCK
    if DIALOG_LOCK:
        return

    DIALOG_LOCK = True
    d = EditDeviceDialog(cmd.getMainWindow(), n)
    d.setModal(True)
    result = d.exec()

    if result == QDialog.Accepted:
        modify = True
    DIALOG_LOCK = False

    return modify

def set_device_enable(n, state):
    global DEVICES

    if n < 0 or n >= len(DEVICES):
        return

    DEVICES[n].set_enabled(state)
    DEVICES.update_all()


def set_subject(name, enabled):
    global DEVICES
    for device in DEVICES:
        #if isinstance(device, shogun.ViconShogun):
        device.set_subject(name, enabled)


def delete_device(device_name):
    """ Called by the main app to delete a device instance, by device name (key) """
    global DEVICES
    DEVICES.remove(device_name)
    DEVICES.update_all()


def command(command, argument):
    """ Main app sending a command - passed to device.command()
    Command: Argument
    transport: stop, next, prev, play
    record: takeName
    stop
    """

    global DEVICES
    for device in DEVICES:
        if device.enabled:
            device.command(command, argument)

    # This is causing a weird blackout issue:
    # DEVICES.update_all()


def show_harvest():
    """ Copy the files from the devices to a local directory """
    harvest_devices = [ d for d in DEVICES if d.has_harvest() ]
    if len(harvest_devices) == 0:
        title = QCoreApplication.translate("peel", "Harvest")
        msg = QCoreApplication.translate("peel", "No supported devices available")
        QMessageBox.warning(cmd.getMainWindow(), title, msg)
        return
    h = harvest.HarvestDialog(SETTINGS, harvest_devices, cmd.getMainWindow())
    h.exec_()
    h.deleteLater()
    return h.has_download

def do_stop():
    """ Called shortly after stop event to update devices """
    global DEVICES
    DEVICES.update_all()
