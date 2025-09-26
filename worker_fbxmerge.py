from PySide6 import QtCore
import os
import ctypes
import mylogger

DLL_MERGE_FILE = './FbxMergeHelper.dll'

class MergeFbxFilesThread(QtCore.QThread):
    # 0.0 - 1.0 progress done
    tick = QtCore.Signal(float)
    file_start = QtCore.Signal()
    file_process = QtCore.Signal(int)
    # Name, CopyState, error string
    file_done = QtCore.Signal(int, str, int, str)
    all_done = QtCore.Signal()
    message = QtCore.Signal(str)

    MERGE_FAIL = 0
    MERGE_OK = 1
    MERGE_SKIP = 2

    STATUS_NONE = 0
    STATUS_RUNNING = 1
    STATUS_STOP = 2
    STATUS_FINISHED = 3

    def __init__(self, dict_node, merge_list, file_count, directory):
        super(MergeFbxFilesThread, self).__init__()
        self.status = self.STATUS_NONE
        self.merge_list = merge_list
        self.merge_file_count = file_count
        self.output_root = directory
        self.mod_merge_fbx = None
        self.current_file = None

        self.body_leftnode = dict_node['body_left_node']
        self.body_rightnode = dict_node['body_right_node']
        self.hand_leftnode = dict_node['hand_left_node']
        self.hand_rightnode = dict_node['hand_right_node']

    def __del__(self):
        self.terminate()

    def log(self, message):
        mylogger.error(message)
        self.message.emit(message)

    def teardown(self):
        # cmd.writeLog(f"Teardown {str(self)}\n")
        self.status = self.STATUS_STOP
        self.wait(1000)

    def set_finished(self):
        self.status = self.STATUS_FINISHED
        self.tick.emit(1.0)
        self.all_done.emit()

    def set_started(self):
        self.status = self.STATUS_RUNNING
        self.tick.emit(0.0)
        self.file_start.emit()

    # tell ui whick one will process
    def set_current(self, job_index):
        self.file_process.emit(job_index)

    def file_ok(self, job_index, name):
        mylogger.error(f"[{name}] merge ok.")
        self.file_done.emit(job_index, name, self.MERGE_OK, None)

    def file_fail(self, job_index, name, err):
        mylogger.error(f"[{name}] merge failed, err: {err}")
        self.file_done.emit(job_index, name, self.MERGE_FAIL, err)
        
    def file_skip(self, job_index, name, reason):
        mylogger.error(f"[{name}] merge skip, {reason}")
        self.file_done.emit(job_index, name, self.MERGE_SKIP, reason)

    def is_running(self):
        return self.status is self.STATUS_RUNNING
    
    def run(self):
        self.log(self.tr("Merge %d CMTracker files") % self.merge_file_count)
        
        if self.mod_merge_fbx == None:
            try:
                # load FbxMergeHelper.dll file
                self.mod_merge_fbx = ctypes.CDLL(DLL_MERGE_FILE)
                self.func_merge_fbx = self.mod_merge_fbx.MergeFbxFile
                self.func_merge_fbx.restype = ctypes.c_bool

            except Exception as e:
                err_log = f"Load {DLL_MERGE_FILE} failed. exception: {e}"
                self.log(err_log)
                return

        self.set_started()

        body_leftnode_b = self.body_leftnode.encode('utf-8')
        body_rightnode_b = self.body_rightnode.encode('utf-8')
        hand_leftnode_b = self.hand_leftnode.encode('utf-8')
        hand_rightnode_b = self.hand_rightnode.encode('utf-8')

        #通过TakeList向各设备取得录制文件
        row_index = 0
        job_index = 0
        process_value = 0.0
        for key, value in self.merge_list.items():
            row_index += 1
            for take_item in value:

                self.set_current(row_index)

                shot_name = take_item['shot_name']
                body_fullpath = take_item['body_fullpath']

                dirStr, ext = os.path.splitext(body_fullpath)
                merged_filename = dirStr.split("/")[-1] + "_merged" + ext
                merge_fullpath = os.path.join(self.output_root, merged_filename)
                self.current_file = merge_fullpath.replace('\\', '/')
                if os.path.exists(self.current_file):
                    self.file_skip(row_index, self.current_file, self.tr('Merge file existed.'))
                    job_index += 1.0
                    process_value = job_index / self.merge_file_count
                    self.tick.emit(process_value)
                    row_index += 1
                    continue

                hand_files = take_item['hand_files']
                len_hands = len(hand_files)
                if len_hands == 0:
                    self.file_skip(row_index, self.current_file, self.tr('No hand files.'))
                    job_index += 1.0
                    process_value = job_index / self.merge_file_count
                    self.tick.emit(process_value)
                    row_index += 1
                    continue
                
                hand_files_utf8 = []
                for hand in hand_files:
                    hand_files_utf8.append(hand.encode('utf-8'))
                
                ccp_hands = (ctypes.c_char_p * len_hands)(*hand_files_utf8)

                # call module function to merge fbx
                res = self.func_merge_fbx(body_fullpath.encode('utf-8'), 
                                        body_leftnode_b, body_rightnode_b, 
                                        ccp_hands, len_hands, 
                                        hand_leftnode_b, hand_rightnode_b, 
                                        self.current_file.encode('utf-8'))
                
                if res == True:
                    self.file_ok(row_index, self.current_file)
                else:
                    self.file_fail(row_index, self.current_file, self.tr('merge failed.'))

                job_index += 1.0
                process_value = job_index / self.merge_file_count
                self.tick.emit(process_value)
                row_index += 1

        self.set_finished()
        self.log(self.tr("Merge Thread done."))

