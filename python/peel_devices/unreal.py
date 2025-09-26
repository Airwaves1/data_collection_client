from functools import partial
import peel_devices
from peel_devices.osc import Osc, OscListenThread
from peel_devices import common
from peel_devices import files_download

# CMTracker默认IP
default_unreal_ip = "127.0.0.1"
# CMTracker默认端口
default_unreal_port = 5500
# RemoteTool默认端口
defualt_remotetool_port = 5800

# CMCapture默认IP
default_listener_ip = "127.0.0.1"
# CMCapture默认端口
default_listener_port = 2222

class UnrealDialog(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        has_host = True
        has_port = True
        has_remotetool_port = True
        has_listen_ip=True
        has_listen_port=True
        super(UnrealDialog, self).__init__(settings, "Unreal", has_host=has_host, has_port=has_port,has_remotetool_port=has_remotetool_port,
                                           has_listen_ip=has_listen_ip, has_listen_port=has_listen_port)
        
        if has_host:
            self.host.setText(str(default_unreal_ip))

        if has_port:
            self.port.setText(str(default_unreal_port))

        if has_remotetool_port:
            self.remotetool_port.setText(str(defualt_remotetool_port))

        if has_listen_ip:
            self.listen_ip.setCurrentText(str(default_listener_ip))

        if has_listen_port:
            self.listen_port.setText(str(default_listener_port))

        msg = self.tr("<P>Enable Switchboard and OSC plugins in Unreal</P>")
        msg += self.tr("<P>In the Unreal project settings, enable 'Start an OSC Server when the editor launches'</P>")
        msg += self.tr("<P>The 'OSC Server Address' listen port in unreal ")
        msg += self.tr("Restart Unreal to enable the osc server")
        self.set_info(msg)

class Unreal(Osc):
    def __init__(self, name=None, device_ip=None, device_port=None, remotetool_port=None, listen_ip=None, listen_port=None):
        super(Unreal, self).__init__(OscListenThreadUnreal, name, device_ip, device_port, remotetool_port, listen_ip, listen_port)
        self.shot_name = None

    @staticmethod
    def device():
        return "Unreal"
    
    @staticmethod
    def dialog(settings):
        return UnrealDialog(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        ret = Unreal()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = UnrealDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return False

        widget.update_device(self)
        return True
    
    def get_state(self):
        if not self.enabled:
            return "OFFLINE"
        if self.state == "OFFLINE":
            self.client_send("/OSCAddSendTarget", (self.listen_ip, self.listen_port))

        return super(Unreal, self).get_state()

    def command(self, command, argument):
        if command == "stop":
            # Stop recording
            self.is_recording = False
            self.client_send("/RecordStop", "")
            self.remotetool_client_send(common.cmd_req_record, (self.listen_ip, self.listen_port, False, self.shot_name))
            
        if command == "record":
            # Create a marker and name it
            self.is_recording = True  # used to block online messages
            self.client_send("/Slate", self.shot_name)
            self.client_send("/RecordStart", "")
            self.remotetool_client_send(common.cmd_req_record, (self.listen_ip, self.listen_port, True, self.shot_name))

        if command == "shotName":
            self.shot_name = argument

        if command == "takeNumber":
            try:
                self.client_send("/Take", int(argument))
            except ValueError as e:
                print("Invalid take number: " + str(argument))

    def list_takes(self):
        return []
    
    def has_harvest(self):
        return True

    def harvest(self, directory):
        thread = files_download.AllFileDownloadThread(self, directory)
        return thread
    

class OscListenThreadUnreal(OscListenThread):
    def record_filter_handler(self, address, *args):
        print(f"unreal record: {address}: {args}")
        self.state_changed.emit("RECORDING")

    def stop_filter_handler(self, address, *args):
        print(f"unreal stop: {address}: {args}")
        self.state_changed.emit("ONLINE")

    def register_callbacks(self):
        self.dp.map("/RecordStartConfirm", partial(self.record_filter_handler, self))
        self.dp.map("/RecordStopConfirm", partial(self.stop_filter_handler, self))
        self.dp.map("/UE4LaunchConfirm", partial(self.stop_filter_handler, self))


