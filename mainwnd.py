import sys, os, importlib
from PySide6.QtCore import Qt, QTimer, QTime, QTranslator, Signal
from PySide6.QtGui import (QAction, QIcon, QKeySequence, QTextCursor, QTextCharFormat, QColor, QFont)
from PySide6.QtWidgets import (QApplication, QDockWidget, QSplitter, QGridLayout, QLabel, QDialog, QMenu,
    QFileDialog, QMainWindow, QMessageBox, QWidget, QTableWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QSpacerItem, QSizePolicy, QHeaderView, QPushButton,
                   QLineEdit, QListWidget)

from PySide6.QtGui import QColor
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

from takeitem import TakeItem, ActionInfo
from datetime import datetime

from app_const import AppName
import app_css
from app_config import AppConfig
import app_json
import app_common
import mainwnd_rc

from dialog_takeitem import TakeItemDialog
from dialog_fbxmerge import FbxMergeDialog

import mylogger
from factory_widget import QtWidgetFactory
import app_const
from dict_shotname import DictShotName
from task_list_widget import TaskListWidget
from task_property_widget import TaskPropertyPanel

# 录制按钮长宽
RecordButtonWidth = 220
RecordButtonHeight = 60

# 录制的FPS
FPSDenominator = 33


class ExportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('路径选择工具')
        self.setGeometry(500, 200, 500, 150)  # 设置窗口位置和大小

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 标题标签
        hLayout = QHBoxLayout()
        self.path_label = QLabel()
        self.path_label.setStyleSheet("QLabel{color: black; background-color: white}")
        hLayout.addWidget(self.path_label)
        pathChooseBtn = QPushButton('...')
        pathChooseBtn.setStyleSheet("QPushButton {border: 1px solid #EAEAEA;}")
        pathChooseBtn.setFixedSize(50, 20)
        pathChooseBtn.clicked.connect(self.browse_path)
        hLayout.addWidget(pathChooseBtn)

        self.exportBtn = QPushButton(self.tr("export"))
        self.exportBtn.setStyleSheet("QPushButton {border: 1px solid #EAEAEA;}")

        layout.addLayout(hLayout)
        layout.addWidget(self.exportBtn)

        self.setLayout(layout)

    def browse_path(self):
        """打开文件对话框选择路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            '选择文件夹路径',
            '',  # 默认路径
            QFileDialog.ShowDirsOnly
        )
        if path:
            self.path_label.setText(path)

class MainWindow(QMainWindow):
    highlight_signal = Signal(int)

    def __init__(self):
        super().__init__()

        self.modPeelApp = importlib.import_module("PeelApp")
        if self.modPeelApp is None:
            mylogger.error('Import PeelApp module failed.')
            return
        self.modPeelApp.setMainWindow(self)

        self.mod_peel_devices = importlib.import_module("peel_devices")
        if self.mod_peel_devices is None:
            mylogger.error('Import peel_devices module failed.')
            return
            
        self.mod_peel = importlib.import_module("peel")
        if self.mod_peel is None:
            mylogger.error('Import peel module failed.')
            return
        
        self.mod_peel.startup()

        self.mod_merge_fbx = None
        self.func_merge_fbx = None
        self.init_device_list = []
        self.init_shot_list = []
        self.init_take_list = []

        # 录制面板初始数据
        self.init_take_no = app_const.Defualt_Edit_Take_No
        self.init_take_name = app_const.Defualt_Edit_Shot_Name
        self.init_take_notes = ''
        self.init_take_desc = ''

        self._shot_list = []

        # 保存Flag
        self._will_save = False

        #当前工程全路径
        self._save_fullpath = ""
        self._open_folder = os.getcwd()
        #录制中状态
        self._recording = False
        #录制时间
        self._record_secord = 0

        #录制一览表
        self._takelist = []
        #设备列表
        self._all_device = []
        #takename索引，放置重复录制相同名称的视频
        self._dict_takename = {}
        # shotname 分组
        self._dict_shotname = DictShotName()

        self.translator = None
        self.switch_language(app_const.Lang_CHS)

        self._time_record = QTimer(self)
        self._time_record.timeout.connect(self.record_tick)

        self._time_code = QTimer(self)
        self._time_code.timeout.connect(self.timecode_tick)
        self._time_code.start(FPSDenominator)

        self._centerWidget = QWidget()
        self.setCentralWidget(self._centerWidget)

        # 为兼容旧逻辑，提供一个隐藏的占位 shot 表（不显示到UI，仅用于内部读写）
        self._shotTable = QTableWidget(0, 4)

        self.create_actions()
        self.create_menus()
        self.create_tool_bars()
        self.create_status_bar()
        self.create_dock_windows()
        self.create_mainwnd()
        self.setWindowTitle(AppName)
        self.setStyleSheet(app_css.SheetStyle_Window)
        self._appconfig = AppConfig()
        self._appconfig.load_ui_config(self)
        if self._save_fullpath is not None and len(self._save_fullpath) > 0:
            self.open_project_file(self._save_fullpath)
        self.highlight_signal.connect(self.highLightNoteInfo)

        mylogger.info('MainWindow launch.')

    # 当主窗口关闭，子窗口也关闭
    def closeEvent(self, event):

        # 是否在录制中
        if self._recording:
            QMessageBox.warning(self, app_const.AppName, self.tr("It's recording now. Please stop record first."))
            event.ignore()
            return
        
        # 判断是否按了【取消】
        if self.save_project_ask() == False:
            event.ignore()
            return

        # 保存配置
        self._appconfig.save_open_file(self._save_fullpath)
        self._appconfig.save_ui_config(self)

        #断开所有设备
        self.mod_peel.teardown()
        mylogger.info('Application shutdown.')
        sys.exit(0)

    def switch_language(self, language):
        app = QApplication.instance()
        if self.translator is None:
            self.translator = QTranslator()
        else:
            app.removeTranslator(self.translator)
        
        if language == app_const.Lang_ENG:
            self.translator.load('zh_en.qm', directory='i18n')
        elif language == app_const.Lang_CHS:
            self.translator.load('zh_cn.qm', directory='i18n')
        app.installTranslator(self.translator)
        self.update()

    # 新建工程
    def new_project(self):

        if self.save_project_ask():
            self._appconfig.save_open_file(self._save_fullpath)
            self._save_fullpath = None
            self._recording = False
            self._record_secord = 0
            self._dict_takename = {}
            self._dict_shotname.clear()
            self._takelist = []
            self._all_device = []

            self.mod_peel.teardown()
            self.clearAllUiControl()
            self.setWindowTitle(AppName)
            #self.mod_peel.file_new()

    # 保存当前工程
    def save_project_ask(self):

        self.update_shot_list_model()
        modify = self.is_project_modify()

        if not self._will_save and not modify:
            return True
        
        reply = QMessageBox.question(self, AppName, self.tr("Save current open project?"), QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.save(True)

        if reply == QMessageBox.Cancel:
            return False
        else:
            return True

    # 工程是否被修改
    def is_project_modify(self):
        if self.init_take_name != self._edt_shotName.text():
            return True
        
        if self.init_take_desc != self._edt_desc.text():
            return True
        
        if self.init_take_notes != self.get_notes_text():
            return True
    
        # shot list是否被修改过
        shot_list_count_new = len(self._shot_list)
        if len(self.init_shot_list) == shot_list_count_new:
            for i in range(shot_list_count_new):
                item_shot_new = self._shot_list[i]
                item_shot_old = self.init_shot_list[i]

                if not self.is_item_same(item_shot_old, item_shot_new, 'name'):
                    return True

                if not self.is_item_same(item_shot_old, item_shot_new, 'description'):
                    return True

                if not self.is_item_same(item_shot_old, item_shot_new, 'take_no'):
                    return True
                
                if not self.is_item_same(item_shot_old, item_shot_new, 'shot_count'):
                    return True
                
        return False

    def is_item_same(self, item_old, item_new, key_name):
        name_new = None
        if key_name in item_new:
            name_new = item_new[key_name]

        name_old = None
        if key_name in item_old:
            name_old = item_old[key_name]

        if name_new != name_old:
            return False
        else:
            return True

    def open_project(self):
        # 打开文件对话框
        file_dialog = QFileDialog(self, f"Select a {AppName} json file", self._open_folder)
        file_dialog.setNameFilter("JSON Files (*.json)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        open_result = file_dialog.exec()
        if open_result == 0:
            return

        # 获取选择的文件路径
        selected_files = file_dialog.selectedFiles()
        file_path = selected_files[0]
        if self.open_project_file(file_path):
            self._appconfig.save_open_file(file_path)

    # open project file
    def open_project_file(self, json_file):
        json_data = app_json.load_json_file(json_file)
        if json_data is None:
            msg = self.tr("Open json file has been failed: ")
            QMessageBox.warning(self, self.tr("Open File"), msg + json_file)
            return False

        self._save_fullpath = json_file

        # 加载数据作为保存时对比用
        if 'shots' in json_data:
            self.init_shot_list = json_data['shots']
        else:
            self.init_shot_list = []

        if 'takes' in json_data:
            self.init_take_list = json_data['takes']
        else:
            self.init_take_list = []

        if 'take_no' in json_data:
            self.init_take_no = int(json_data['take_no'])

        if 'take_name' in json_data:
            self.init_take_name = json_data['take_name']

        if 'take_notes' in json_data:
            self.init_take_notes = json_data['take_notes']

        if 'take_description' in json_data:
            self.init_take_desc = json_data['take_description']
        
        self._shotTable.setRowCount(len(self.init_shot_list))
        row = 0
        for shot in self.init_shot_list:
            if shot is not None and len(shot) > 0:
                # 判断键是否存在
                if 'name' in shot:
                    self._shotTable.setItem(row, 0, QTableWidgetItem(shot['name']))

                if 'description' in shot:
                    self._shotTable.setItem(row, 1, QTableWidgetItem(shot['description']))

                if 'take_no' in shot:
                    self._shotTable.setItem(row, 2, QTableWidgetItem(shot['take_no']))

                if 'shot_count' in shot:
                    self._shotTable.setItem(row, 3, QTableWidgetItem(shot['shot_count']))
            
            row += 1
            
        self._takelist.clear()
        self._dict_takename.clear()
        for one_take in self.init_take_list:
            if one_take is None or len(one_take) == 0:
                continue
            
            take = TakeItem()
            shot_name = one_take['shot_name']
            if shot_name is not None:
                take._shot_name = shot_name

            take_no = one_take['take_no']
            if take_no is not None:
                take._take_no = take_no

            take_name = one_take['take_name']
            if take_name is not None:
                take._take_name = take_name
                self._dict_takename[take_name] = ''

            take_desc = one_take['take_desc']
            if take_desc is not None:
                take._take_desc = take_desc
            
            take_notes = one_take['take_notes']
            if take_notes is not None:
                take._take_notes = take_notes
            
            start_time = one_take['start_time']
            if start_time is not None:
                take._start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")

            end_time = one_take['end_time']
            if end_time is not None:
                take._end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")
            
            due = one_take['due']
            if due is not None:
                take._due = float(due)

            eval = one_take['eval']
            if eval is not None:
                take._eval = eval

            self._takelist.append(take)

        #update ui
        row = 0
        self._table_takelist.setRowCount(len(self._takelist))

        for _take in self._takelist:
            self.updateTakeRow(row, _take)
            row += 1

        self._dict_shotname.shot_list_group_by(self._takelist)

        self.mod_peel.load_data(json_file, 'replace')
        self._save_fullpath = json_file
        self._open_folder = os.path.dirname(json_file)
        self.setWindowTitle(f"{AppName} - {self._save_fullpath}")

        # 显示录制面板信息
        self._edt_shotName.setText(self.init_take_name)
        self._edt_desc.setText(self.init_take_desc)
        self._edt_notes.clear()
        if self.init_take_notes:
            # 将文本按行分割并添加到列表
            lines = self.init_take_notes.split('\n')
            for line in lines:
                if line.strip():
                    self._edt_notes.addItem(line.strip())

        self.updateLabelTakeName()
        return True

    def highLightNoteInfo(self, row):
        # 清除所有高亮 - 对于QListWidget，我们通过样式来实现
        if row == -1:
            # 清除所有选中状态
            self._edt_notes.clearSelection()
            return
        
        # 设置指定行的高亮
        if 0 <= row < self._edt_notes.count():
            self._edt_notes.setCurrentRow(row)
            # 滚动到指定项
            self._edt_notes.scrollToItem(self._edt_notes.item(row))

    def updateTakeRow(self, row, take_item):
        twItem = QTableWidgetItem(take_item._take_name)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 0, twItem)

        twItem = QTableWidgetItem(take_item._take_desc)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 1, twItem)
        
        twItem = QTableWidgetItem(take_item._take_notes)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 2, twItem)

        twItem = QTableWidgetItem(take_item._start_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 3, twItem)

        twItem = QTableWidgetItem(take_item._end_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 4, twItem)

        twItem = QTableWidgetItem(f"{'{:.1f}'.format(take_item._due)} sec")
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 5, twItem)

        #评分
        self.cmbEval = QtWidgetFactory.create_QComboBox(app_const.ComboBox_Eval_Default, take_item._eval)
        self.cmbEval.currentIndexChanged.connect(self.onComboBoxIndexChanged)
        self._table_takelist.setCellWidget(row, 6, self.cmbEval)

    def save(self, silence = False):
        # 判断是否第一次保存
        if self._save_fullpath is None or len(self._save_fullpath) == 0:
            dialog = QFileDialog(self)
            filename = f"myshot_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            fileNames = dialog.getSaveFileName(self, self.tr("Save file"),filename,'json files (*.json);; All files (*)')

            if len(fileNames) == 0:
                return
            
            self._save_fullpath = fileNames[0]

        saved = self.save_project_file()
        if saved:
            self._will_save = False

        self.setWindowTitle(f"{AppName} - {self._save_fullpath}")
        self.statusBar().showMessage(f"Saved '{self._save_fullpath}'", 2000)
        self._will_save = False

        # 静默不弹框
        if silence:
            return
        
        if saved:
            QMessageBox.information(self, AppName, self.tr("Project file saved."))

    def save_project_file(self):

        if self._save_fullpath is None or len(self._save_fullpath) == 0:
            return False
        
        self.update_shot_list_model()
        devices = self.mod_peel.get_devices_data()
        
        json_data = { 
                     'devices': devices,
                     'shots': self._shot_list,
                     'takes': self._takelist,
                     'take_name': self._edt_shotName.text(),
                     'take_description': self._edt_desc.text(),                     
                     'take_notes': self.get_notes_text()
                     }
        
        save_result = app_json.save_json_file(self._save_fullpath, json_data)
        if save_result == False:
            QMessageBox.warning(self, AppName, self.tr("Project file saved failed: ") + self._save_fullpath)

        return save_result
    
    def update_shot_list_model(self):
        self._shot_list.clear()
        rows = self._shotTable.rowCount()
        for row in range(rows):
            row_data = {}
            # Shot Name
            itemName = self._shotTable.item(row, 0)
            if itemName is not None:
                row_data['name'] = itemName.text()

            # Shot 描述
            itemDesc = self._shotTable.item(row, 1)
            if itemDesc is not None:
                row_data['description'] = itemDesc.text()
            
            # 最大的Take#
            itemTakeNo = self._shotTable.item(row, 2)
            if itemTakeNo is not None:
                row_data['take_no'] = itemTakeNo.text()

            # 统计[Shot Name]总数
            itemTakeCount = self._shotTable.item(row, 3)
            if itemTakeCount is not None:
                row_data['shot_count'] = itemTakeCount.text()

            for shot in self.init_shot_list:
                if shot is not None and len(shot) > 0:
                    if 'name' in shot and shot['name'] == row_data['name']:
                        if 'notes' in shot:
                            row_data['notes'] = shot['notes']

            self._shot_list.append(row_data)


    def collect_file(self):
        if self.mod_peel.show_harvest():
            self._will_save = True

    def export_file(self):
        window = ExportWidget(self)
        window.show()
        window.exportBtn.clicked.connect(lambda: self.mod_peel.command('Export', window.path_label.text()))

    def merge_motion_file(self):
        merge_list = {}
        row_count = self.generate_merge_list(merge_list)
        settings = self.mod_peel.get_settings()
        dlgFbxMerge = FbxMergeDialog(settings, merge_list, row_count, self)
        dlgFbxMerge.exec_()
        dlgFbxMerge.deleteLater()

    def generate_merge_list(self, merge_list):
        devices = self.mod_peel.get_devices_data()
        tracker_devices = []
        vrtrix_devices = {}
        row_count = 0
        #将CMTracker与手套设备进行分类
        for d in devices:
            device_type = d[0]
            if device_type == 'CMTracker' or device_type == 'CMAvatar':
                device_name = d[1]['name']
                tracker_devices.append(d[1])
                
            elif device_type == 'Vrtrix':
                device_name = d[1]['name']
                vrtrix_devices[device_name] = d[1]
            
        for td in tracker_devices:
            device_name = td['name']
            device_takes = td['takes']
            shot_items = []
            row_count += 1
            for key, value in device_takes.items():
                track_fbx = self.filterFbxFile(value)

                # fbx文件还未下载至本地
                if track_fbx is None or len(track_fbx) == 0:
                    mylogger.error(f'Device: [{device_name}], {key} {value} get track fbx file failed.')
                    continue

                hand_files = []
                #TODO should make relation
                for vr_key, vr_value in vrtrix_devices.items():
                    vr_takes = vr_value['takes']
                    if vr_takes is None or len(vr_takes) == 0:
                        continue

                    if key in vr_takes:
                        vr_files = vr_takes[key]['local_files']
                        if vr_files is not None and len(vr_files) > 0:
                            # vr_fbx = self.filterFbxFile(vr_files)
                            # 在列表末尾一次性追加另一个序列中的多个值
                            hand_files.extend(vr_files)
                    
                item = {'shot_name': key, 'body_fullpath': track_fbx, 'hand_files': hand_files }
                shot_items.append(item)
                row_count += 1

            merge_list[device_name] = shot_items

        return row_count

    # filter fbx file from file list
    def filterFbxFile(self, dict_take):
        arr_files = dict_take['local_files']

        if "skeleton_index" in dict_take:
            # CMTracker拆分骨骼
            arr_human_index = dict_take['skeleton_index']
            if arr_human_index is not None and len(arr_human_index) > 0:
                for idx in arr_human_index:
                    return arr_files[idx]

        # 未拆分骨骼
        for f in arr_files:
            (file_name, file_ext) = os.path.splitext(f)
            if file_ext == '.fbx':
                fbx_body = f
                return f
        return None
    
    def set_english(self):
        self.switch_language(app_const.Lang_ENG)
        pass

    def set_chinese(self):
        self.switch_language(app_const.Lang_CHS)
        pass

    def about(self):
        QMessageBox.about(self, AppName, f"<b>{AppName}</b> v1.0")

    def create_actions(self):
        icon = QIcon(':/images/new_project')
        self._new_letter_act = QAction(icon, self.tr("&New"),
                self, shortcut=QKeySequence.New,
                statusTip=self.tr("Create a new shot list"), triggered=self.new_project)
        
        icon = QIcon(':/images/open_project')
        self._open_project_act = QAction(icon, self.tr("&Open File"),
                self, shortcut=QKeySequence.Open,
                statusTip=self.tr("Open a project file"), triggered=self.open_project)

        icon = QIcon(':/images/save_project')
        self._save_act = QAction(icon, self.tr("&Save..."), self,
                shortcut=QKeySequence.Save,
                statusTip=self.tr("Save the current shot list"), triggered=self.save)

        self._quit_act = QAction(self.tr("&Quit"), self, shortcut="Ctrl+Q",
                statusTip=self.tr("Quit the application"), triggered=self.close)
        
        icon = QIcon(':/images/download_files')
        self._collect_file_act = QAction(icon, self.tr("Collect File"), self, shortcut="Ctrl+E",
                statusTip=self.tr("Collect file from remote devices"), triggered=self.collect_file)

        icon = QIcon(':/images/merge_files')
        self._merge_file_act = QAction(icon, self.tr("Merge Motion File"), self, shortcut="Ctrl+M",
                statusTip=self.tr("Merge motion file with body and hand fbx file"), triggered=self.merge_motion_file)

        icon = QIcon(':/images/export_files')
        self._export_file_act = QAction(icon, self.tr("Export File"), self, shortcut="Ctrl+B",
                statusTip=self.tr("Export file from avatar"), triggered=self.export_file)

        # 创建两个动作，分别表示英语和中文
        # self._eng_act = QAction("English", self)
        # self._eng_act.triggered.connect(self.set_english)
        # self._chs_act = QAction("Chinese", self)
        # self._chs_act.triggered.connect(self.set_chinese)
        self._about_act = QAction(self.tr("&About"), self,
                statusTip=self.tr("Show the application's About box"),
                triggered=self.about)

    def create_menus(self):
        self._file_menu = self.menuBar().addMenu(self.tr("&File"))
        self._file_menu.addAction(self._new_letter_act)
        self._file_menu.addAction(self._open_project_act)
        self._file_menu.addAction(self._save_act)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._quit_act)

        self._view_menu = self.menuBar().addMenu(self.tr("&View"))

        self._publish_menu = self.menuBar().addMenu(self.tr("&Publish"))
        self._publish_menu.addAction(self._collect_file_act)
        self._publish_menu.addAction(self._merge_file_act)
        self._publish_menu.addAction(self._export_file_act)

        self.menuBar().addSeparator()

        self._help_menu = self.menuBar().addMenu(self.tr("&Help"))
        # self._help_menu.addAction(self._chs_act)
        # self._help_menu.addAction(self._eng_act)
        self._help_menu.addAction(self._about_act)

    def create_tool_bars(self):
        self._file_tool_bar = self.addToolBar(self.tr("File"))

        self._file_tool_bar.addAction(self._new_letter_act)
        self._file_tool_bar.addAction(self._open_project_act)
        self._file_tool_bar.addAction(self._save_act)

        # 添加分隔符
        self._file_tool_bar.addSeparator()

        self._file_tool_bar.addAction(self._collect_file_act)
        self._file_tool_bar.addAction(self._merge_file_act)
        self._file_tool_bar.addAction(self._export_file_act)

    def create_status_bar(self):
        self.statusBar().showMessage("就绪...", 2000)

    def create_takelist(self, splitter):
        # 创建 QTableWidget
        takelistWidget = QTableWidget(splitter)
        # 设置列名
        header_labels = ["拍摄名称", 
                         "描述", 
                         "备注", 
                         "开始时间", 
                         "结束时间", 
                         "持续时间", 
                         "评分"]
        takelistWidget.setColumnCount(len(header_labels))
        takelistWidget.setHorizontalHeaderLabels(header_labels)
        # 设置表头字体颜色为黑色
        takelistWidget.horizontalHeader().setStyleSheet(app_css.SheetStyle_TableWidget_Header)
        # 设置表头字体颜色为黑色
        takelistWidget.verticalHeader().setStyleSheet(app_css.SheetStyle_TableWidget_Header)
        takelistWidget.itemDoubleClicked.connect(self.handleItemDoubleClicked)

        # 设置表格样式
        takelistWidget.setStyleSheet(app_css.SheetStyle_TableWidget)
        # QTableWidget右击
        takelistWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        takelistWidget.customContextMenuRequested.connect(self.showContextMenu)

        return takelistWidget
    
    # 双击QTableWidget显示编辑对话框
    def handleItemDoubleClicked(self, item):
        row = item.row()
        # column = item.column()
        # value = item.text()
        item_selected = self._takelist[row]
        h = TakeItemDialog(item_selected, self._dict_takename, self)
        h.resize(650, 600)
        result = h.exec()
        h.deleteLater()

        if result == QDialog.Accepted:
            self.updateTakeRow(row, item_selected)
            # 编辑框修改了内容
            if h._modify:
                self._will_save = True

	# 右击QTableWidget显示删除菜单
    def showContextMenu(self, pos):
        contextMenu = QMenu(self)

        deleteAction = QAction(self.tr("Remove Row"), self)
        deleteAction.triggered.connect(self.deleteSelectedRows)
        contextMenu.addAction(deleteAction)

        clearAction = QAction(self.tr("Clear Table"), self)
        clearAction.triggered.connect(self.clearAllRows)
        contextMenu.addAction(clearAction)

        contextMenu.exec_(self._table_takelist.mapToGlobal(pos))

	# 删除选中行
    def deleteSelectedRows(self):
        selected = self._table_takelist.selectedItems()
        if selected:
            rows = set(item.row() for item in selected)
            rows = list(rows)
            rows.sort(reverse=True)
            for row in rows:
                self._table_takelist.removeRow(row)
                shot = self._takelist.pop(row)
                self._dict_takename.pop(shot._take_name)
                self.delete_device_take(shot._take_name)

            # 更新场景切换表格
            self._dict_shotname.shot_list_group_by(self._takelist)
            self.update_shotlist()
            
    # 删除设备中的takes元素        
    def delete_device_take(self, shot_name):
        devices = self.mod_peel.get_devices_data()
        
        for d in devices:
            device_type = d[0]
            if device_type == 'CMTracker' or device_type == 'Vrtrix':
                shot_takes = d[1]['takes']
                if shot_name in shot_takes:
                    shot_takes.pop(shot_name)
                    return

    # 清空QTableWidget
    def clearAllRows(self):
        reply = QMessageBox.question(None, AppName, 
                                     self.tr("Are you sure you want to clear the table? This operation cannot be undone?"), 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._table_takelist.clearContents()
            self._table_takelist.setRowCount(0)
            self._takelist.clear()
            self._dict_takename.clear()
            self._dict_shotname.clear()

    def create_recordpanel(self, splitter):
        widget = QWidget(splitter)
        hBoxLayout = QHBoxLayout(widget)

        # 创建 QGridLayout
        gridLayout = QGridLayout()

        lblShotName = QLabel("任务ID:")
        gridLayout.addWidget(lblShotName, 0, 0)
        self._edt_shotName = QtWidgetFactory.create_QLineEdit(app_const.Defualt_Edit_Shot_Name)
        self._edt_shotName.setMaxLength(app_const.Max_Shot_Name)
        self._edt_shotName.setReadOnly(True)  # 设置为只读
        # 设置半角字符验证器
        reg_half = QRegularExpression(app_const.Regular_Char_Half)
        validator_half = QRegularExpressionValidator(self)
        validator_half.setRegularExpression(reg_half)
        self._edt_shotName.setValidator(validator_half)
        self._edt_shotName.textChanged.connect(self.edt_shotName_changed)
        
        gridLayout.addWidget(self._edt_shotName, 0, 1)

        lblDesc = QLabel("任务名称:")
        gridLayout.addWidget(lblDesc, 1, 0)
        #self.tr("Record description")
        self._edt_desc = QtWidgetFactory.create_QLineEdit('')
        self._edt_desc.setReadOnly(True)  # 设置为只读
        gridLayout.addWidget(self._edt_desc, 1, 1)

        lblNotes = QLabel("动作脚本:")
        gridLayout.addWidget(lblNotes, 2, 0)
        #self.tr("Record script")
        self._edt_notes = QListWidget()
        # QListWidget没有setReadOnly方法，通过样式和属性控制只读
        self._edt_notes.setStyleSheet(app_css.SheetStyle_ListWidget)
        gridLayout.addWidget(self._edt_notes, 2, 1)
        gridLayout.setRowStretch(2, 3)

        vboxLayout = QVBoxLayout()

        self._lbl_takename = QLabel()
        self._lbl_takename.setStyleSheet(app_css.SheetStyle_Label)
        self._lbl_takename.setFixedWidth(RecordButtonWidth)
        self._lbl_takename.setFixedHeight(RecordButtonHeight)
        self._lbl_takename.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.updateLabelTakeName()

        self._lbl_timecode = QLabel('00:00:00:00')
        self._lbl_timecode.setStyleSheet(app_css.SheetStyle_Label)
        self._lbl_timecode.setFixedWidth(RecordButtonWidth)
        self._lbl_timecode.setFixedHeight(RecordButtonHeight)
        self._lbl_timecode.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # Record button
        self._btn_record = QtWidgetFactory.create_QPushButton("录制", app_css.SheetStyle_Button_Record, self.record_clicked)
        self._btn_record.setFixedSize(RecordButtonWidth, RecordButtonHeight)

        vboxLayout.addWidget(self._lbl_takename)
        vboxLayout.addWidget(self._lbl_timecode)
        vboxLayout.addWidget(self._btn_record)

        #设置按钮间隔
        vboxLayout.setSpacing(5)
        #设置底部空白
        vboxLayout.addStretch(1)

        # 创建一个 QWidget 作为 QGridLayout 的容器
        hBoxLayout.addLayout(gridLayout)
        hBoxLayout.addLayout(vboxLayout)
        widget.setLayout(hBoxLayout)
        return widget

    def create_mainwnd(self):

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Vertical)

        self._table_takelist = self.create_takelist(splitter)
        self._widget_recordPanel = self.create_recordpanel(splitter)

        # 创建布局
        #layout = QVBoxLayout()
        splitter.addWidget(self._table_takelist)
        splitter.addWidget(self._widget_recordPanel)

        # 设置 QSplitter 的尺寸
        splitter.setSizes([300, 500])

        # 设置中心部件
        self.setCentralWidget(splitter)

        # layout.addWidget(self._btn_record)
        # layout.addWidget(self._btn_play)
        # layout.addWidget(self._btn_stop)

        # 创建中心部件并设置布局
        # centralWidget = QWidget(self)
        # centralWidget.setLayout(splitter)

        # 设置中心部件
        self.setCentralWidget(splitter)

    def get_takelist_table(self):
        return self._table_takelist

    def create_dock_windows(self):
        # 使用新的任务列表与属性面板替代旧的 Shot List
        # 先创建任务列表，再创建属性面板，这样属性面板会在下方
        self.create_tasks_dock_win()
        self.create_task_property_dock()
        self.create_devices_dock_win()

    def create_tasks_dock_win(self):
        dwTasks = QDockWidget("任务列表", self)
        dwTasks.setStyleSheet(app_css.SheetStyle_DockWidget)
        dwTasks.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._taskListWidget = TaskListWidget(dwTasks)
        self._taskListWidget.task_selected.connect(self.on_task_selected)
        dwTasks.setWidget(self._taskListWidget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dwTasks)
        self._view_menu.addAction(dwTasks.toggleViewAction())

    def create_task_property_dock(self):
        dwProps = QDockWidget("任务属性", self)
        dwProps.setStyleSheet(app_css.SheetStyle_DockWidget)
        dwProps.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._taskPropertyPanel = TaskPropertyPanel(dwProps)
        dwProps.setWidget(self._taskPropertyPanel)
        self.addDockWidget(Qt.LeftDockWidgetArea, dwProps)
        self._view_menu.addAction(dwProps.toggleViewAction())

    def on_task_selected(self, task):
        """任务选择回调：更新属性面板与录制面板输入"""
        # 更新左侧属性面板
        if hasattr(self, "_taskPropertyPanel") and self._taskPropertyPanel:
            self._taskPropertyPanel.display_task(task)

        # 同步到录制面板（任务ID/任务名称）
        task_id = task.task_id or ""
        self._edt_shotName.setText(task_id)
        
        # 任务名称优先中文，其次英文
        task_name = task.task_name_cn or task.task_name_en or ""
        self._edt_desc.setText(task_name)
        
        # 解析动作脚本
        self.parse_action_script(task.action_text_cn or "")
        
        self.updateLabelTakeName()

    def get_notes_text(self):
        """获取动作脚本的文本内容"""
        items = []
        for i in range(self._edt_notes.count()):
            item_text = self._edt_notes.item(i).text()
            # 移除序号前缀 (例如 "1. " -> "")
            action_text = item_text[item_text.find('. ') + 2:] if '. ' in item_text else item_text
            items.append(action_text)
        return '\n'.join(items)

    def parse_action_script(self, action_text_cn):
        """解析动作脚本，将换行符分隔的动作文本转换为列表显示"""
        if not action_text_cn:
            self._edt_notes.clear()
            return

        # 按双换行符分割动作
        actions = action_text_cn.split('\n\n')
        # 过滤空字符串
        actions = [action.strip() for action in actions if action.strip()]

        # 清空列表并添加动作项
        self._edt_notes.clear()
        for i, action in enumerate(actions):
            item_text = f"{i+1}. {action}"
            self._edt_notes.addItem(item_text)

    # 旧的 Shot List 停靠窗口已被任务列表替代

    def create_devices_dock_win(self):
        dwDevices = QDockWidget("设备列表", self)
        dwDevices.setStyleSheet(app_css.SheetStyle_DockWidget)
        dwDevices.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._widgetDevices = QWidget(dwDevices)
        #self._widgetDevices.setMinimumWidth(400)
        dwDevices.setWidget(self._widgetDevices)
        self.addDockWidget(Qt.RightDockWidgetArea, dwDevices)
        self._view_menu.addAction(dwDevices.toggleViewAction())

        vBoxlayout = QVBoxLayout()
        self._widgetDevices.setLayout(vBoxlayout)

        hBoxLayout = QHBoxLayout()

        self._device_spacer = QSpacerItem(35, 35, QSizePolicy.Expanding, QSizePolicy.Minimum)
        # add device button
        self._device_add = QtWidgetFactory.create_QPushButton('+', app_css.SheetStyle_ToolButton, self.devicelist_add)
        self._device_add.setFixedSize(35, 35)

        # delete device button
        self._device_del = QtWidgetFactory.create_QPushButton('-', app_css.SheetStyle_ToolButton, self.devicelist_delete)
        self._device_del.setFixedSize(35, 35)

        hBoxLayout.addItem(self._device_spacer)
        hBoxLayout.addWidget(self._device_add)
        hBoxLayout.addWidget(self._device_del)

        vBoxlayout.addLayout(hBoxLayout)

        # 创建 Device TableWidget
        self._deviceTable = QTableWidget(0, 3)
        # 设置列名
        header_labels = ["名称", "状态", "地址"]
        self._deviceTable.setHorizontalHeaderLabels(header_labels)
        # 设置表头字体颜色为黑色
        self._deviceTable.horizontalHeader().setStyleSheet(app_css.SheetStyle_TableWidget_Header)
        self._deviceTable.verticalHeader().setStyleSheet(app_css.SheetStyle_TableWidget_Header)

        # 设置表格样式
        self._deviceTable.setStyleSheet(app_css.SheetStyle_TableWidget)
        self._deviceTable.doubleClicked.connect(self.deviceTable_doubleClicked)
        # self._deviceTable.cellChanged.connect(self.deviceCellChanged)
        self._deviceTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        vBoxlayout.addWidget(self._deviceTable)

    # def deviceCellChanged(self, row, column):
    #     table_item = self._deviceTable.item(row, column)
    #     QMessageBox.warning(self, table_item.text(), table_item.text())

    # 再次打开设备对话框
    def deviceTable_doubleClicked(self, item):
        row = item.row()
        if self.mod_peel.device_info(row):
            self._will_save = True

    def edt_shotName_changed(self, text):
        self.updateLabelTakeName()

    def clearAllUiControl(self):
        self._shotTable.clearContents()
        self._shotTable.setRowCount(0)

        self._deviceTable.clearContents()
        self._deviceTable.setRowCount(0)

        self._table_takelist.clearContents()
        self._table_takelist.setRowCount(0)

    # 添加新设备
    def devicelist_add(self):
        device_cnt_before = len(self._all_device)
        self.mod_peel.add_device()
        device_cnt_after = len(self._all_device)
        if device_cnt_before != device_cnt_after:
            self._will_save = True

    # 删除设备
    def devicelist_delete(self):
        selected_rows = []

        selected_items = self._deviceTable.selectedItems()
        if len(selected_items) == 0:
            return
        
        for item in self._deviceTable.selectedItems():
            if item.row() not in selected_rows:
                selected_rows.append(item.row())

        # 从后往前删除，避免索引变化
        selected_rows.sort(reverse=True)  

        for row in selected_rows:
            recordItem = self._all_device[row]
            self.mod_peel.delete_device(recordItem.deviceId)

        self._will_save = True
    
    # 添加场景列表
    def shotlist_add(self):
        row_cnt = self._shotTable.rowCount() + 1
        self._shotTable.setRowCount(row_cnt)

    # 删除场景列表
    def shotlist_delete(self):
        selected_rows = []
        selectedIndexes = self._shotTable.selectedIndexes()
        for item in selectedIndexes:
            item_row = item.row()
            if item_row not in selected_rows:
                selected_rows.append(item_row)

        # 从后往前删除，避免索引变化
        selected_rows.sort(reverse=True)

        for row in selected_rows:
            self._shotTable.removeRow(row)


    def shotTable_sectionClicked(self, row):
        itemShotName = self._shotTable.item(row, 0)
        if itemShotName is None:
            return
        
        shot_name = itemShotName.text()
        
        shot_desc = ''
        itemShotDess = self._shotTable.item(row, 1)
        if itemShotDess is not None:
            shot_desc = itemShotDess.text()

        take_info = self._dict_shotname.take_info(shot_name)

        take_no = '1'
        if take_info is not None:
            take_no = str(take_info[0] + 1)

        self._edt_shotName.setText(shot_name)
        self._edt_desc.setText(shot_desc)
        for shot in self.init_shot_list:
            if shot['name'] == shot_name:
                if 'notes' in shot:
                    self._edt_notes.clear()
                    lines = shot['notes'].split('\n')
                    for line in lines:
                        if line.strip():
                            self._edt_notes.addItem(line.strip())
        
        self.updateLabelTakeName()

    # 录制开始/停止
    def record_clicked(self):
        if self._recording:
            #录制中
            self.mod_peel.command('stop', self._lbl_takename.text())
            self._lbl_takename.setStyleSheet(app_css.SheetStyle_Label)
            self._btn_record.setText("录制")
            self._record_secord = 0
            self._recording = False

            self._time_record.stop()

            take_last = self._takelist[-1]
            take_last._end_time = datetime.now()
            take_last._due = (take_last._end_time - take_last._start_time).total_seconds()

            row_count = len(self._takelist)
            lastRow = row_count - 1

            #录制结束时间
            str_end_time = take_last._end_time.strftime('%H:%M:%S')
            twItem = QTableWidgetItem(str_end_time)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(lastRow, 4, twItem)

            #录制时长(1位小数)
            twItem = QTableWidgetItem(f"{'{:.1f}'.format(take_last._due)} sec")
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(lastRow, 5, twItem)

            self._device_add.setEnabled(True)
            self._device_del.setEnabled(True)

            self.statusBar().showMessage("就绪...", 2000)
            self.highLightNoteInfo(-1)
            self.save(True)
        else:
            #未录制
            shot_name = self._edt_shotName.text()
            take_no = 1  # 固定为1，不再使用拍摄次数
            take_name = self._lbl_takename.text()
            if take_name in self._dict_takename:
                msg = self.tr(" has existed. Please modify shot name or take no.")
                QMessageBox.warning(self, AppName, take_name + msg)
                return

            self._dict_takename[take_name] = ''
            
            # for unreal
            self.mod_peel.command('shotName', shot_name)
            # common command
            self.mod_peel.command('takeNumber', take_no)
            self.mod_peel.command('record', take_name)
            self._lbl_takename.setStyleSheet(app_css.SheetStyle_Label_Shot)
            self._btn_record.setText('00:00:00')
            
            self._recording = True

            strDesc = self._edt_desc.text()
            strNotes = self.get_notes_text()
            takeItem = TakeItem(shot_name, 
                                take_no, 
                                take_name, 
                                strDesc, 
                                strNotes)
            
            self._takelist.append(takeItem)

            row_count = len(self._takelist)
            self._table_takelist.setRowCount(row_count)
            newRow = row_count - 1
            #Take名
            twItem = QTableWidgetItem(takeItem._take_name)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(newRow, 0, twItem)

            #录制描述
            twItem = QTableWidgetItem(takeItem._take_desc)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(newRow, 1, twItem)

            #录制批注
            twItem = QTableWidgetItem(takeItem._take_notes)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(newRow, 2, twItem)

            #录制开始时间
            str_start_time = takeItem._start_time.strftime('%H:%M:%S')
            twItem = QTableWidgetItem(str_start_time)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._table_takelist.setItem(newRow, 3, twItem)

            #评分
            self.cmbEval = QtWidgetFactory.create_QComboBox(app_const.ComboBox_Eval_Default, takeItem._eval)
            self.cmbEval.currentIndexChanged.connect(self.onComboBoxIndexChanged)
            self._table_takelist.setCellWidget(newRow, 6, self.cmbEval)
            self._table_takelist.scrollToBottom()
            self.statusBar().showMessage("录制中...", 0)
            #self._edt_notes.setReadOnly(True)
            #self.highLightNoteInfo()

            self._device_add.setEnabled(False)
            self._device_del.setEnabled(False)

            self._record_secord = 0
            self._time_record.start(1000)
            # 更新索引
            self._dict_shotname.add_shot_with_take(shot_name, take_no)
            self.update_shotlist()
        self._will_save = True

    def UpdateActionInfo(self, row, startFrame, endFrame):
        if 0 <= row < self._edt_notes.count():
            item_text = self._edt_notes.item(row).text()
            # 移除序号前缀 (例如 "1. " -> "")
            actionName = item_text[item_text.find('. ') + 2:] if '. ' in item_text else item_text
            actionInfo = ActionInfo(actionName, startFrame, endFrame)
            self._takelist[-1].add_action(actionInfo)

    # 根据shot name更新ShotList的序号列
    def update_shotlist(self):

        # 更新Shot List
        rows = self._shotTable.rowCount()
        for row in range(rows):
            item_shot_name = self._shotTable.item(row, 0)
            if item_shot_name is None:
                continue

            item_shot_name_value = item_shot_name.text()
            if item_shot_name_value is None or len(item_shot_name_value) == 0:
                continue

            take_info = self._dict_shotname.take_info(item_shot_name_value)
            if take_info is not None:
                self._shotTable.setItem(row, 2, QTableWidgetItem(str(take_info[0])))
                self._shotTable.setItem(row, 3, QTableWidgetItem(str(take_info[1])))

    # 下拉选择评分
    def onComboBoxIndexChanged(self, index):
        # 找到发出信号的QComboBox
        sender = self.sender()

        # selected_item = self.cmbEval.itemText(index)
        # print(f'Selected Eval: {selected_item}')

        # 通过QTableWidget的cellWidget方法找到QComboBox所在的行
        if sender:
            row = self._table_takelist.indexAt(sender.pos()).row()
            #self._table_takelist.setItem(row, 6, QTableWidgetItem(sender.currentText()))
            curTake = self._takelist[row]
            curTake._eval = sender.currentText()
            self._will_save = True

        # self._table_takelist.setItem(lastRow, 5, QTableWidgetItem(str(take_last._due.seconds) + ' sec'))

    def updateLabelTakeName(self):
        # 使用任务ID和任务名称生成显示名称
        task_id = self._edt_shotName.text()
        task_name = self._edt_desc.text()
        if task_id and task_name:
            result = f"{task_id}_{task_name}"
        elif task_id:
            result = task_id
        elif task_name:
            result = task_name
        else:
            result = "未选择任务"
        self._lbl_takename.setText(result)

    def record_tick(self):
        # print('recording: ' + datetime.now().strftime('%H:%M:%S'))
        self._record_secord += 1

        hh = int(self._record_secord / (60 * 60))
        mm = int((self._record_secord - (hh * 60 * 60)) / 60)
        ss = int((self._record_secord - (hh * 60 * 60)) - mm * 60)
        hour = str(hh)
        if len(hour) == 1:
            hour = "0" + hour

        min = str(mm)
        if len(min) == 1:
            min = "0" + min

        sec = str(ss)
        if len(sec) == 1:
            sec = "0" + sec

        qTime = hour + ":" + min + ":" + sec
        self._btn_record.setText(qTime)

    def timecode_tick(self):
        curTime = QTime.currentTime()
        msec = curTime.msec()
        curFps = int(msec / FPSDenominator)

        qsFps = str(curFps)
        if len(qsFps) == 1:
            qsFps = "0" + qsFps
        self._lbl_timecode.setText(curTime.toString() + ":" + qsFps)

    def stop_clicked(self):
        self.mod_peel.command('stop', 'test')

    '''添加设备，所有设备一起刷新'''
    def setDevices(self, devices):
        self._all_device = devices
        row_cnt = len(self._all_device)
        
        self._deviceTable.setRowCount(row_cnt)
        r = 0
        for d in devices:
            #设备名不可修改
            twItem = QTableWidgetItem(d.name)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._deviceTable.setItem(r, 0, twItem)

            #设备状态不可修改
            status_color = self.getStatusColor(d.status)
            twItem = QTableWidgetItem(d.status)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            
            # 设置背景色
            twItem.setBackground(status_color)
            self._deviceTable.setItem(r, 1, twItem)
            
            # 设备地址
            twItem = QTableWidgetItem(d.address)
            twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
            self._deviceTable.setItem(r, 2, twItem)

            r += 1

    def updateDevice(self, updatedDevice):
        row = 0
        for d in self._all_device:
            if updatedDevice.deviceId == d.deviceId:
                d.status = updatedDevice.status
                d.info = updatedDevice.info
                break
            row += 1
        
        twItem = QTableWidgetItem(updatedDevice.status)
        #设备状态不可修改
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        status_color = self.getStatusColor(updatedDevice.status)
        twItem.setBackground(status_color)
        self._deviceTable.setItem(row, 1, twItem)

    def getStatusColor(self, status):
        if status == 'OFFLINE':
            #1F1F1F
            return QColor(31,31,31)
        elif status == 'ONLINE':
            return QColor('green')
        elif status == 'RECORDING':
            return QColor('red')
        else:
            #紫色
            return QColor(128,100,162)
        
    