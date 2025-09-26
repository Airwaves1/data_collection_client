from PySide6 import QtWidgets, QtCore
from pythonosc import udp_client
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import peel_devices
from peel_devices import common

from PeelApp import cmd

class OscListenThread(QtCore.QThread):

    state_changed = QtCore.Signal(str)

    def __init__(self, host, port):
        super(OscListenThread, self).__init__()
        self.setObjectName("OscListenThread")
        self.host = host
        self.port = port
        self.listen = None
        self.dp = None

    def register_callbacks(self):
        raise NotImplementedError

    def run(self):

        self.dp = Dispatcher()

        self.register_callbacks()

        # Start off line until we get a packet saying otherwise
        self.state_changed.emit("OFFLINE")

        try:
            print('BlockingOSCUDPServer: ' + self.host + ': ' + str(self.port))
            self.listen = BlockingOSCUDPServer((self.host, self.port), self.dp)
        except OverflowError as e:
            print("OSC ERROR...")
            self.state_changed.emit("ERROR")
            raise e

        try:
            self.listen.serve_forever()
        except OSError as e:
            # Windows throws an error when the socket is closed, we can ignore it
            if not str(e).startswith("[WinError 10038]"):
                raise e

        print("OSC Server Stopped")

    def teardown(self):
        if self.listen:
            self.listen.shutdown()
            self.listen.server_close()

class Osc(peel_devices.PeelDeviceBase):
    def __init__(self, listen_class, name=None, device_ip=None, device_port=None, remotetool_port=None, listen_ip=None,
                 listen_port=None, parent=None):
        super(Osc, self).__init__(name, parent)

        self.listen_class = listen_class

        # reconfigure sets these
        self.device_ip = device_ip
        self.device_port = device_port
        self.remotetool_port = remotetool_port
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self.slate = ""
        self.take = ""
        self.desc = ""
        self.listen_thread = None

        print("OSC Host: %s   Port: %s" % (str(device_ip), str(device_port)))

        self.state = "OFFLINE"
        self.is_recording = False

        self.client = None
        self.clientTransform = None
        self.ping_timer = None
        self.reconfigure(name, host=device_ip, port=device_port, remotetool_port=remotetool_port,
                         listen_ip=listen_ip, listen_port=listen_port)

        #client_send("/RecordStart", ["slate", "take1", "my desc"] )

    @staticmethod
    def device():
        # Must be subclassed
        raise NotImplementedError

    def as_dict(self):
        return {'name': self.name,
                'device_ip': self.device_ip,
                'device_port': self.device_port,
                'remotetool_port': self.remotetool_port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port}

    def reconfigure(self, name, **kwargs):

        for i in ['host', 'port', 'remotetool_port', 'listen_ip', 'listen_port']:
            if i not in kwargs.keys():
                print(kwargs.keys())
                raise ValueError("Missing key for reconfigure: " + i)

        self.name = name
        self.device_ip = kwargs['host']
        self.device_port = kwargs['port']
        self.remotetool_port = kwargs['remotetool_port']
        self.listen_ip = kwargs['listen_ip']
        self.listen_port = kwargs['listen_port']

        print("OSC Reconfigure: ", name, self.device_ip, self.device_port,
              self.listen_ip, self.listen_port)

        # Close the connections
        self.teardown()

        if self.device_ip is not None and self.device_port is not None:
            self.client = udp_client.SimpleUDPClient(self.device_ip, self.device_port,
                                                     allow_broadcast=False)
            
        if self.device_ip is not None and self.remotetool_port is not None:
            self.clientTransform = udp_client.SimpleUDPClient(self.device_ip, self.remotetool_port,
                                                     allow_broadcast=False)
            self.ping_timer = QtCore.QTimer()
            self.ping_timer.timeout.connect(self.ping_timeout)
            self.ping_timer.setInterval(common.timeout_heartbeat)
            self.ping_timer.setSingleShot(False)
            self.ping_timer.start()

        if self.listen_ip is not None and self.listen_port is not None:
            print("Staring OSC listen thread ", self.listen_ip, self.listen_port)

            if self.listen_thread:
                self.listen_thread.teardown()

            self.listen_thread = self.listen_class(self.listen_ip, self.listen_port)
            self.listen_thread.state_changed.connect(self.on_state, QtCore.Qt.QueuedConnection)
            self.listen_thread.start()


    def on_state(self, new_state):
        if new_state == "ONLINE" and self.is_recording:
            # Skip online messages while recording
            return

        if new_state == "STOP":
            new_state = "ONLINE"
        self.state = new_state
        self.update_state(new_state, "")

    def teardown(self):
        if self.ping_timer is not None:
            self.ping_timer.stop()
            self.ping_timer.timeout.disconnect(self.ping_timeout)
            self.ping_timer = None

        if self.client is not None:
            #self.client.client_close()
            self.client._sock.close()
            self.client = None

        if self.listen_thread:
            self.listen_thread.teardown()
            self.listen_thread.wait()
            self.listen_thread = None

    def ping_timeout(self):
        # param is not use
        self.remotetool_client_send(common.cmd_req_heatbeat, (self.device_ip, self.remotetool_port))

    def thread_join(self):
        pass

    def client_send(self, cmd, arg):
        try:
            print(f"OSC: {cmd} {arg}")
            if self.client == None:
                return
            self.client.send_message(cmd, arg)

        except OSError as e:
            self.on_state("ERROR")
            raise e
        except OverflowError as e:
            self.on_state("ERROR")
            raise e
        
    def remotetool_client_send(self, cmd, arg):
        try:
            print(f"OSC: {cmd} {arg}")
            if self.clientTransform == None:
                return
            self.clientTransform.send_message(cmd, arg)

        except OSError as e:
            self.on_state("ERROR")
            raise e
        except OverflowError as e:
            self.on_state("ERROR")
            raise e

    def command(self, command, argument):
        raise NotImplementedError

    def get_state(self):
        if not self.enabled:
            return "OFFLINE"
        return self.state

    def get_info(self):
        return ""

