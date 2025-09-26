from peel_devices.xml_udp import XmlUdpDeviceBase
from peel_devices import SimpleDeviceWidget

# CMTracker默认IP
default_avatary_ip = "127.0.0.1"
# CMTracker默认端口
default_avatary_port = "6600"
# RemoteTool默认端口
defualt_remotetool_port = 7600

# CMCapture默认IP
default_listener_ip = "127.0.0.1"
# CMCapture默认端口
default_listener_port = 6666

class AvataryWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        has_host = True
        has_port = True
        has_remotetool_port = True
        has_listen_ip=True
        has_listen_port=True
        super().__init__(settings, "Avatary", has_host=has_host, has_port=has_port, has_remotetool_port=has_remotetool_port,
                         has_listen_ip=has_listen_ip, has_listen_port=has_listen_port)
        
        if has_host:
            self.host.setText(str(default_avatary_ip))

        if has_port:
            self.port.setText(str(default_avatary_port))

        if has_remotetool_port:
            self.remotetool_port.setText(str(defualt_remotetool_port))

        if has_listen_ip:
            self.listen_ip.setCurrentText(str(default_listener_ip))

        if has_listen_port:
            self.listen_port.setText(str(default_listener_port))

        msg = self.tr('<P>Avatary is a great motion capture program!</P>')
        self.set_info(msg)

class Avatary(XmlUdpDeviceBase):

    def __init__(self, name=None, device_ip=None, device_port=None, remotetool_port=None, listen_ip=None, listen_port=None,
                 set_capture_folder=False):
        super().__init__(name, device_ip, device_port, remotetool_port, listen_ip, listen_port, fmt=None,
                         set_capture_folder=set_capture_folder)

    def as_dict(self):
        return {
                'name': self.name,
                'device_ip': self.device_ip,
                'device_port': self.device_port,
                'remotetool_port': self.remotetool_port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port }

    @staticmethod
    def device():
        return "Avatary"

    @staticmethod
    def dialog(settings):
        return AvataryWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return
        ret = Avatary()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):

        dlg = AvataryWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return False
        widget.update_device(self)
        return True
    
    def list_takes(self):
        return []


