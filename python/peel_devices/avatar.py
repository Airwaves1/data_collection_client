from pythonosc import dispatcher, osc_server, udp_client
from peel_devices import PeelDeviceBase, DownloadThread, FileItem, BaseDeviceWidget
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox
import threading, socket, struct
from PySide6.QtCore import QCoreApplication
import os
import os.path

from . import common
from . import device_util
from PeelApp import cmd
from factory_widget import QtWidgetFactory

# CMAvatar默认IP
default_avatar_ip = "127.0.0.1"
# CMAvatar默认端口
default_avatar_port = 12300
# RemoteTool默认端口
defualt_remotetool_port = 12700

# CMCapture默认IP
default_listener_ip = "127.0.0.1"
# CMCapture默认端口
default_listener_port = 12100

class AddAvatarWidget(BaseDeviceWidget):
    def __init__(self, settings):
        super(AddAvatarWidget, self).__init__(settings)
        form_layout = QtWidgets.QFormLayout()

        self.setStyleSheet("Label: { color: black}")
        self.setWindowTitle(self.tr("Add CMAvatar Client"))

        msg = self.tr('<P>CMAvatar is a great motion capture program!</P>')
        self.set_info(msg)

        self.name = QtWidgetFactory.create_QLineEdit(settings.value("CMAvatarName", "CMAvatar"))
        form_layout.addRow(self.tr("Name"), self.name)

        self.device_ip = QtWidgetFactory.create_QLineEdit_IP(settings.value("CMAvatarIp", default_avatar_ip))
        form_layout.addRow(self.tr("Address"), self.device_ip)

        self.device_port = QtWidgetFactory.create_QLineEdit_port(settings.value("CMAvatarPort", str(default_avatar_port)))
        form_layout.addRow(self.tr("Port"), self.device_port)

        self.remotetool_port = QtWidgetFactory.create_QLineEdit_port(settings.value("CMAvatarRemoteToolPort", str(defualt_remotetool_port)))
        form_layout.addRow(self.tr("RemoteTool Port"), self.remotetool_port)

        self.listen_ip = QtWidgetFactory.create_QComboBox_IP(settings.value("CMAvatarListenIp", self.tr("--all--")))
        form_layout.addRow(self.tr("Listen IP"), self.listen_ip)

        self.listen_port = QtWidgetFactory.create_QLineEdit_port(settings.value("CMAvatarListenPort", str(default_listener_port)))
        form_layout.addRow(self.tr("Listen Port"), self.listen_port)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.device_ip.setText(device.device_ip)
        self.device_port.setText(str(device.device_port))
        self.remotetool_port.setText(str(device.remotetool_port))
        self.listen_ip.setCurrentText(device.listen_ip)
        self.listen_port.setText(str(device.listen_port))

    def update_device(self, device):
        # Update the device with the data in the text fields
        try:
            device.name = self.name.text()
            device.device_ip = self.device_ip.text()
            device.device_port = int(self.device_port.text())
            device.remotetool_port = int(self.remotetool_port.text())
            device.listen_ip = self.listen_ip.ip()
            device.listen_port = int(self.listen_port.text())
            device.start_services()
        except ValueError:
            QMessageBox.warning(self, "Error", self.tr("Error"), self.tr("Invalid port"))

    def do_add(self):
        # if not super().do_add():
        #     return False

        device_name_text = self.name.text().strip()
        if device_name_text is None or len(device_name_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device name can't empty."))
            return False
        
        device_ip_text = self.device_ip.text().strip()
        if device_ip_text is None or len(device_ip_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device IP can't empty."))
            return False
        
        if not device_util.check_ip_address(device_ip_text):
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device IP is invaild."))
            return False

        device_port_text = self.device_port.text().strip()
        if device_port_text is None or len(device_port_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device port can't empty."))
            return False
        
        if not device_util.check_ip_port(device_port_text):
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Device port is invaild. Range by 1~65535"))
            return False
        
        remotetool_port_text = self.remotetool_port.text().strip()
        if remotetool_port_text is None or len(remotetool_port_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("RemoteTool port can't empty."))
            return False
        
        if not device_util.check_ip_port(remotetool_port_text):
            QMessageBox.warning(self, self.tr("Add device"), self.tr("RemoteTool port is invaild. Range by 1~65535"))
            return False

        # no need check.
        listen_ip_text = self.listen_ip.currentText()
        
        listen_port_text = self.listen_port.text().strip()
        if listen_port_text is None or len(listen_port_text) == 0:
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Listen port can't empty."))
            return False
        
        if not device_util.check_ip_port(listen_port_text):
            QMessageBox.warning(self, self.tr("Add device"), self.tr("Listen port is invaild. Range by 1~65535"))
            return False

        # save it to register
        self.settings.setValue("CMAvatarName", device_name_text)
        self.settings.setValue("CMAvatarIp", device_ip_text)
        self.settings.setValue("CMAvatarPort", device_port_text)
        self.settings.setValue("CMAvatarRemoteToolPort", remotetool_port_text)
        self.settings.setValue("CMAvatarListenIp", listen_ip_text)
        self.settings.setValue("CMAvatarListenPort", listen_port_text)

        return True


class CMAvatar(PeelDeviceBase):

    def __init__(self,
                 name,
                 device_ip,
                 device_port=default_avatar_port,
                 remotetool_port = defualt_remotetool_port,
                 listen_ip=default_listener_ip,
                 listen_port=default_listener_port,
                 takes=None):

        super(CMAvatar, self).__init__(name)
        self.device_ip = device_ip
        self.device_port = device_port
        self.remotetool_port = remotetool_port
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.server = None
        self.thread = None
        self.takeNumber = None
        self.thermals = None
        self.info = ""
        self.state = "OFFLINE"
        # CMAvatar client
        self.client = None
        # RemoteTool client
        self.clientTransform = None
        self.ping_timer = None
        
        self.got_response = False

        if takes is None:
            self.takes = {}
        else:
            self.takes = takes
        self.current_take = None

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.set_default_handler(self.callback, True)

        # self.start_services()

    def start_services(self):

        self.ping_timer = QtCore.QTimer()
        self.ping_timer.timeout.connect(self.ping_timeout)
        self.ping_timer.setInterval(common.timeout_heartbeat)
        self.ping_timer.setSingleShot(False)

        self.ping_timer.start()

        if self.thread is not None and self.server is not None:
            print("Stopping current CMAvatar OSC Server")
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.thread = None
            print("OSC server stopped")

        print("Creating udp client")

        # 伽利略系统接收端口: 12001
        self.client = udp_client.SimpleUDPClient(self.device_ip, self.device_port)
        # 文件传输
        self.clientTransform = udp_client.SimpleUDPClient(self.device_ip, self.remotetool_port)

        try:
            # 伽利略系统发送端口: 12001
            print("Starting OSC Server: " + str(self.listen_ip) + ":" + str(self.listen_port))
            self.server = osc_server.ThreadingOSCUDPServer((self.listen_ip, self.listen_port), self.dispatcher)
        except IOError as e:
            print("Could not start OSC Server: " + str(e))
            self.state = "ERROR"
            self.info = "OSC Error"
            return

        print("Starting CMAvatar thread")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

        # 心跳
        self.client.send_message(common.cmd_req_heatbeat, (self.listen_ip, self.listen_port))
        self.clientTransform.send_message(common.cmd_req_heatbeat, (self.listen_ip, self.listen_port))

        self.state = "OFFLINE"
        self.update_state(self.state, "")

    @staticmethod
    def device():
        return "CMAvatar"

    def as_dict(self):
        return {
                'name': self.name,
                'device_ip': self.device_ip,
                'device_port': self.device_port,
                'remotetool_port': self.remotetool_port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'takes': self.takes
                }

    def teardown(self):
        if self.ping_timer is not None:
            self.ping_timer.stop()
            self.ping_timer.timeout.disconnect(self.ping_timeout)
            self.ping_timer = None

        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        return

    def command(self, command, arg):

        print(f"{command} {arg}")

        if command == "takeNumber":
            self.takeNumber = int(arg)

        if command == "record":
            if self.takeNumber is None:
                self.state = "ERROR"
                self.info = "No take#"
                raise RuntimeError("Take number not set while starting recording")

            # int + char* + char* + char*
            #   参数1：表示开始/录制
            #   参数2：表示生成报告的路径和名称
            #   参数3：表示导出bvh的路径和名称
            #   参数4：表示token
            self.current_take = arg
            self.client.send_message(common.cmd_req_record, (self.listen_ip, self.listen_port, True, self.current_take))
            self.clientTransform.send_message(common.cmd_req_record, (self.listen_ip, self.listen_port, True, self.current_take))

        if command == "stop":
            self.current_take = arg
            self.client.send_message(common.cmd_req_record, (self.listen_ip, self.listen_port, False, self.current_take))
            self.clientTransform.send_message(common.cmd_req_record, (self.listen_ip, self.listen_port, False, self.current_take))

        if command == "Export":
            exportPath = arg
            takeTable = self.GetTakeInfo()
            for row in range(takeTable.rowCount()):
                item = takeTable.item(row, 0)  # 第一列，列号为0
                comboBox = takeTable.cellWidget(row, 6)
                if comboBox.currentText() != "NG":
                    self.client.send_message(common.cmd_req_export, (self.listen_ip, self.listen_port, exportPath, item.text()))
                    self.clientTransform.send_message(common.cmd_req_export, (self.listen_ip, self.listen_port, exportPath, item.text()))

    def callback(self, address, command, *args):

        cmd.writeLog(f"{self.name} callback from {address}  {command}  {args}\n")

        self.got_response = True
        # bool + char* + char*
        #   参数1：表示开始录制操作是否成功
        #   参数2：返回失败时的对应消息（成功时为空）
        #   参数3：表示token
        if command == common.cmd_rep_record_start:
            record_result = args[0]
            # record_msg = args[1]
            # record_take = args[2]
            
            if record_result:
                self.state = "RECORDING"
            else:
                self.state = "REC ERR"
            
            self.push_state()
            return
        
        if command == common.cmd_rep_record_stop:

            self.state = "ONLINE"
            self.push_state()

            # remote project path, remote files, local files
            print("Adding " + str(self.current_take) + " " + str(args))
            proj_fullPath = ""
            remote_files = []
            files_cnt = len(args)
            if files_cnt > 0:
                proj_fullPath = args[0]
                remote_files.extend(args[1:])

            if self.current_take:
                self.takes[self.current_take] = { 'remote_project': proj_fullPath, 'remote_files' : remote_files, 'local_files': []}

            return

        if command == common.cmd_rep_heatbeat:
            self.thermals = args
            last_state = self.state
            if self.state == "RECORDING":
                return
            self.state = "ONLINE"

            if last_state != self.state:
                self.push_state()

        if command == common.cmd_rep_record_stage:
            stage = args[0]
            startFrame = args[1]
            endFrame = args[2]
            self.HighLightNotes(stage)
            self.UpdateActionInfo(stage, startFrame, endFrame)

    def push_state(self):

        ret = []

        if self.takes is not None and len(self.takes) > 0:
            ret.append("Clips: %d" % len(self.takes))

        self.info = " / ".join(ret)
        self.update_state(self.state, self.info)

    def ping_timeout(self):
        if not self.got_response:
            self.state = "OFFLINE"
            self.update_state(self.state, "")

        self.got_response = False

        self.client.send_message(common.cmd_req_heatbeat, (self.listen_ip, self.listen_port))
        self.clientTransform.send_message(common.cmd_req_heatbeat, (self.listen_ip, self.listen_port))

    def get_state(self):
        if not self.enabled:
            self.ping_timer.stop()
            return "OFFLINE"

        return self.state

    def get_info(self):
        return self.info

    def __str__(self):
        return self.name

    def has_harvest(self):
        return True

    def harvest(self, directory):
        thread = CMAvatarDownloadThread(self, directory)
        for take, remote_item in self.takes.items():
            if not remote_item:
                continue

            try:
                remote_project = remote_item['remote_project']
                remote_files = remote_item['remote_files']
                local_files = remote_item['local_files']
                local_files.clear()

                for remote_file in remote_files:
                    # Get remote project name
                    remote_project_name = os.path.basename(remote_project)
                    remote_project_root = remote_project.replace(remote_project_name, '')
                    relative_path = remote_file.replace(remote_project_root, '')
                    if relative_path.startswith('/') == False and relative_path.startswith('\\') == False:
                        relative_path = '/' + relative_path
                        
                    local_fullpath = directory + relative_path
                    local_folder = os.path.dirname(os.path.abspath(local_fullpath))
                    fileItem = FileItem(remote_project, remote_file, local_folder, local_fullpath)
                    
                    thread.files.append(fileItem)
                    local_files.append(local_fullpath)
            except Exception as e:
                print("Harvest files error, exception: " + str(e))
                continue

        return thread

    @staticmethod
    def dialog(settings):
        return AddAvatarWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        try:
            name = widget.name.text()
            device_ip = widget.device_ip.text()
            device_port = int(widget.device_port.text())
            remotetool_port = int(widget.remotetool_port.text())
            listen_ip = widget.listen_ip.ip()
            listen_port = int(widget.listen_port.text())
            return CMAvatar(name, device_ip, device_port, remotetool_port, listen_ip, listen_port)
        except ValueError:
            title = QCoreApplication.translate("peel_device", "Error")
            msg = QCoreApplication.translate("peel_device", "Invalid port")
            QtWidgets.QMessageBox(widget, title, msg)

    def edit(self, settings):
        dlg = AddAvatarWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return False
        widget.update_device(self)
        return True
    
    def list_takes(self):
        return self.takes.keys()


class CMAvatarDownloadThread(DownloadThread):

    def __init__(self, device, directory, listen_port=8444, takes=None):
        super(CMAvatarDownloadThread, self).__init__()
        self.takes = takes
        self.device = device
        self.listen_port = listen_port
        self.directory = directory
        self.file_progress = 0.0

        self.files = []
        self.file_i = None
        self.tick_mod = 0
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)

            self.socket.bind((device.listen_ip, self.listen_port))
        except Exception as e:
            self.log(str(e))
            self.teardown()
            
    def __str__(self):
        return str(self.device) + " Downloader"

    def teardown(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        super(CMAvatarDownloadThread, self).teardown()

    def run(self):

        print("Downloading %d CMAvatar files" % len(self.files))
        self.log(self.tr("Downloading %s files count: %d") % (self.device.name, len(self.files)))

        if not os.path.isdir(self.directory):
            try:
                os.mkdir(self.directory)
            except IOError:
                self.log(self.tr("Error could not create directory: ") + str(self.directory))
                self.set_finished()
                return

        self.set_started()

        self.file_i = 0

        if self.socket == None:
            self.log(self.tr("%s device connect failed.\n" % self.device.name))
            self.all_done.emit()
            return

        try:
            self.socket.listen()
            while self.is_running():
                # For each file - loop much increment file_i or break
                if self.file_i >= len(self.files):
                    self.log(self.tr("No more files"))
                    break

                this_file = self.files[self.file_i]
                if not os.path.exists(this_file.local_project):
                    try:
                        os.makedirs(this_file.local_project)
                    except IOError:
                        self.log(self.tr("Error could not create directory: ") + this_file.local_project)
                        continue
                
                fileName = os.path.basename(this_file.local_file)
                this_name = str(self.device) + ":" + fileName

                # Skip existing
                #full_path = os.path.join(local_folder, this_file.local_file)
                if os.path.isfile(this_file.local_file):
                    self.file_i += 1
                    major = float(self.file_i) / float(len(self.files))
                    self.tick.emit(major)
                    self.file_done.emit(this_name, self.COPY_SKIP, None)
                    continue

                # Tell the CMAvatar we want it to send us a file
                #self.device.client.send_message("/control/transport", (self.device.listen_ip, self.listen_port, this_file.remote_file))
                self.device.clientTransform.send_message(common.cmd_req_transport, (self.device.listen_ip, self.listen_port, this_file.remote_file))
                self.file_progress = 0

                try:
                    # Wait for the connection from the device sending the file
                    conn, addr = self.socket.accept()
                except socket.timeout:
                    self.set_current("No response for file: " + this_file.remote_file)
                    print("No response for: " + this_file.remote_file)
                    self.file_done.emit(this_name, DownloadThread.COPY_FAIL, "Timeout")
                    conn = None

                if conn is not None:

                    conn.settimeout(2)
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

                    print('open full path: ' + this_file.local_file)
                    
                    # Get the file
                    local_fp = open(this_file.local_file, "wb")
                    self.read(conn, this_file, local_fp)
                    if this_file.complete:
                        print('get file complete...')
                        self.file_done.emit(this_name, this_file.complete, this_file.error)

                    local_fp.close()
                    conn.close()

                    if not this_file.complete:
                        os.unlink(this_file.local_file)

                self.file_i += 1
                self.file_progress = 1.0
                major = float(self.file_i) / float(len(self.files))
                self.tick.emit(major)

            self.log(self.tr("Download Thread done"))

        except Exception as e:
            self.log(str(e))
        finally:
            self.socket.close()

        self.all_done.emit()

    def read(self, conn, this_file, fp):

        # Remote device has connected, get the file
        self.set_current(this_file.local_file)

        this_file.complete = self.COPY_FAIL
        size_header = conn.recv(4)
        if size_header is None:
            this_file.error = "Read Error"
            return

        headers = struct.unpack(">i", size_header)
        this_file.file_size = headers[0]

        this_file.data_size = 0

        if this_file.file_size == 0:
            this_file.error = "Zero sized file"
            return

        while self.is_running():
            data = conn.recv(1024 * 10)
            if data is None or len(data) == 0:
                break

            fp.write(data)
            this_file.data_size += len(data)
            
            if self.tick_mod > 30:
                value = float(this_file.data_size)
                total = float(this_file.file_size)
                file_progress = value / total

                major = float(self.file_i) / float(len(self.files))
                minor = (1.0 / float(len(self.files))) * file_progress
                # print(f"*** major: {major}, minor: {minor}")
                self.tick.emit(major + minor)
                self.tick_mod = 0
            else:
                self.tick_mod += 1

        if this_file.data_size != this_file.file_size:
            this_file.error = "Incomplete data"
        else:
            this_file.complete = self.COPY_OK
