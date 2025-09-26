from pythonosc import udp_client
import socket, time
from peel_devices import PeelDeviceBase, SimpleDeviceWidget
from PySide6 import QtCore, QtWidgets
from peel_devices import common
from peel_devices import files_download

# CMTracker默认IP
default_motionbuilder_ip = "127.0.0.1"
# CMTracker默认端口
default_motionbuilder_port = 8833
# RemoteTool默认端口
defualt_remotetool_port = 9933

class SocketThread(QtCore.QThread):

    state_change = QtCore.Signal(str)

    def __init__(self, host, port):
        super(SocketThread, self).__init__()
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        self.messages = []
        self.error_flag = None
        self.status = 'OFFLINE'

    def run(self):

        while self.running:

            # when device teardown
            if self.socket is None:
                return
            
            try:
                ret = self.socket.recvfrom(1024, 0)
            except IOError as e:
                self.status = "OFFLINE"
                self.state_change.emit(self.status)
                time.sleep(2)
                continue

            if not ret:
                continue

            if ret[0] == b'RECORDING\x00':
                self.status = "RECORDING"
                self.state_change.emit(self.status)

            if ret[0] == b'STOPPED\x00':
                self.status = "ONLINE"
                self.state_change.emit(self.status)

            if ret[0] == b'HELLO\x00':
                if self.status != "RECORDING":
                    self.status = "ONLINE"
                    self.state_change.emit(self.status)

    def send(self, msg):
        self.socket.sendto(msg.encode("utf8"), (self.host, self.port))

    def close_socket(self):
        self.status = "OFFLINE"
        self.state_change.emit(self.status)
        
        if self.socket is None:
            print("Closing a closed socket")
            return

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        except IOError as e:
            print("Error closing Mobu Device socket: " + str(e))


class MobuDeviceWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "MotionBuilder", has_host=True, has_port=True,has_remotetool_port=True,
                         has_listen_ip=False, has_listen_port=False)
        msg = self.tr("<P>Connects to CMCapture Motion Builder Device</P>")
        msg += self.tr("<P>Requires the CMCapture device to be installed in motion builder</P>")
        msg += self.tr("<P>Records a new take and sets the take name</P>")

        if self.port.text() == "":
            self.port.setText(str(default_motionbuilder_port))

        if self.remotetool_port.text() == "":
            self.remotetool_port.setText(str(defualt_remotetool_port))

        self.set_info(msg)


class MotionBuilderDevice(PeelDeviceBase):
    def __init__(self, name, device_ip, device_port, remotetool_port):
        super(MotionBuilderDevice, self).__init__(name)
        self.recording = None
        self.current_take = None
        self.udp = None
        self.clientTransform = None
        self.current_state = None
        self.device_ip = None
        self.device_port = None
        self.remotetool_port = None
        self.listen_ip = '127.0.0.1'

        self.ping_timer = QtCore.QTimer()
        self.ping_timer.timeout.connect(self.ping_timeout)
        self.ping_timer.setInterval(common.timeout_heartbeat)
        self.ping_timer.setSingleShot(False)

        self.ping_timer.start()

        self.reconfigure(name, device_ip, device_port, remotetool_port)

    @staticmethod
    def device():
        return "Motionbuilder"

    def as_dict(self):

        return {
                'name': self.name,
                'device_ip': self.device_ip,
                'device_port': self.device_port,
                'remotetool_port': self.remotetool_port
                }

    def command(self, command, arg):

        if command == "record":
            self.udp.send("RECORD=" + arg)
            self.remotetool_client_send(common.cmd_req_record, (self.device_ip, self.device_port, True, self.current_take))

        if command == 'stop':
            self.udp.send("STOP")
            self.remotetool_client_send(common.cmd_req_record, (self.device_ip, self.device_port, False, self.current_take))

        if command == 'play':
            self.udp.send("PLAY")

    def reconfigure(self, name, host=None, port=None, remotetool_port=None):

        self.name = name

        if self.udp:
            self.udp.running = False
            self.udp.close_socket()
            self.udp.wait()
            self.udp = None

        if host is None or port is None:
            return
        
        self.device_ip = host
        self.device_port = port
        self.remotetool_port = remotetool_port

        # init by offline status
        self.do_state("OFFLINE")
        
		# connect to MotionBuilder.
        self.udp = SocketThread(host, port)
        self.udp.start()
        self.udp.state_change.connect(self.do_state)

        self.udp.send("PING")

        # file transform.
        self.clientTransform = udp_client.SimpleUDPClient(self.device_ip, self.remotetool_port)

    def do_state(self, state):
        self.current_state = state
        self.update_state(state, "")

    def get_state(self):
        if self.udp is None:
            return "ERROR"
        return self.current_state

    @staticmethod
    def dialog(settings):
        return MobuDeviceWidget(settings)

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        d = MotionBuilderDevice(None, None, None, None)
        widget.update_device(d)
        return d

    def edit(self, settings):
        dlg = MobuDeviceWidget(settings)
        dlg.name.setText(self.name)
        if self.udp is None:
            dlg.host.setText("")
            dlg.port.setText("")
            
        else:
            dlg.host.setText(self.udp.host)
            dlg.port.setText(str(self.udp.port))
            
        if self.clientTransform is None:
            dlg.remotetool_port.setText("")
        else:
            dlg.remotetool_port.setText(str(self.remotetool_port))

        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return False

        # calls self.reconfigure()

        try:
            port = int(widget.port.text())
            remotetool_port = int(widget.remotetool_port.text())
            self.reconfigure(widget.name.text(), widget.host.text(), port, remotetool_port)
            return True
        except ValueError as e:
            QtWidgets.QMessageBox.warning(widget, self.tr("Error"), self.tr("Invalid port"))
            return False

    def teardown(self):
        if self.ping_timer is None:
            self.ping_timer.stop()
            self.ping_timer.timeout.disconnect(self.ping_timeout)

        self.clientTransform = None

        if self.udp is not None:
            self.udp.running = False
            self.udp.close_socket()
            self.udp.wait()
            self.udp = None

    def ping_timeout(self):
        # Is MB online?
        if self.udp is not None:
            self.udp.send("PING")
            
        # param is not use
        self.remotetool_client_send(common.cmd_req_heatbeat, (self.device_ip, self.remotetool_port))

    def list_takes(self):
        return []
    
    def has_harvest(self):
        return True

    def harvest(self, directory):
        thread = files_download.AllFileDownloadThread(self, directory)
        return thread

    def remotetool_client_send(self, cmd, arg):
        try:
            print(f"OSC: {self.device_ip}:{self.remotetool_port} {cmd} {arg}")
            if self.clientTransform == None:
                return
                    
            self.clientTransform.send_message(cmd, arg)

        except OSError as e:
            self.on_state("ERROR")
            raise e
        except OverflowError as e:
            self.on_state("ERROR")
            raise e
        