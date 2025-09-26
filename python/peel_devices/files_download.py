import socket, struct
import os
import os.path
from peel_devices import DownloadThread, FileItem
from peel_devices import common


class AllFileDownloadThread(DownloadThread):

    def __init__(self, device, directory, listen_port=8444, takes=None):
        super(AllFileDownloadThread, self).__init__()
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
        super(AllFileDownloadThread, self).teardown()

    def run(self):

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
            #取得远程设备目录下所有文件列表
            self.device.remotetool_client_send(common.cmd_req_filelist, (self.device.listen_ip, self.listen_port))

            try:
                # Wait for the connection from the device sending the file
                conn, addr = self.socket.accept()
            except socket.timeout:
                self.set_current("No response for file list.")
                #print("No response for: " + this_file.remote_file)
                self.file_done.emit(self.device.name, DownloadThread.COPY_FAIL, "Timeout")
                conn = None

            if conn is None:
                self.log(self.tr("Download Thread done"))
                self.all_done.emit()
                return

            conn.settimeout(5)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            filecnt_header = conn.recv(4)
            if filecnt_header is None:
                #this_file.error = "Read Error"
                return
            
            filecnt = struct.unpack(">i", filecnt_header)
            file_count = filecnt[0]
            print('file_count: ' + str(file_count))
            if file_count == 0:
                #this_file.error = "get file list failed."
                self.log(self.tr("No file transform."))
                self.all_done.emit()

                return

            # 服务端接收消息
            total_data = bytes()
            while True:
                # 将收到的数据拼接起来
                data = conn.recv(1024)
                total_data += data
                if len(data) < 1024:
                    break

            #解析文件列表
            filelist_string = total_data.decode('utf-8')
            print('filelist_string: ' + filelist_string)
            filelists = filelist_string.split('|')
            print("file list count: " + str(filelists))
            #列表首条为远程设备工程路径
            firstElement = filelists[0]
            remote_project = firstElement.replace('\\', '/')

            for onefile in filelists[1:]:
                remote_file = onefile.replace('\\', '/')

                # 取得远程设备工程名
                remote_project_name = os.path.basename(remote_project)
                # 取得远程设备根路径
                remote_project_root = remote_project.replace(remote_project_name, '')
                # 取得相对位置
                relative_path = remote_file.replace(remote_project_root, '')
                if relative_path.startswith('/') == False:
                    relative_path = '/' + relative_path
                    
                # 取得本地相对路径
                full_path = self.directory + relative_path
                print("full_path: " + full_path)
                # abspath = os.path.abspath(full_path)
                # print("abspath: " + abspath)
                local_folder = os.path.dirname(full_path)
                print("local_folder: " + local_folder)
                oneFileItem = FileItem(remote_project, remote_file, local_folder, full_path)
                self.files.append(oneFileItem)

            self.log(self.tr("Downloading %s files count: %d") % (self.device.name, len(self.files)))

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
                
                this_name = str(self.device) + ":" + this_file.local_file

                # Skip existing
                #full_path = os.path.join(local_folder, this_file.local_file)
                if os.path.isfile(this_file.local_file):
                    self.file_i += 1
                    major = float(self.file_i) / float(len(self.files))
                    self.tick.emit(major)
                    self.file_done.emit(this_name, self.COPY_SKIP, None)
                    continue

                # Tell the Vrtrix we want it to send us a file
                self.device.remotetool_client_send(common.cmd_req_transport, (self.device.listen_ip, self.listen_port, this_file.remote_file))
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

