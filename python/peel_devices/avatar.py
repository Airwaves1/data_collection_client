from pythonosc import dispatcher, osc_server, udp_client
from peel_devices import PeelDeviceBase, DownloadThread, FileItem, BaseDeviceWidget
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Signal
import threading, socket, struct, time
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

        self.listen_ip = QtWidgetFactory.create_QComboBox_IP_Editable(settings.value("CMAvatarListenIp", self.tr("--all--")))
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

    # 定义信号
    auto_stop_requested = Signal()
    export_completed = Signal(bool, str, str)  # export_result, export_message, take_name
    file_list_received = Signal(list)  # file_list

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
        
        # 连接自动停止信号
        self.auto_stop_requested.connect(self._on_auto_stop_requested)

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
            exportPath = ""
            
            takeTable = self.GetTakeInfo()
            for row in range(takeTable.rowCount()):
                item = takeTable.item(row, 0)  # 第一列，列号为0
                comboBox = takeTable.cellWidget(row, 6)
                if comboBox.currentText() != "NG":
                    self.client.send_message(common.cmd_req_export, (self.listen_ip, self.listen_port, exportPath, item.text()))
                    self.clientTransform.send_message(common.cmd_req_export, (self.listen_ip, self.listen_port, exportPath, item.text()))

    def callback(self, address, command, *args):
        # 添加通用调试打印，显示所有收到的命令
        print(f"[DEBUG] CMAvatar callback from {address} {command} {args}")

        # 过滤心跳回调的打印，减少日志噪音
        if command != common.cmd_rep_heatbeat:
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

        if command == common.cmd_rep_exportFinish:
            # 设备导出完成回调
            # 设备返回格式: (take_name,) 或 (export_result, take_name) 或 (export_result, export_message, take_name)
            if len(args) == 1:
                # 只有take_name
                take_name = args[0]
                export_result = True
                export_message = ""
            elif len(args) == 2:
                # export_result 和 take_name
                export_result = args[0]
                take_name = args[1]
                export_message = ""
            elif len(args) >= 3:
                # export_result, export_message, take_name
                export_result = args[0]
                export_message = args[1]
                take_name = args[2]
            else:
                export_result = True
                export_message = ""
                take_name = ""
            
            print(f"[DEBUG] CMAvatar导出完成: result={export_result}, message={export_message}, take_name={take_name}")
            
            # 发送信号通知主窗口导出完成
            if export_result and take_name:
                print(f"[DEBUG] 发送export_completed信号: result={export_result}, message={export_message}, take_name={take_name}")
                self.export_completed.emit(export_result, export_message, take_name)
                print(f"[DEBUG] export_completed信号发送完成")
            else:
                print(f"[WARNING] 导出失败或无take_name: result={export_result}, take_name={take_name}")
            
            return

        # 处理文件列表响应
        if command == '/control/filelist/result':
            print(f"[DEBUG] 收到文件列表响应命令: {command}, args={args}")
            # 设备返回文件列表
            # args[0] 是文件数量，args[1:] 是文件路径列表
            if len(args) > 0:
                file_count = args[0]
                file_list = args[1:] if len(args) > 1 else []
                print(f"[DEBUG] 收到文件列表: 数量={file_count}, 文件={file_list}")
                
                # 发送信号通知下载线程文件列表已收到
                if hasattr(self, 'file_list_received'):
                    print(f"[DEBUG] 发送file_list_received信号: {file_list}")
                    self.file_list_received.emit(file_list)
                else:
                    print(f"[WARNING] 设备没有file_list_received信号")
            else:
                print(f"[WARNING] 文件列表响应参数为空: args={args}")
            
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
            # 只有在录制状态下才处理动作回调
            if self.state != "RECORDING":
                print(f"忽略动作回调: 当前状态为 {self.state}，非录制状态")
                return
                
            stage = args[0]
            startFrame = args[1]
            endFrame = args[2]
            print(f"[DEBUG] CMAvatar动作回调: stage={stage}, startFrame={startFrame}, endFrame={endFrame}")
            # 当前stage完成后，将高亮切换到下一条（若存在）
            try:
                next_stage = int(stage) + 1
                self.HighLightNotes(next_stage)
            except Exception:
                self.HighLightNotes(stage)
            self.UpdateActionInfo(stage, startFrame, endFrame)
            
            # 检查是否是最后一个动作，如果是则触发自动停止
            self.check_and_auto_stop(stage)

    def check_and_auto_stop(self, stage):
        """检查是否是最后一个动作，如果是则触发自动停止"""
        try:
            # 通过cmd模块获取主窗口的动作脚本数量
            from PeelApp import cmd
            main_wnd = cmd.g_mainWnd
            
            if main_wnd and hasattr(main_wnd, '_edt_notes'):
                total_actions = main_wnd._edt_notes.count()
                # 如果当前动作是最后一个（索引从0开始，所以stage == total_actions - 1）
                if total_actions > 0 and stage == total_actions - 1:
                    print(f"检测到最后一个动作完成 (stage={stage}, total={total_actions})，触发自动停止")
                    # 延迟1秒后触发自动停止，给用户一点时间看到最后一个动作
                    import threading
                    threading.Timer(1.0, self.trigger_auto_stop).start()
        except Exception as e:
            print(f"检查自动停止时出错: {e}")

    def trigger_auto_stop(self):
        """触发自动停止录制"""
        print("发射自动停止信号")
        self.auto_stop_requested.emit()
        
    def _on_auto_stop_requested(self):
        """处理自动停止信号（在主线程中执行）"""
        try:
            from PeelApp import cmd
            main_wnd = cmd.g_mainWnd
            
            if main_wnd and hasattr(main_wnd, 'auto_stop_recording'):
                main_wnd.auto_stop_recording()
        except Exception as e:
            print(f"处理自动停止信号时出错: {e}")

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

    def harvest(self, directory, take_name=None):
        """
        下载设备文件到指定目录
        directory: 本地下载目录
        take_name: take名称，用于文件夹下载模式
        """
        print(f"[DEBUG] CMAvatar.harvest called with directory={directory}, take_name={take_name}")
        
        if take_name:
            # 文件夹下载模式：基于take_name动态扫描整个文件夹
            print(f"[DEBUG] 开始文件夹下载模式，take_name: {take_name}")
            thread = CMAvatarDownloadThread(self, directory, take_name=take_name)
            print(f"[DEBUG] 启动下载线程...")
            try:
                thread.start()
                print(f"[DEBUG] 下载线程已启动")
                print(f"[DEBUG] 线程状态: {thread.status}")
                print(f"[DEBUG] 线程是否运行: {thread.isRunning()}")
            except Exception as e:
                print(f"[ERROR] 启动下载线程失败: {e}")
        else:
            # 如果没有take_name，报错
            print(f"[ERROR] 文件夹下载模式需要提供take_name")
            thread = CMAvatarDownloadThread(self, directory, take_name=None)
            thread.error_message = "文件夹下载模式需要提供take_name"

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
    
    def GetTakeInfo(self):
        """获取take信息表格 - 从主窗口获取任务信息"""
        from PeelApp import cmd
        
        # 获取主窗口实例
        main_window = cmd.getMainWindow()
        if not main_window:
            return MockTable([])
        
        # 获取主窗口的任务列表
        takelist = getattr(main_window, '_takelist', [])
        if not takelist:
            return MockTable([])
        
        class MockTable:
            def __init__(self, takelist):
                self.takelist = takelist
                
            def rowCount(self):
                return len(self.takelist)
                
            def get_episode_id_from_db(self, take_item):
                """从数据库获取episode_id"""
                try:
                    # 获取主窗口的数据库控制器
                    main_window = cmd.getMainWindow()
                    if not main_window or not hasattr(main_window, 'db_controller'):
                        return 'unknown'
                    
                    db_controller = main_window.db_controller
                    task_id = getattr(take_item, '_task_id', None)
                    
                    if not task_id:
                        return 'unknown'
                    
                    # 从数据库查询TaskInfo记录
                    task_info = db_controller.get_task_info_by_task_id(task_id)
                    if task_info and 'episode_id' in task_info:
                        return str(task_info['episode_id'])
                    
                    return 'unknown'
                except Exception as e:
                    print(f"获取episode_id失败: {e}")
                    return 'unknown'
                
            def item(self, row, col):
                if col == 0 and row < len(self.takelist):  # 第一列是任务信息组合
                    take_item = self.takelist[row]

                    # 直接使用TakeItem的take_name字段
                    take_name = getattr(take_item, '_take_name', '')
                    
                    # 如果take_name为空，尝试重新生成
                    if not take_name:
                        task_id = getattr(take_item, '_task_id', '') or ''
                        task_name = getattr(take_item, '_task_name', '') or ''
                        episode_id = getattr(take_item, '_episode_id', '') or ''
                        
                        if task_name and task_id and episode_id:
                            take_name = f"{task_name}_{task_id}_{episode_id}"
                        elif task_name and task_id:
                            take_name = f"{task_name}_{task_id}"

                    class MockItem:
                        def __init__(self, text):
                            self.text_value = text
                        def text(self):
                            return self.text_value
                    return MockItem(take_name)
                return None
                
            def cellWidget(self, row, col):
                if col == 6 and row < len(self.takelist):  # 第7列是状态下拉框
                    take_item = self.takelist[row]
                    task_status = getattr(take_item, '_task_status', 'pending')
                    
                    class MockComboBox:
                        def __init__(self, status):
                            # 将状态映射到中文显示
                            status_map = {
                                'pending': '待处理',
                                'accepted': '接受', 
                                'rejected': '已拒绝',
                                'ng': 'NG'
                            }
                            self.current_text = status_map.get(status, '待处理')
                        def currentText(self):
                            return self.current_text
                    return MockComboBox(task_status)
                return None
        
        return MockTable(takelist)


