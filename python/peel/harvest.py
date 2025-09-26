from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QMessageBox
import os.path
from PeelApp import cmd
from peel_devices import DownloadThread
import app_css
import app_const
from factory_widget import QtWidgetFactory

reg_harvest_dir = "HarvestDirectory"

class HarvestDialog(QtWidgets.QDialog):
    def __init__(self, settings, devices, parent):
        super(HarvestDialog, self).__init__(parent)

        # from peel.DEVICES - list of peel_device.PeelDevice objects
        self.devices = devices
        self.current_device = -1
        self.current_process = None
        self.total_copied = None
        self.total_failed = None
        self.total_skipped = None
        self.running = None
        self.work_threads = []
        self.has_download = False

        self.setWindowTitle(self.tr("Collect File"))

        if settings is None:
            self.settings = QtCore.QSettings(app_const.CompanyName, app_const.AppName)
        else:
            self.settings = settings

        layout = QtWidgets.QVBoxLayout()

        data_dir = self.settings.value(reg_harvest_dir)
        if data_dir is None or len(data_dir) == 0:
            data_dir = os.getcwd() + "\\data"
            self.settings.setValue(reg_harvest_dir, data_dir)

        # File Path Browser
        file_layout = QtWidgets.QHBoxLayout()
        self.path = QtWidgetFactory.create_QLineEdit(str(data_dir))

        # select folder button
        self.path_button = QtWidgetFactory.create_QPushButton(". . .", app_css.SheetStyle_PushButton, self.browse)
        self.path_button.setFixedSize(55, 22)
        
        file_layout.addWidget(self.path)
        file_layout.addWidget(self.path_button)
        file_layout.setSpacing(6)
        layout.addItem(file_layout)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Device List
        self.device_list = QtWidgets.QListWidget()
        self.device_list.setStyleSheet("background: #a6a6a6; color: black; border-radius: 3px;")
        for i in self.devices:
            item = QtWidgets.QListWidgetItem(i.name)
            item.setCheckState(QtCore.Qt.Checked)
            self.device_list.addItem(item)

        self.selected_devices = None

        self.splitter.addWidget(self.device_list)
        self.splitter.setSizes([1, 3])

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setStyleSheet("background: #a6a6a6; color: black;")
        self.splitter.addWidget(self.log)

        layout.addWidget(self.splitter)

        # InfoLabel
        self.info_label = QtWidgets.QLabel()
        self.info_label.setStyleSheet("color: #ccc")
        layout.addWidget(self.info_label)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("color: #ccc")
        layout.addWidget(self.progress_bar)

        # Buttons
        self.go_button = QtWidgetFactory.create_QPushButton(self.tr("Get Files"), app_css.SheetStyle_PushButton, self.go)
        self.close_button = QtWidgetFactory.create_QPushButton(self.tr("Close"), app_css.SheetStyle_PushButton, self.teardown)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.go_button)
        button_layout.addWidget(self.close_button)

        layout.addItem(button_layout)

        self.setLayout(layout)

        self.resize(500, 400)

        geo = self.settings.value("harvestGeometry")
        if geo:
            self.restoreGeometry(geo)

        sizes = self.settings.value("harvestSplitterGeometry")
        if sizes:
            self.splitter.setSizes([int(i) for i in sizes])

    def teardown(self):
        self.running = False
        cmd.writeLog("Harvest teardown\n")
        if self.current_process is not None:
            self.current_process.teardown()
        self.close()

    def __del__(self):
        cmd.writeLog("harvest closing\n")
        self.settings.setValue("harvestGeometry", self.saveGeometry())
        self.settings.setValue("harvestSplitterGeometry", self.splitter.sizes())
        self.teardown()

    def go(self):

        # Go button has been pressed, lets get started...
        self.has_download = True
        if self.go_button.text() == self.tr("Cancel"):
            self.running = False
            if self.current_process is not None:
                self.current_process.teardown()
            self.go_button.setText(self.tr("Get Files"))
            return

        self.selected_devices = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                self.selected_devices.append(i)

        if len(self.selected_devices) == 0:
            QMessageBox.warning(self, self.tr("Collect File"), self.tr("No devices to collect files. Please choose device which need."))
            return

        print("Queue: " + str(self.selected_devices))

        self.running = True
        self.total_copied = 0
        self.total_failed = 0
        self.total_skipped = 0
        self.current_device = -1

        path_input = self.path.text()
        if not os.path.exists(path_input):
            try:
                os.makedirs(path_input)
            except IOError:
                self.log("Harvest Error could not create directory: " + path_input)
                return

        # Start the copy loop
        self.next_device()

    def update_gui(self):
        if self.running:
            self.device_list.setEnabled(False)
            self.path.setEnabled(False)
            self.path_button.setEnabled(False)
            self.go_button.setText(self.tr("Cancel"))
        else:
            self.device_list.setEnabled(True)
            self.path.setEnabled(True)
            self.path_button.setEnabled(True)
            self.go_button.setText(self.tr("Get Files"))

    def log_message(self, message):
        self.log.appendPlainText(message)
        #print("> " + message)

    def is_done(self):
        return self.current_device >= len(self.selected_devices)

    def next_device(self):

        """ Called when we first start of when a device has finished processing """

        # current device is an index in self.selected_devices
        # self.selected devices is a list of indexes in self.device_list / self.devices

        if self.current_process is not None:
            print("Finished: " + str(self.current_process))

        print("Next device")

        self.current_device += 1

        self.update_gui()

        if not self.running:
            print("Not running")
            return

        if self.is_done():
            # Finished

            self.progress_bar.setValue(100)
            self.progress_bar.setRange(0, 100)
            self.info_label.setText("")

            #down_complete = self.tr('Download Complete')
            file_copied = self.tr('Files copied')
            file_skipped = self.tr('Files skipped')
            file_failed = self.tr('Files failed')
            msg = f"\n\n{file_copied}: %d\n{file_skipped}: %d\n{file_failed}: %d" % (self.total_copied, self.total_skipped, self.total_failed)
            self.log.appendPlainText(msg)
            self.running = False
            self.update_gui()

            QMessageBox.information(self, self.tr("Done"), msg)
            return

        # Un-highlight all the devices
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            item.setBackground(QtGui.QBrush())

        device_id = self.selected_devices[self.current_device]
        device = self.devices[device_id]

        print("Starting: %d" % self.current_device)
        print("Device:   %d" % device_id)

        path_input = self.path.text()
        path_temp = os.path.join(path_input, device.name)
        path_download = path_temp.replace('\\', '/')
        self.current_process = device.harvest(path_download)
        self.current_process.tick.connect(self.progress, QtCore.Qt.QueuedConnection)
        self.current_process.file_done.connect(self.file_done, QtCore.Qt.QueuedConnection)
        self.current_process.all_done.connect(self.next_device, QtCore.Qt.QueuedConnection)
        self.current_process.message.connect(self.log_message, QtCore.Qt.QueuedConnection)
        self.current_process.finished.connect(self.device_cleanup)
        self.work_threads.append(self.current_process)
        print(f"Starting download thread for {str(device)}")
        self.current_process.start()

        # Highlight the device we are about to start on
        item = self.device_list.item(device_id)
        item.setBackground(QtGui.QBrush(QtGui.QColor(167, 195, 244)))

    def device_cleanup(self):
        device_thread = self.sender()
        print("Thread done: " + str(device_thread))
        self.work_threads.remove(device_thread)

    def file_done(self, name, copy_state, error):
        if copy_state == DownloadThread.COPY_OK:
            copied = self.tr('COPIED')
            self.log.appendPlainText(f"{copied}: {name}")
            self.total_copied += 1
        elif copy_state == DownloadThread.COPY_SKIP:
            skipped = self.tr('SKIPPED')
            local_file_exists = self.tr('local file exists')
            self.log.appendHtml(f"<FONT COLOR=\"#444\">{skipped}: {name} ({local_file_exists})</FONT>")
            self.total_skipped += 1
        elif copy_state == DownloadThread.COPY_FAIL:
            failed = self.tr('FAILED')
            self.log.appendHtml(f"<FONT COLOR=\"#933\">{failed}: {name}: {str(error)}</FONT>")
            self.total_failed += 1

    def progress(self, minor):
        if self.current_device is None or self.is_done():
            print("Process Done")
            return

        if len(self.devices) == 0:
            return

        minor = float(minor) / float(len(self.devices))
        major = float(self.current_device) / float(len(self.selected_devices))
        self.progress_bar.setValue(int((major + minor) * 100.0))
        self.progress_bar.setRange(0, 100)
        device_name = self.devices[self.current_device].name
        if self.current_process.current_file is not None:
            self.info_label.setText(str(device_name) + ": " + str(self.current_process.current_file))

    def browse(self):
        d = self.settings.value(reg_harvest_dir)
        if d is None or len(d) == 0:
            d = os.getcwd() + "\\data"
            self.settings.setValue(reg_harvest_dir, d)

        ret = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr("Shoot Directory"), d)
        if ret:
            self.path.setText(ret)
            self.settings.setValue(reg_harvest_dir, ret)