# PEEL LISTENER
class OscListenThreadPeel(OscListenThread):

    def record_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC RECORD TRIGGER: " + str(args))
        cmd.record()

    def stop_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC STOP TRIGGER: " + str(args))
        cmd.stop()

    def play_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PLAY TRIGGER: " + str(args))
        cmd.play()

    def play_stop(self, *args):
        self.state_changed.emit("ONLINE")
        print("OSC PLAY STOP TRIGGER: " + str(args))
        cmd.stop()

    def mark_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC MARK TRIGGER: " + str(args))
        cmd.createMark(args[1])

    def go_prev(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PREV: " + str(args))
        cmd.prev()

    def go_next(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC NEXT: " + str(args))
        cmd.next()

    def go_prevshot(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PREV SHOT: " + str(args))
        cmd.prevShot()

    def go_nextshot(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC NEXT SHOT: " + str(args))
        cmd.nextShot()

    def go_shotload(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC SHOT#: " + str(args))
        cmd.gotoShot(args[1])

    def default_handler(self, *args):
        self.state_changed.emit("ONLINE")
        print("DEFAULT")
        print(args)

    def register_callbacks(self):
        self.dp.map("/peel/transport/startrecord", self.record_filter)
        self.dp.map("/peel/transport/stoprecord", self.stop_filter)
        self.dp.map("/peel/transport/mark", self.mark_filter)
        self.dp.map("/peel/playback/play", self.play_filter)
        self.dp.map("/peel/playback/stop", self.play_stop)
        self.dp.map("/peel/playback/prev", self.go_prev)
        self.dp.map("/peel/playback/next", self.go_next)
        self.dp.map("/peel/shotlist/prev", self.go_prevshot)
        self.dp.map("/peel/shotlist/next", self.go_nextshot)
        self.dp.map("/peel/shotlist/shotload", self.go_shotload)
        self.dp.set_default_handler(self.default_handler)


class OscListenDialog(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        super(OscListenDialog, self).__init__(settings, "Osc Listen", has_host=True, has_port=True,has_remotetool_port=True,
                                              has_listen_ip=True, has_listen_port=True)