class CMAvatarDownloadThread(DownloadThread):
    """
    全新的文件夹递归下载线程
    使用现有的cmd_req_filelist命令获取文件列表，然后递归下载
    """

    def __init__(self, device, directory, listen_port=8444, take_name=None):
        print(f"[DEBUG] CMAvatarDownloadThread.__init__ called with take_name={take_name}")
        super(CMAvatarDownloadThread, self).__init__()
        self.device = device
        self.directory = directory
        self.listen_port = listen_port
        self.file_progress = 0.0
        self.files = []
        self.file_i = None
        self.tick_mod = 0
        
        # 文件夹下载相关
        self.take_name = take_name  # 直接使用传入的take_name
        self.file_list_received = False
        self.file_list = []
        self.download_mode = "folder"  # 默认文件夹下载模式
        
        # 错误处理
        self.error_message = None

        print(f"[DEBUG] 创建Socket，设备IP: {device.listen_ip}, 端口: {self.listen_port}")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.bind((device.listen_ip, self.listen_port))
            print(f"[DEBUG] Socket创建成功")
        except Exception as e:
            print(f"[ERROR] Socket creation failed: {e}")
            self.log(str(e))
            self.teardown()
            
        print(f"[DEBUG] CMAvatarDownloadThread.__init__ 完成")
            
    def __str__(self):
        return str(self.device) + " Folder Downloader"

    def teardown(self):
        if hasattr(self, 'socket') and self.socket is not None:
            try:
                self.socket.close()
            except Exception as e:
                print(f"Error closing socket in teardown: {e}")
            finally:
                self.socket = None
        super(CMAvatarDownloadThread, self).teardown()

    def _request_file_list(self, take_name):
        """
        使用现有的cmd_req_filelist命令请求文件列表
        """
        print(f"[DEBUG] 请求文件列表: {take_name}")
        print(f"[DEBUG] 设备IP: {self.device.listen_ip}, 端口: {self.listen_port}")
        print(f"[DEBUG] 发送命令: {common.cmd_req_filelist}")
        print(f"[DEBUG] 命令参数: (self.device.listen_ip={self.device.listen_ip}, self.listen_port={self.listen_port}, take_name={take_name})")
        
        # 发送文件列表请求命令
        # 假设设备支持传入take_name作为参数
        try:
            self.device.clientTransform.send_message(common.cmd_req_filelist, (self.device.listen_ip, self.listen_port, take_name))
            print(f"[DEBUG] 已发送文件列表请求命令")
            print(f"[DEBUG] 等待设备响应 /control/filelist/result 命令...")
        except Exception as e:
            print(f"[ERROR] 发送文件列表请求失败: {e}")
            self.error_message = f"发送文件列表请求失败: {e}"

    def _on_file_list_received(self, file_list):
        """
        处理设备返回的文件列表
        """
        print(f"[DEBUG] 收到文件列表: {file_list}")
        self.file_list = file_list
        self.file_list_received = True

    def run(self):
        """
        文件夹递归下载主流程
        """
        print(f"[DEBUG] ===== CMAvatarDownloadThread.run() 开始执行 =====")
        print(f"[DEBUG] 开始文件夹下载，take_name: {self.take_name}")
        print(f"[DEBUG] 下载目录: {self.directory}")
        print(f"[DEBUG] 设备: {self.device}")
        
        # 检查take_name
        if not self.take_name:
            print(f"[ERROR] 文件夹下载需要提供take_name")
            self.log("文件夹下载需要提供take_name")
            self.set_finished()
            return
        
        # 检查socket
        if self.socket is None:
            print(f"[ERROR] Socket创建失败")
            self.log(f"{self.device.name} 设备连接失败")
            self.all_done.emit()
            return
        
        try:
            # 创建本地下载目录
            if not os.path.isdir(self.directory):
                try:
                    os.makedirs(self.directory)
                    print(f"[DEBUG] 创建下载目录: {self.directory}")
                except IOError as e:
                    print(f"[ERROR] 无法创建目录: {e}")
                    self.log(f"无法创建目录: {self.directory}")
                    self.set_finished()
                    return
            
            # 启动socket监听
            self.socket.listen()
            print(f"[DEBUG] Socket开始监听端口: {self.listen_port}")
            
            # 连接文件列表信号
            if hasattr(self.device, 'file_list_received'):
                self.device.file_list_received.connect(self._on_file_list_received)
            
            # 请求文件列表
            self._request_file_list(self.take_name)
            
            # 等待文件列表返回（设置超时）
            timeout_count = 0
            max_timeout = 30  # 30秒超时
            
            print(f"[DEBUG] 开始等待文件列表响应...")
            while not self.file_list_received and timeout_count < max_timeout:
                time.sleep(1)
                timeout_count += 1
                print(f"[DEBUG] 等待文件列表... ({timeout_count}/{max_timeout})")
                
                # 每5秒检查一次设备状态
                if timeout_count % 5 == 0:
                    print(f"[DEBUG] 设备状态检查: IP={self.device.listen_ip}, 端口={self.listen_port}")
                    print(f"[DEBUG] 信号连接状态: {hasattr(self.device, 'file_list_received')}")
            
            # 断开信号连接
            if hasattr(self.device, 'file_list_received'):
                try:
                    self.device.file_list_received.disconnect(self._on_file_list_received)
                except:
                    pass
            
            if not self.file_list_received:
                print(f"[ERROR] 获取文件列表超时")
                self.log("获取文件列表超时")
                self.set_finished()
                return
            
            if not self.file_list:
                print(f"[WARNING] 文件夹为空: {self.take_name}")
                self.log(f"文件夹为空: {self.take_name}")
                self.set_finished()
                return
            
            # 构建FileItem列表
            for remote_file in self.file_list:
                # 构建本地文件路径，保持目录结构
                # remote_file 格式: /path/to/take_name/file.ext
                # 本地路径: directory/take_name/file.ext
                
                # 提取文件名
                file_name = os.path.basename(remote_file)
                
                # 构建本地完整路径
                local_file_path = os.path.join(self.directory, self.take_name, file_name)
                local_folder = os.path.dirname(local_file_path)
                
                # 创建FileItem
                fileItem = FileItem("", remote_file, local_folder, local_file_path)
                self.files.append(fileItem)
            
            print(f"[DEBUG] 准备下载 {len(self.files)} 个文件")
            self.log(f"准备下载 {len(self.files)} 个文件")
            
            # 开始下载文件
            self.set_started()
            self.file_i = 0
            
            while self.is_running() and self.file_i < len(self.files):
                this_file = self.files[self.file_i]
                
                # 创建本地目录
                if not os.path.exists(this_file.local_project):
                    try:
                        os.makedirs(this_file.local_project)
                    except IOError as e:
                        print(f"[ERROR] 无法创建目录: {e}")
                        self.log(f"无法创建目录: {this_file.local_project}")
                        self.file_i += 1
                        continue
                
                file_name = os.path.basename(this_file.local_file)
                this_name = f"{self.device.name}:{file_name}"
                
                # 跳过已存在的文件
                if os.path.isfile(this_file.local_file):
                    print(f"[DEBUG] 跳过已存在文件: {file_name}")
                    self.file_i += 1
                    major = float(self.file_i) / float(len(self.files))
                    self.tick.emit(major)
                    self.file_done.emit(this_name, self.COPY_SKIP, None)
                    continue
                
                # 请求设备发送文件
                print(f"[DEBUG] 请求下载文件: {this_file.remote_file}")
                self.device.clientTransform.send_message(
                    common.cmd_req_transport, 
                    (self.device.listen_ip, self.listen_port, this_file.remote_file)
                )
                self.file_progress = 0
                
                try:
                    # 等待设备连接
                    conn, addr = self.socket.accept()
                    print(f"[DEBUG] 设备连接: {addr}")
                except socket.timeout:
                    print(f"[ERROR] 文件下载超时: {this_file.remote_file}")
                    self.set_current(f"文件下载超时: {file_name}")
                    self.file_done.emit(this_name, self.COPY_FAIL, "Timeout")
                    conn = None
                
                if conn is not None:
                    try:
                        conn.settimeout(10)  # 文件传输超时
                        conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                        
                        print(f"[DEBUG] 开始下载文件: {this_file.local_file}")
                        
                        # 下载文件
                        local_fp = open(this_file.local_file, "wb")
                        self.read(conn, this_file, local_fp)
                        local_fp.close()
                        conn.close()
                        
                        if this_file.complete:
                            print(f"[DEBUG] 文件下载完成: {file_name}")
                            self.file_done.emit(this_name, this_file.complete, this_file.error)
                        else:
                            print(f"[ERROR] 文件下载失败: {file_name}")
                            self.file_done.emit(this_name, this_file.complete, this_file.error)
                            # 删除不完整的文件
                            if os.path.exists(this_file.local_file):
                                os.unlink(this_file.local_file)
                    
                    except Exception as e:
                        print(f"[ERROR] 文件下载异常: {e}")
                        self.file_done.emit(this_name, self.COPY_FAIL, str(e))
                        if conn:
                            conn.close()
                
                # 更新进度
                self.file_i += 1
                self.file_progress = 1.0
                major = float(self.file_i) / float(len(self.files))
                self.tick.emit(major)
            
            print(f"[DEBUG] 文件夹下载完成")
            self.log("文件夹下载完成")
            
        except Exception as e:
            print(f"[ERROR] 下载过程异常: {e}")
            self.log(f"下载过程异常: {e}")
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
        
        self.set_finished()
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
