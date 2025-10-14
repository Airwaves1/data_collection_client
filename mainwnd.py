import sys, os, importlib, json
from PySide6.QtCore import Qt, QTimer, QTime, QTranslator, Signal
from PySide6.QtGui import (QAction, QIcon, QKeySequence, QTextCursor, QTextCharFormat, QColor, QFont)
from PySide6.QtWidgets import (QApplication, QDockWidget, QSplitter, QGridLayout, QLabel, QDialog, QMenu,
    QFileDialog, QMainWindow, QMessageBox, QWidget, QTableWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QSpacerItem, QSizePolicy, QHeaderView, QPushButton,
                   QLineEdit, QListWidget, QTextEdit, QComboBox)

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
from login_dialog import LoginDialog

import mylogger
from factory_widget import QtWidgetFactory
import app_const
from dict_shotname import DictShotName
from task_list_widget import TaskListWidget
from task_property_widget import TaskPropertyPanel
from service.db_controller import DBController
from export_manager import ExportManager
from uuid import uuid4

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
        # 数据控制器与当前采集者
        self.db_controller = DBController()
        self.current_collector: dict | None = None
        
        # 用户认证状态
        self.is_logged_in = False
        
        # 导出管理器
        self.export_manager = ExportManager(self.db_controller, self)
        
        # 数据库自动保存配置
        self.auto_save_to_db = True  # 默认开启自动保存到数据库
        
        # 导出完成等待状态
        self._waiting_for_export = False
        self._export_target_path = ""
        
        # 下载队列管理
        self._download_queue = []  # 等待下载的take_name列表
        self._is_downloading = False  # 当前是否正在下载

        self.mod_merge_fbx = None
        self.func_merge_fbx = None
        self.init_device_list = []
        self.init_shot_list = []

        # 录制面板初始数据
        self.init_take_no = app_const.Defualt_Edit_Take_No
        # 不再保存项目级takename
        self.init_take_name = ""
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
        
        # 自增ID管理
        self._next_episode_id = 1

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
        
        # 显示登录对话框
        self.show_login_dialog()

    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self)
        login_dialog.login_success.connect(self.on_login_success)
        
        # 如果用户取消登录，关闭应用程序
        if login_dialog.exec_() != QDialog.Accepted:
            self.close()
            
    def on_login_success(self, user_info):
        """登录成功处理"""
        self.current_collector = user_info
        self.is_logged_in = True
        
        # 更新状态栏显示当前用户
        self.statusBar().showMessage(f"当前用户: {user_info.get('collector_name', 'Unknown')}")
        
        # 可以在这里添加其他登录后的初始化操作
        mylogger.info(f"用户登录成功: {user_info.get('username', 'Unknown')}")
        
    def check_login_status(self):
        """检查登录状态"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "未登录", "请先登录后再进行操作")
            return False
        return True

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
            self.init_device_list = []  # 重置初始设备列表
            self.init_shot_list = []   # 重置初始shot列表
            
            # 清空任务列表数据
            if hasattr(self, '_taskListWidget') and self._taskListWidget:
                self._taskListWidget.data_manager.tasks.clear()
                self._taskListWidget.refresh_ui()

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
            saved = self.save(True)
            if not saved:
                # 保存失败，询问用户是否继续退出
                retry_reply = QMessageBox.question(self, AppName, self.tr("Save failed. Do you want to exit without saving?"), QMessageBox.Yes | QMessageBox.No)
                if retry_reply == QMessageBox.No:
                    return False  # 用户选择不退出

        if reply == QMessageBox.Cancel:
            return False
        else:
            return True

    # 工程是否被修改
    def is_project_modify(self):
        # 检查是否有任务数据被导入
        if hasattr(self, '_taskListWidget') and self._taskListWidget and len(self._taskListWidget.data_manager.tasks) > 0:
            return True
        
        # 检查是否有设备被添加或修改
        if len(self._all_device) != len(self.init_device_list):
            return True
        
        # 检查设备配置是否被修改
        for i, device in enumerate(self._all_device):
            if i < len(self.init_device_list):
                init_device = self.init_device_list[i]
                if device.name != init_device.get('name', ''):
                    return True
                if device.address != init_device.get('address', ''):
                    return True
        
        # shot list是否被修改过
        shot_list_count_new = len(self._shot_list)
        if len(self.init_shot_list) != shot_list_count_new:
            return True
            
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

        # 自动加载保存的Excel文件
        if 'excel_file_path' in json_data and json_data['excel_file_path']:
            excel_path = json_data['excel_file_path']
            if os.path.exists(excel_path) and hasattr(self, '_taskListWidget') and self._taskListWidget:
                try:
                    if self._taskListWidget.data_manager.load_from_excel(excel_path):
                        self._taskListWidget.refresh_ui()
                        # 保存当前Excel文件路径
                        self._taskListWidget._current_excel_path = excel_path
                        print(f"已自动加载Excel文件: {excel_path}")
                        print(f"加载了 {len(self._taskListWidget.data_manager.tasks)} 个任务数据")
                    else:
                        print(f"自动加载Excel文件失败: {excel_path}")
                except Exception as e:
                    print(f"自动加载Excel文件时出错: {e}")
            else:
                print(f"Excel文件不存在或路径无效: {excel_path}")

        # 不再读取项目级takename/描述/脚本
        
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
        
        # 设置UI状态：不从项目文件填充描述与脚本

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

        # 初始化设备列表，用于检测修改
        self.init_device_list = []
        for d in self._all_device:
            self.init_device_list.append({
                'name': d.name,
                'address': d.address,
                'status': d.status
            })

        # 显示录制面板信息：不从项目文件填充描述与脚本
        self._edt_notes.clear()

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
        # 任务ID
        twItem = QTableWidgetItem(take_item._task_id)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 0, twItem)

        # 任务名称
        twItem = QTableWidgetItem(take_item._task_name)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 1, twItem)
        
        # 开始时间
        twItem = QTableWidgetItem(take_item._start_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 2, twItem)

        # 结束时间
        twItem = QTableWidgetItem(take_item._end_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 3, twItem)

        # 持续时间
        twItem = QTableWidgetItem(f"{'{:.1f}'.format(take_item._due)} sec")
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 4, twItem)
        
        # 状态下拉框
        status_combo = QComboBox()
        status_combo.addItems(["待处理", "接受", "已拒绝", "NG"])
        
        # 根据当前状态设置选中项
        status_map = {
            "pending": "待审核",
            "accepted": "已接受", 
            "rejected": "已拒绝",
            "ng": "NG"
        }
        current_status_text = status_map.get(take_item._task_status, "待审核")
        status_combo.setCurrentText(current_status_text)
        
        # 连接状态变更事件
        status_combo.currentTextChanged.connect(lambda text, r=row: self.on_status_changed(r, text))
        
        self._table_takelist.setCellWidget(row, 5, status_combo)

    def on_status_changed(self, row, status_text):
        """处理状态变更事件"""
        try:
            if 0 <= row < len(self._takelist):
                take_item = self._takelist[row]
                
                # 将中文状态转换为英文状态
                status_map = {
                    "待审核": "pending",
                    "已接受": "accepted",
                    "已拒绝": "rejected", 
                    "NG": "ng"
                }
                new_status = status_map.get(status_text, "pending")
                
                # 更新TakeItem状态
                take_item._task_status = new_status
                
                print(f"任务 {take_item._task_id} 状态已更新为: {status_text} ({new_status})")
                
                # 如果任务已保存到数据库，则更新数据库状态
                if hasattr(take_item, '_task_id') and take_item._task_id:
                    self._update_task_status_in_db(take_item._task_id, new_status)
                    
        except Exception as e:
            print(f"更新状态失败: {e}")

    def _update_task_status_in_db(self, task_id, status):
        """更新数据库中的任务状态"""
        try:
            if self.db_controller:
                success = self.db_controller.update_task_status(task_id, status)
                if success:
                    print(f"数据库任务 {task_id} 状态已更新为: {status}")
                else:
                    print(f"更新数据库任务 {task_id} 状态失败")
        except Exception as e:
            print(f"更新数据库状态失败: {e}")

    def save(self, silence = False):
        # 判断是否第一次保存
        if self._save_fullpath is None or len(self._save_fullpath) == 0:
            dialog = QFileDialog(self)
            filename = f"myshot_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            fileNames = dialog.getSaveFileName(self, self.tr("Save file"),filename,'json files (*.json);; All files (*)')

            if len(fileNames) == 0 or not fileNames[0]:
                return False
            
            self._save_fullpath = fileNames[0]

        saved = self.save_project_file()
        if saved:
            self._will_save = False
            self.setWindowTitle(f"{AppName} - {self._save_fullpath}")
            self.statusBar().showMessage(f"Saved '{self._save_fullpath}'", 2000)

        # 静默不弹框
        if silence:
            return saved
        
        if saved:
            QMessageBox.information(self, AppName, self.tr("Project file saved."))
        else:
            QMessageBox.warning(self, AppName, self.tr("Project file save failed."))
            
        return saved

    def save_project_file(self):

        if self._save_fullpath is None or len(self._save_fullpath) == 0:
            return False
        
        self.update_shot_list_model()
        # 只保存设备配置信息，不包含takes数据
        devices = self.mod_peel.get_device_config_data()
        
        # 获取表格文件路径
        excel_file_path = ""
        if hasattr(self, '_taskListWidget') and self._taskListWidget:
            # 获取当前加载的Excel文件路径（如果有的话）
            excel_file_path = getattr(self._taskListWidget, '_current_excel_path', "")
        
        json_data = { 
                     'devices': devices,
                     'shots': self._shot_list,
                     'excel_file_path': excel_file_path
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
        # 选择保存路径
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "选择保存路径", self._open_folder)
        if not path:
            return
        
        # 检查是否有设备连接
        has_connection, message = self.check_device_connection()
        if not has_connection:
            QMessageBox.warning(self, "设备连接检查", message)
            return
        
        # 连接CMAvatar设备信号（如果还没有连接）
        self.connect_avatar_signals()
        
        # 设置导出目标路径
        self._export_target_path = path
        
        # 先调用设备的导出命令（路径为空，让设备自己处理）
        self.mod_peel.command('Export', '')
        
        # 显示等待消息
        self.statusBar().showMessage("等待设备导出完成...", 0)
        
        # 设置超时保护（30秒后如果还没收到回调，则停止等待）
        if hasattr(self, '_export_timeout_timer') and self._export_timeout_timer is not None:
            try:
                self._export_timeout_timer.stop()
            except Exception:
                pass
        else:
            self._export_timeout_timer = QTimer(self)
            self._export_timeout_timer.timeout.connect(self._on_export_timeout)
        
        # 30秒超时
        self._export_timeout_timer.start(30000)

    def _on_export_timeout(self):
        """导出超时处理"""
        self.statusBar().showMessage("导出超时，尝试下载现有文件...", 3000)
        # 超时后仍然尝试下载
        if self.mod_peel.show_harvest_with_path(self._export_target_path):
            self._will_save = True
            self.statusBar().showMessage("下载完成", 3000)
        else:
            self.statusBar().showMessage("下载失败", 3000)

    def export_file(self):
        """从数据库导出TaskInfo到选定文件夹"""
        self.export_manager.export_data(self._takelist, self._open_folder)

    def _export_task_data(self, task_id, takes):
        """导出单个任务的数据"""
        try:
            # 获取任务信息（从任务列表组件）
            task_info = self._get_task_info(task_id)
            
            # 构建导出数据
            export_data = []
            
            for take_item in takes:
                # 解析动作脚本为action_config格式
                # 将take_notes转换为列表格式
                notes_list = take_item._take_notes.split('\n') if take_item._take_notes else []
                action_config = self._parse_actions_to_config(notes_list, take_item._actions, task_info)
                
                # 使用英文任务名称，过滤换行符
                task_name_en = self._clean_text(task_info.get('task_name_en', ''))
                if not task_name_en:
                    task_name_en = self._clean_text(take_item._take_desc)
                
                # 使用场景信息
                scene_text = self._clean_text(task_info.get('scenarios', ''))
                if not scene_text:
                    scene_text = f"Task {task_id}: {task_name_en}"
                
                episode_data = {
                    "episode_id": self._get_next_episode_id(),
                    "label_info": {
                        "action_config": action_config
                    },
                    "task_name": task_name_en,
                    "init_scene_text": scene_text
                }
                export_data.append(episode_data)
            
            # 保存到文件
            output_file = os.path.join("data", "output", "task_info", f"task_{task_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"成功导出任务 {task_id} 到 {output_file}")
            return True
            
        except Exception as e:
            print(f"导出任务 {task_id} 失败: {e}")
            return False

    def _get_task_info(self, task_id):
        """获取任务信息"""
        try:
            # 从任务列表组件获取任务信息
            if hasattr(self, '_taskListWidget') and self._taskListWidget:
                task = self._taskListWidget.data_manager.get_task_by_id(task_id)
                if task:
                    return {
                        'task_name_en': task.task_name_en,
                        'task_name_cn': task.task_name_cn,
                        'scenarios': task.scenarios,
                        'action_text_en': task.action_text_en,
                        'action_text_cn': task.action_text_cn
                    }
                else:
                    print(f"[DEBUG] 未找到任务 {task_id}")
            else:
                print(f"[DEBUG] 没有_taskListWidget组件")
        except Exception as e:
            print(f"获取任务信息失败: {e}")
        
        return {}

    def _save_task_to_database(self, task_id, takes):
        """保存任务数据到数据库"""
        try:
            # 获取任务信息
            task_info = self._get_task_info(task_id)
            
            # 获取当前采集者ID
            collector_id = self.current_collector.get('collector_id') or self.current_collector.get('id')
            if not collector_id:
                print(f"保存任务 {task_id} 到数据库失败: 没有采集者ID")
                print(f"当前采集者信息: {self.current_collector}")
                return False
            
            saved_count = 0
            
            for take_item in takes:
                # 解析动作脚本为action_config格式
                notes_list = take_item._take_notes.split('\n') if take_item._take_notes else []
                action_config = self._parse_actions_to_config(notes_list, take_item._actions, task_info)
                
                # 使用英文任务名称
                task_name_en = self._clean_text(task_info.get('task_name_en', ''))
                if not task_name_en:
                    task_name_en = self._clean_text(take_item._take_desc)
                
                # 使用场景信息
                scene_text = self._clean_text(task_info.get('scenarios', ''))
                if not scene_text:
                    scene_text = f"Task {task_id}: {task_name_en}"
                
                # 更新现有的TaskInfo记录，而不是创建新的
                update_data = {
                    'task_name': task_name_en,
                    'init_scene_text': scene_text,
                    'action_config': action_config,
                    'task_status': 'pending'  # 默认为待审核状态
                }
                
                result = self.db_controller.update_task_by_task_id(str(task_id), update_data)
                
                if result:
                    saved_count += 1
                    # 获取更新后的任务ID
                    task_info_id = result.get('id')
                    if task_info_id:
                        # 将任务ID保存到TakeItem中，用于后续状态更新
                        take_item._task_id = task_info_id
                    print(f"成功更新任务 {task_id} 到数据库")
                else:
                    print(f"更新任务 {task_id} 到数据库失败")
            
            return saved_count > 0
            
        except Exception as e:
            print(f"保存任务 {task_id} 到数据库失败: {e}")
            return False

    def _clean_action_text(self, action_text):
        """清理动作文本，移除括号内的技能标识"""
        import re
        # 移除括号内的技能标识，如 (Fold), (Pick) 等
        cleaned_text = re.sub(r'\([^)]+\)', '', action_text)
        # 清理多余的空格和标点
        cleaned_text = cleaned_text.strip()
        return cleaned_text

    def _clean_text(self, text):
        """清理文本，移除换行符和多余空格"""
        if not text:
            return ""
        return text.replace('\n', ' ').replace('\r', ' ').strip()

    def _parse_actions_to_config(self, notes_text, actions, task_info=None):
        """将动作脚本解析为action_config格式"""
        action_config = []
        
        # 优先使用英文动作文本
        english_actions = ""
        if task_info and task_info.get('action_text_en'):
            english_actions = task_info.get('action_text_en')
        
        # 如果没有英文动作文本，直接返回空配置
        if not english_actions:
            print("警告: 没有英文动作文本，跳过动作配置生成")
            return action_config
        
        if actions:
            # 如果有具体的动作信息（包含帧数据），使用英文动作文本
            for i, action in enumerate(actions):
                # 从英文动作文本中获取对应的动作
                action_text = self._get_english_action_by_index(english_actions, i)
                if not action_text:
                    # 如果没有找到对应的英文动作，跳过这个动作
                    print(f"警告: 没有找到第{i+1}个动作的英文文本，跳过")
                    continue
                
                # 提取技能
                skill = self._extract_skill_from_action(action_text)
                # 清理动作文本，移除括号内的技能标识
                cleaned_action_text = self._clean_action_text(action_text)
                
                action_config.append({
                    "start_frame": action.start_frame,
                    "end_frame": action.end_frame,
                    "action_text": self._clean_text(cleaned_action_text),
                    "skill": skill
                })
        else:
            # 如果没有具体动作信息，从英文动作文本解析
            source_text = english_actions
            
            if source_text:
                # 处理动作文本，支持多种分隔符
                lines = []
                if isinstance(source_text, str):
                    # 检查是否是Python列表格式的字符串
                    if source_text.strip().startswith('[') and source_text.strip().endswith(']'):
                        # 解析Python列表格式的字符串
                        try:
                            import ast
                            parsed_list = ast.literal_eval(source_text)
                            if isinstance(parsed_list, list):
                                lines = parsed_list
                            else:
                                lines = source_text.split('\n')
                        except:
                            # 如果解析失败，按换行符分割
                            lines = source_text.split('\n')
                    else:
                        # 如果是普通字符串，按换行符分割
                        lines = source_text.split('\n')
                elif isinstance(source_text, list):
                    # 如果是列表，直接使用
                    lines = source_text
                
                current_frame = 0
                frame_duration = 100  # 默认每个动作100帧
                
                for line in lines:
                    if isinstance(line, str):
                        line = line.strip()
                    else:
                        line = str(line).strip()
                    
                    if line:
                        # 移除序号前缀
                        if '. ' in line:
                            action_text = line[line.find('. ') + 2:]
                        else:
                            action_text = line
                        
                        # 清理动作文本
                        action_text = self._clean_text(action_text)
                        
                        if action_text:  # 确保动作文本不为空
                            # 提取技能
                            skill = self._extract_skill_from_action(action_text)
                            # 清理动作文本，移除括号内的技能标识
                            cleaned_action_text = self._clean_action_text(action_text)
                            
                            action_config.append({
                                "start_frame": current_frame,
                                "end_frame": current_frame + frame_duration,
                                "action_text": cleaned_action_text,
                                "skill": skill
                            })
                            current_frame += frame_duration
        
        return action_config

    def _get_english_action_by_index(self, english_actions, index):
        """根据索引获取英文动作文本"""
        if not english_actions:
            return None
        
        try:
            # 解析英文动作文本
            lines = []
            if isinstance(english_actions, str):
                # 检查是否是Python列表格式的字符串
                if english_actions.strip().startswith('[') and english_actions.strip().endswith(']'):
                    import ast
                    parsed_list = ast.literal_eval(english_actions)
                    if isinstance(parsed_list, list):
                        lines = parsed_list
                    else:
                        lines = english_actions.split('\n')
                else:
                    lines = english_actions.split('\n')
            elif isinstance(english_actions, list):
                lines = english_actions
            
            # 根据索引获取对应的动作
            if 0 <= index < len(lines):
                action_text = lines[index]
                if isinstance(action_text, str):
                    action_text = action_text.strip()
                    # 移除序号前缀
                    if '. ' in action_text:
                        action_text = action_text[action_text.find('. ') + 2:]
                    return action_text
                else:
                    return str(action_text).strip()
            
            return None
        except Exception as e:
            print(f"解析英文动作文本失败: {e}")
            return None

    def _get_english_action_text(self, chinese_action, english_actions):
        """根据中文动作获取对应的英文动作文本"""
        if not english_actions:
            return ""
        
        # 简单的映射逻辑，可以根据需要改进
        # 这里可以根据动作的相似性进行匹配
        english_lines = english_actions.split('\n')
        chinese_lines = []
        
        # 如果有中文动作文本，也进行分割
        if hasattr(self, '_current_task') and self._current_task:
            chinese_text = self._current_task.action_text_cn or ""
            chinese_lines = chinese_text.split('\n')
        
        # 尝试找到对应的英文动作
        for i, chinese_line in enumerate(chinese_lines):
            if chinese_action in chinese_line and i < len(english_lines):
                return english_lines[i].strip()
        
        return ""

    def _extract_skill_from_action(self, action_text):
        """从动作文本中提取技能类型"""
        import re
        
        # 首先检查是否有括号内的技能标识，如 (Fold), (Pick), (Push) 等
        skill_match = re.search(r'\(([^)]+)\)', action_text)
        if skill_match:
            skill = skill_match.group(1).strip()
            # 清理技能名称，移除多余的空格和标点
            skill = skill.replace('.', '').strip()
            return skill
        
        # 如果没有括号内的技能标识，使用关键词匹配
        action_text_lower = action_text.lower()
        
        # 支持中英文关键词判断技能类型
        if any(keyword in action_text for keyword in ["取", "抓", "拿"]) or \
           any(keyword in action_text_lower for keyword in ["pick", "grab", "take", "retrieve"]):
            return "Pick"
        elif any(keyword in action_text for keyword in ["放", "置"]) or \
             any(keyword in action_text_lower for keyword in ["place", "put", "set"]):
            return "Place"
        elif "推" in action_text or any(keyword in action_text_lower for keyword in ["push"]):
            return "Push"
        elif "拉" in action_text or any(keyword in action_text_lower for keyword in ["pull"]):
            return "Pull"
        elif "倒" in action_text or any(keyword in action_text_lower for keyword in ["pour", "dump"]):
            return "Pour"
        elif "刷" in action_text or any(keyword in action_text_lower for keyword in ["brush", "scrub"]):
            return "Brush"
        elif "摇" in action_text or any(keyword in action_text_lower for keyword in ["shake"]):
            return "Shake"
        elif "握" in action_text or any(keyword in action_text_lower for keyword in ["hold", "grip"]):
            return "Hold"
        elif any(keyword in action_text_lower for keyword in ["fold", "bend"]):
            return "Fold"
        else:
            return "Manipulate"  # 默认技能类型

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

        # 账户菜单已移除（登录改为启动时强制弹窗）

        self._publish_menu = self.menuBar().addMenu(self.tr("&Publish"))
        self._publish_menu.addAction(self._collect_file_act)
        self._publish_menu.addAction(self._merge_file_act)
        self._publish_menu.addAction(self._export_file_act)

        self.menuBar().addSeparator()

        self._help_menu = self.menuBar().addMenu(self.tr("&Help"))
        # self._help_menu.addAction(self._chs_act)
        # self._help_menu.addAction(self._eng_act)
        self._help_menu.addAction(self._about_act)
        
    def toggle_auto_save(self):
        """切换自动保存到数据库功能"""
        self.auto_save_to_db = self._auto_save_act.isChecked()
        status = "开启" if self.auto_save_to_db else "关闭"
        self.statusBar().showMessage(f"自动保存到数据库: {status}", 2000)
        print(f"自动保存到数据库: {status}")
        
    # 账户菜单及相关流程已移除

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
        # 显示当前采集者
        self._collector_label = QLabel(self.tr("未登录采集者"))
        self.statusBar().addPermanentWidget(self._collector_label)

    def create_takelist(self, splitter):
        # 创建 QTableWidget
        takelistWidget = QTableWidget(splitter)
        # 设置列名 - 优化后的列名
        header_labels = ["任务ID", 
                         "任务名称", 
                         "开始时间", 
                         "结束时间", 
                         "持续时间",
                         "状态"]
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

        # 设置列宽
        takelistWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 任务ID
        takelistWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)           # 任务名称
        takelistWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 开始时间
        takelistWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 结束时间
        takelistWidget.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 持续时间
        takelistWidget.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)   # 状态

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
                # 仅当存在有效take_name时再同步字典与设备
                if getattr(shot, "_take_name", None):
                    if shot._take_name in self._dict_takename:
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
        lblShotName.setStyleSheet("""
            QLabel {
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                background-color: transparent;
                padding: 4px 0px;
            }
        """)
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
        
        # 设置任务ID输入框的字体样式
        self._edt_shotName.setStyleSheet("""
            QLineEdit {
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                background-color: #2A2A2A;
                border: 2px solid #333333;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0078D4;
                background-color: #333333;
            }
            QLineEdit:hover {
                border: 2px solid #555555;
            }
            QLineEdit[readOnly="true"] {
                background-color: #1A1A1A;
                color: #CCCCCC;
                border: 2px solid #444444;
            }
        """)
        
        gridLayout.addWidget(self._edt_shotName, 0, 1)

        lblDesc = QLabel("任务名称:")
        lblDesc.setStyleSheet("""
            QLabel {
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                background-color: transparent;
                padding: 4px 0px;
            }
        """)
        gridLayout.addWidget(lblDesc, 1, 0)
        #self.tr("Record description")
        self._edt_desc = QtWidgetFactory.create_QLineEdit('')
        self._edt_desc.setReadOnly(True)  # 设置为只读
        
        # 设置任务名称输入框的字体样式
        self._edt_desc.setStyleSheet("""
            QLineEdit {
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                background-color: #2A2A2A;
                border: 2px solid #333333;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0078D4;
                background-color: #333333;
            }
            QLineEdit:hover {
                border: 2px solid #555555;
            }
            QLineEdit[readOnly="true"] {
                background-color: #1A1A1A;
                color: #CCCCCC;
                border: 2px solid #444444;
            }
        """)
        
        gridLayout.addWidget(self._edt_desc, 1, 1)

        lblNotes = QLabel("动作脚本:")
        lblNotes.setStyleSheet("""
            QLabel {
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                background-color: transparent;
                padding: 4px 0px;
            }
        """)
        gridLayout.addWidget(lblNotes, 2, 0)
        #self.tr("Record script")
        self._edt_notes = QListWidget()
        # QListWidget没有setReadOnly方法，通过样式和属性控制只读
        
        # 设置动作脚本列表的字体样式
        self._edt_notes.setStyleSheet("""
            QListWidget {
                background-color: #1A1A1A;
                color: #CCCCCC;
                border: 2px solid #333333;
                border-radius: 4px;
                font-family: 'Microsoft YaHei';
                font-size: 14pt;
                font-weight: bold;
                padding: 8px;
                outline: none;
            }

            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #333333;
                background-color: transparent;
                font-size: 14pt;
                font-weight: bold;
            }

            QListWidget::item:hover {
                background-color: #2A2A2A;
            }

            QListWidget::item:selected {
                background-color: #0078D4;
                color: #FFFFFF;
            }

            QListWidget::item:selected:hover {
                background-color: #005A9E;
            }

            QListWidget::item:focus {
                outline: none;
            }
        """)
        
        gridLayout.addWidget(self._edt_notes, 2, 1)
        gridLayout.setRowStretch(2, 3)

        vboxLayout = QVBoxLayout()

        self._lbl_timecode = QLabel('00:00:00:00')
        self._lbl_timecode.setStyleSheet(app_css.SheetStyle_Label)
        self._lbl_timecode.setFixedWidth(RecordButtonWidth)
        self._lbl_timecode.setFixedHeight(RecordButtonHeight)
        self._lbl_timecode.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # Record button
        self._btn_record = QtWidgetFactory.create_QPushButton("录制", app_css.SheetStyle_Button_Record, self.record_clicked)
        self._btn_record.setFixedSize(RecordButtonWidth, RecordButtonHeight)
        self._btn_record.setEnabled(False)  # 初始状态禁用

        vboxLayout.addWidget(self._lbl_timecode)
        vboxLayout.addWidget(self._btn_record)

        # 添加录制提示框
        self._lbl_recording_tips = QLabel()
        self._lbl_recording_tips.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #cccccc;
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Microsoft YaHei';
                line-height: 1.4;
            }
        """)
        self._lbl_recording_tips.setFixedWidth(RecordButtonWidth)
        self._lbl_recording_tips.setWordWrap(True)  # 允许换行
        self._lbl_recording_tips.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # 设置提示内容
        tips_content = """1. 点击录制会有三秒的准备时间。
2. 左侧动作列表高亮后再进行操作。
3. 完成一个动作后稍作停顿，等待下个动作列表高亮后操作。
4. 完成所有动作后，会自动结束录制。"""
        self._lbl_recording_tips.setText(tips_content)
        
        vboxLayout.addWidget(self._lbl_recording_tips)

        # 添加提示编辑器框
        self._edt_tips = QTextEdit()
        self._edt_tips.setReadOnly(True)  # 设置为只读
        self._edt_tips.setFixedWidth(RecordButtonWidth)
        self._edt_tips.setFixedHeight(120)  # 设置较大的高度
        self._edt_tips.setStyleSheet(app_css.SheetStyle_Label)
        self._edt_tips.setPlainText("就绪")  # 设置默认文本
        self._edt_tips.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示滚动条
        self._edt_tips.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        vboxLayout.addWidget(self._edt_tips)

        # 添加倒计时数字标签
        self._lbl_countdown = QLabel("")
        self._lbl_countdown.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #ff4444;
                background-color: #404040;
                border: 2px solid #333333;
                border-radius: 10px;
                padding: 10px;
                font-family: 'Microsoft YaHei';
            }
        """)
        self._lbl_countdown.setFixedWidth(RecordButtonWidth)
        self._lbl_countdown.setFixedHeight(80)
        self._lbl_countdown.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._lbl_countdown.hide()  # 默认隐藏
        vboxLayout.addWidget(self._lbl_countdown)

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
        
        # 启用录制按钮
        self._btn_record.setEnabled(True)
        
        self.updateLabelTakeName()

    def get_notes_text(self):
        """获取动作脚本的文本内容"""
        items = []
        for i in range(self._edt_notes.count()):
            item_text = self._edt_notes.item(i).text()
            # 移除序号前缀 (例如 "1. " -> "")
            action_text = item_text[item_text.find('. ') + 2:] if '. ' in item_text else item_text
            items.append(action_text)
        return items  # 返回列表而不是字符串

    def _get_next_episode_id(self):
        """生成全局唯一的episode ID，避免与后端唯一约束冲突"""
        return uuid4().hex

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

    def connect_avatar_signals(self):
        """连接CMAvatar设备的信号"""
        print(f"[DEBUG] connect_avatar_signals 被调用")
        
        # 从peel模块获取真正的设备对象
        try:
            # 使用主窗口已经导入的peel模块的DEVICES（DeviceCollection）
            if hasattr(self.mod_peel, 'DEVICES') and self.mod_peel.DEVICES:
                print(f"[DEBUG] 从mod_peel.DEVICES获取设备，数量: {len(self.mod_peel.DEVICES)}")
                
                # 查找CMAvatar设备（真正的Python设备对象）
                avatar_devices = [d for d in self.mod_peel.DEVICES if d.device() == "CMAvatar"]
                print(f"[DEBUG] 找到的CMAvatar设备数量: {len(avatar_devices)}")
                
                for avatar_device in avatar_devices:
                    print(f"[DEBUG] 处理CMAvatar设备: {avatar_device.name}")
                    print(f"[DEBUG] 设备类型: {type(avatar_device)}")
                    if hasattr(avatar_device, 'export_completed'):
                        try:
                            # 断开之前的连接（如果有的话）
                            avatar_device.export_completed.disconnect()
                            print(f"[DEBUG] 断开之前的信号连接")
                        except TypeError:
                            # 如果没有连接过，会抛出TypeError，忽略即可
                            print(f"[DEBUG] 没有之前的信号连接")
                            pass
                        
                        # 连接新的信号
                        avatar_device.export_completed.connect(self._on_avatar_export_completed)
                        print(f"已连接CMAvatar设备信号: {avatar_device.name}")
                        print(f"[DEBUG] 信号连接成功: {avatar_device.name}")
                        print(f"[DEBUG] 设备对象: {avatar_device}")
                        print(f"[DEBUG] 信号对象: {avatar_device.export_completed}")
                    else:
                        print(f"[ERROR] 设备 {avatar_device.name} 没有 export_completed 信号")
            else:
                print(f"[ERROR] mod_peel.DEVICES 为空或不存在")
        except Exception as e:
            print(f"[ERROR] 获取设备失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_avatar_export_completed(self, export_result, export_message, take_name):
        """处理CMAvatar设备导出完成回调"""
        print(f"[DEBUG] 收到导出完成回调: result={export_result}, message={export_message}, take_name={take_name}")
        
        if export_result and take_name:
            # 停止超时定时器
            if hasattr(self, '_export_timeout_timer') and self._export_timeout_timer is not None:
                try:
                    self._export_timeout_timer.stop()
                    print(f"[DEBUG] 停止导出超时定时器")
                except Exception as e:
                    print(f"[DEBUG] 停止超时定时器失败: {e}")
            
            # 导出成功，添加到下载队列
            print(f"[DEBUG] 导出完成，添加到下载队列: {take_name}")
            self._download_queue.append(take_name)
            
            # 更新状态栏显示队列状态
            queue_size = len(self._download_queue)
            if self._is_downloading:
                self.statusBar().showMessage(f"下载队列: {queue_size} 个任务等待中...", 0)
            else:
                self.statusBar().showMessage(f"导出完成，{queue_size} 个任务等待下载...", 0)
            
            # 如果当前没有在下载，开始处理队列
            if not self._is_downloading:
                self._process_download_queue()
        else:
            # 导出失败
            self.statusBar().showMessage(f"导出失败: {export_message}", 3000)
            print(f"[ERROR] 导出失败: {export_message}")
            QMessageBox.warning(self, "导出失败", f"设备导出失败: {export_message}")

    def _process_download_queue(self):
        """处理下载队列"""
        if not self._download_queue or self._is_downloading:
            return
        
        # 从队列中取出第一个任务
        take_name = self._download_queue.pop(0)
        print(f"[DEBUG] 开始处理下载队列中的任务: {take_name}")
        
        # 设置下载状态
        self._is_downloading = True
        
        # 更新状态栏
        queue_size = len(self._download_queue)
        if queue_size > 0:
            self.statusBar().showMessage(f"正在下载: {take_name} (队列中还有 {queue_size} 个任务)...", 0)
        else:
            self.statusBar().showMessage(f"正在下载: {take_name}...", 0)
        
        # 开始下载
        self._start_async_download(take_name)

    def _start_async_download(self, take_name):
        """异步启动下载，不阻塞UI"""
        try:
            print(f"[DEBUG] 开始异步下载: take_name={take_name}, path={self._export_target_path}")
            
            # 获取真正的CMAvatar设备对象（Python对象，有harvest方法）
            harvest_devices = [d for d in self.mod_peel.DEVICES if d.device() == "CMAvatar"]
            if len(harvest_devices) == 0:
                self.statusBar().showMessage("没有找到CMAvatar设备", 3000)
                return
            
            device = harvest_devices[0]
            download_path = os.path.join(self._export_target_path, device.name)
            
            print(f"[DEBUG] 调用 device.harvest with download_path={download_path}, take_name={take_name}")
            
            # 创建下载线程，确保传递take_name参数
            download_thread = device.harvest(download_path, take_name)
            
            # 连接信号
            download_thread.all_done.connect(lambda: self._on_download_completed(take_name))
            download_thread.tick.connect(self._on_download_progress)
            download_thread.file_done.connect(self._on_file_downloaded)
            download_thread.message.connect(self._on_download_message)
            
            # 启动下载线程
            download_thread.start()
            print(f"[DEBUG] 异步下载线程已启动: {take_name}")
            
        except Exception as e:
            print(f"[ERROR] 启动异步下载失败: {e}")
            self.statusBar().showMessage(f"启动下载失败: {e}", 3000)
    
    def _on_download_completed(self, take_name):
        """下载完成回调"""
        print(f"[DEBUG] 文件夹下载完成: {take_name}")
        self._will_save = True
        
        # 重置下载状态
        self._is_downloading = False
        
        # 更新状态栏
        queue_size = len(self._download_queue)
        if queue_size > 0:
            self.statusBar().showMessage(f"下载完成: {take_name}，继续处理队列中的 {queue_size} 个任务...", 2000)
            # 处理队列中的下一个任务
            self._process_download_queue()
        else:
            self.statusBar().showMessage(f"所有下载任务完成: {take_name}", 3000)
    
    def _on_download_progress(self, progress):
        """下载进度回调"""
        progress_percent = int(progress * 100)
        self.statusBar().showMessage(f"下载进度: {progress_percent}%", 0)
    
    def _on_file_downloaded(self, filename, status, error):
        """单个文件下载完成回调"""
        if status == 1:  # COPY_OK
            print(f"[DEBUG] 文件下载成功: {filename}")
        elif status == 0:  # COPY_FAIL
            print(f"[ERROR] 文件下载失败: {filename}, 错误: {error}")
        elif status == 2:  # COPY_SKIP
            print(f"[DEBUG] 文件跳过: {filename}")
    
    def _on_download_message(self, message):
        """下载消息回调"""
        print(f"[DEBUG] 下载消息: {message}")

    def check_device_connection(self):
        """检查CMAvatar设备连接状态"""
        if not self._all_device:
            return False, "没有添加CMAvatar设备"
        
        # 调试信息：打印所有设备信息
        print(f"[DEBUG] 总设备数量: {len(self._all_device)}")
        for i, d in enumerate(self._all_device):
            print(f"[DEBUG] 设备 {i}: name={d.name}, type={type(d)}, status={getattr(d, 'status', 'N/A')}")
        
        # 通过设备名称识别CMAvatar设备
        avatar_devices = [d for d in self._all_device if d.name == "CMAvatar"]
        
        print(f"[DEBUG] 找到的CMAvatar设备数量: {len(avatar_devices)}")
        
        if not avatar_devices:
            return False, "没有找到CMAvatar设备"
        
        avatar_device = avatar_devices[0]  # 只使用第一个CMAvatar设备
        
        print(f"[DEBUG] 选择的CMAvatar设备: name={avatar_device.name}, status={getattr(avatar_device, 'status', 'N/A')}")
        
        # 检查设备状态
        if hasattr(avatar_device, 'status'):
            device_status = avatar_device.status
            if device_status == "ONLINE":
                return True, f"CMAvatar设备在线: {avatar_device.name}"
            else:
                return False, f"CMAvatar设备离线: {avatar_device.name} (状态: {device_status})"
        
        return False, "无法获取CMAvatar设备状态"

    # 录制开始/停止
    def record_clicked(self):
        # 检查是否有选择任务
        if not self._edt_shotName.text().strip():
            QMessageBox.warning(self, "提示", "请先选择一个任务")
            return
        
        # 检查设备连接状态
        has_connection, message = self.check_device_connection()
        if not has_connection:
            QMessageBox.warning(self, "设备连接检查", message)
            return
            
        if self._recording:
            #录制中
            # 停止时仅依赖记录ID：取最后一条记录的record_id
            if not self._takelist:
                return
            last_take = self._takelist[-1]
            stop_id = last_take._record_id if hasattr(last_take, "_record_id") else None
            if stop_id is None:
                # 兜底用行号作为ID
                stop_id = len(self._takelist)
            self.mod_peel.command('stop', str(stop_id))
            # 已移除标题标签，无需设置样式
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
            self._btn_record.setEnabled(True)  # 重新启用录制按钮

            self.statusBar().showMessage("就绪...", 2000)
            self.update_tips("录制完成", 3000)  # 3秒后恢复默认
            self.highLightNoteInfo(-1)
            self.save(True)
        else:
            #未录制 - 开始倒计时
            shot_name = self._edt_shotName.text()
            take_no = 1
            self.start_countdown(3, "准备开始录制")
            # 禁用录制按钮防止重复点击
            self._btn_record.setEnabled(False)
            # 注意：计时器在倒计时结束后才启动，不在这里启动
            # 更新索引 - 使用当前任务信息
            self._dict_shotname.add_shot_with_take(shot_name, take_no)
            self.update_shotlist()
        self._will_save = True

    def UpdateActionInfo(self, row, startFrame, endFrame):
        print(f"[DEBUG] UpdateActionInfo: row={row}, startFrame={startFrame}, endFrame={endFrame}")
        actionName = "未知动作"  # 默认动作名称
        
        if 0 <= row < self._edt_notes.count():
            item_text = self._edt_notes.item(row).text()
            # 移除序号前缀 (例如 "1. " -> "")
            actionName = item_text[item_text.find('. ') + 2:] if '. ' in item_text else item_text
        
        actionInfo = ActionInfo(actionName, startFrame, endFrame)
        
        # 检查是否有正在录制的take
        if self._takelist and len(self._takelist) > 0:
            self._takelist[-1].add_action(actionInfo)
        else:
            print(f"警告: 没有正在录制的take，忽略动作回调 (row={row})")

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
            # 评分功能已移除
            self._will_save = True

        # self._table_takelist.setItem(lastRow, 5, QTableWidgetItem(str(take_last._due.seconds) + ' sec'))

    def update_tips(self, message, duration=0):
        """更新提示信息
        
        Args:
            message: 提示信息文本
            duration: 显示时长（毫秒），0表示永久显示
        """
        self._edt_tips.setPlainText(message)
        # 滚动到底部显示最新内容
        self._edt_tips.moveCursor(QTextCursor.End)
        if duration > 0:
            # 使用QTimer在指定时间后恢复默认提示
            QTimer.singleShot(duration, lambda: self._edt_tips.setPlainText("就绪"))

    def append_tips(self, message):
        """追加提示信息到现有内容
        
        Args:
            message: 要追加的提示信息文本
        """
        current_text = self._edt_tips.toPlainText()
        if current_text == "就绪":
            self._edt_tips.setPlainText(message)
        else:
            self._edt_tips.append(message)
        # 滚动到底部显示最新内容
        self._edt_tips.moveCursor(QTextCursor.End)

    def clear_tips(self):
        """清除提示信息，恢复默认状态"""
        self._edt_tips.setPlainText("就绪")

    def start_countdown(self, seconds=3, message="准备开始录制", auto_stop=False):
        """开始倒计时
        
        Args:
            seconds: 倒计时秒数，默认3秒
            message: 倒计时期间显示的消息
            auto_stop: 是否为自动停止模式
        """
        self._countdown_seconds = seconds
        self._countdown_is_auto_stop = auto_stop
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._update_countdown)
        
        # 显示倒计时标签和提示信息
        self._lbl_countdown.show()
        self.update_tips(f"{message}\n倒计时: {seconds}秒")
        self._lbl_countdown.setText(str(seconds))
        
        # 开始倒计时
        self._countdown_timer.start(1000)  # 每秒更新一次

    def _update_countdown(self):
        """更新倒计时显示"""
        self._countdown_seconds -= 1
        
        if self._countdown_seconds > 0:
            # 更新倒计时数字
            self._lbl_countdown.setText(str(self._countdown_seconds))
            # 更新提示信息
            if hasattr(self, '_countdown_is_auto_stop') and self._countdown_is_auto_stop:
                self.update_tips(f"录制即将结束\n倒计时: {self._countdown_seconds}秒")
            else:
                self.update_tips(f"准备开始录制\n倒计时: {self._countdown_seconds}秒")
        else:
            # 倒计时结束
            self._countdown_timer.stop()
            self._lbl_countdown.hide()
            if hasattr(self, '_countdown_is_auto_stop') and self._countdown_is_auto_stop:
                self.update_tips("录制完成！")
                # 触发自动停止录制
                self._on_auto_stop_countdown_finished()
            else:
                self.update_tips("录制开始！")
                # 这里可以触发实际的录制开始逻辑
                self._on_countdown_finished()

    def _on_countdown_finished(self):
        """倒计时结束后的回调，开始实际录制"""
        # 重新启用录制按钮
        self._btn_record.setEnabled(True)
        
        # 开始实际录制
        shot_name = self._edt_shotName.text()
        take_no = 1  # 固定为1
        record_id = len(self._takelist) + 1

        # 在开始录制前：从任务列表获取真实任务名称，创建后端 TaskInfo 并从数据库读取 task_name 与 episode_id
        episode_id_str = ""
        db_task_name = ""
        
        # 从任务列表组件获取真实的任务名称
        real_task_name = ""
        try:
            if hasattr(self, '_taskListWidget') and self._taskListWidget:
                task = self._taskListWidget.data_manager.get_task_by_id(shot_name)
                if task:
                    real_task_name = task.task_name_en or task.task_name_cn or shot_name
                else:
                    real_task_name = shot_name
            else:
                real_task_name = shot_name
        except Exception as e:
            real_task_name = shot_name
        
        # 在录制开始时保存到数据库，生成episode_id
        try:
            collector_id = 0
            if self.current_collector and isinstance(self.current_collector, dict):
                # 兼容登录返回结构：可能是 { 'collector_id': int, 'username': ... }
                collector_id = self.current_collector.get('collector_id') or self.current_collector.get('id') or 0
            # 使用业务 task_id 为 shot_name，task_name 使用真实的任务名称
            action_config = []
            init_scene_text = self._edt_desc.text() if hasattr(self, '_edt_desc') else ""
            task_status = 'pending'
            task_info_id = self.db_controller.save_full_episode(int(collector_id or 0), "", shot_name, real_task_name, init_scene_text, action_config, task_status)
            # 立即查询数据库，获取真实的 task_name 与 episode_id
            task_info = self.db_controller.get_task_info_by_task_id(shot_name)
            if task_info:
                # 后端视图按约定会返回包含 task_name 与 episode_id 的序列化数据
                db_task_name = str(task_info.get('task_name') or real_task_name)
                episode_id_val = task_info.get('episode_id')
                if episode_id_val is not None:
                    episode_id_str = str(episode_id_val)
        except Exception as e:
            # 若后端创建失败，不阻塞录制，仅回退使用空episode_id
            episode_id_str = ""
            db_task_name = real_task_name

        # 创建TakeItem来生成take_name
        temp_take_item = TakeItem(
            task_id=shot_name,
            task_name=db_task_name or real_task_name,
            episode_id=episode_id_str
        )
        
        # 使用TakeItem的take_name作为录制参数
        take_name = temp_take_item._take_name

        # for unreal（如仍需）
        self.mod_peel.command('shotName', shot_name)
        # common command
        self.mod_peel.command('takeNumber', take_no)
        self.mod_peel.command('record', take_name)
        # 不再显示标题标签，保持原有样式调用安全
        self._btn_record.setText('00:00:00')
        
        # 倒计时结束后才开始计时
        self._time_record.start(1000)
        self._recording = True

        # 倒计时结束后立即高亮第一条脚本
        try:
            if hasattr(self, '_edt_notes') and self._edt_notes.count() > 0:
                self.highLightNoteInfo(0)
        except Exception:
            pass

        strDesc = self._edt_desc.text()
        strNotes = '\n'.join(self.get_notes_text())
        
        # 使用新的构造函数创建TakeItem
        takeItem = TakeItem(
            task_id=shot_name,
            task_name=db_task_name or real_task_name,
            episode_id=episode_id_str,
            take_desc=strDesc,
            take_note=strNotes,
            record_id=record_id
        )
        
        self._takelist.append(takeItem)

        row_count = len(self._takelist)
        self._table_takelist.setRowCount(row_count)
        newRow = row_count - 1
        
        # 使用updateTakeRow方法统一更新
        self.updateTakeRow(newRow, takeItem)
        self._table_takelist.scrollToBottom()
        self.statusBar().showMessage("录制中...", 0)
        self.update_tips("正在录制中...")  # 永久显示直到停止
        #self._edt_notes.setReadOnly(True)

    def auto_stop_recording(self):
        """自动停止录制，由设备回调触发"""
        if not self._recording:
            return
            
        print("触发自动停止录制")
        
        # 更新提示信息
        self.update_tips("录制完成，即将结束...")
        
        # 开始3秒倒计时
        self.start_countdown(3, "录制即将结束", auto_stop=True)
        
    def _on_auto_stop_countdown_finished(self):
        """自动停止倒计时结束后的回调"""
        if not self._recording:
            return
            
        print("自动停止倒计时结束，执行停止录制")
        
        # 执行停止录制逻辑
        if not self._takelist:
            return
            
        last_take = self._takelist[-1]
        stop_id = last_take._record_id if hasattr(last_take, "_record_id") else None
        if stop_id is None:
            # 兜底用行号作为ID
            stop_id = len(self._takelist)
            
        self.mod_peel.command('stop', str(stop_id))
        
        # 更新UI状态
        self._btn_record.setText("录制")
        self._record_secord = 0
        self._recording = False

        self._time_record.stop()

        take_last = self._takelist[-1]
        take_last._end_time = datetime.now()
        take_last._due = (take_last._end_time - take_last._start_time).total_seconds()

        row_count = len(self._takelist)
        lastRow = row_count - 1

        # 使用updateTakeRow方法统一更新
        self.updateTakeRow(lastRow, take_last)
        self._table_takelist.scrollToBottom()
        
        # 更新提示信息
        self.update_tips("录制完成！")
        
        # 重新启用录制按钮
        self._btn_record.setEnabled(True)
        
        self.statusBar().showMessage("录制完成", 2000)
        #self.highLightNoteInfo()

        self._device_add.setEnabled(False)
        self._device_del.setEnabled(False)

        self._record_secord = 0
        
        # 自动保存到数据库（如果配置了自动保存）
        if hasattr(self, 'auto_save_to_db') and self.auto_save_to_db:
            self._auto_save_current_recording()

    def _auto_save_current_recording(self):
        """自动保存当前录制到数据库"""
        try:
            if not self._takelist:
                return
            
            # 获取最后一个录制的take
            last_take = self._takelist[-1]
            task_id = last_take._task_id
            
            # 检查是否有当前采集者
            if not self.current_collector:
                print("自动保存失败: 没有登录采集者")
                return
            
            # 保存到数据库
            success = self._save_task_to_database(task_id, [last_take])
            if success:
                print(f"自动保存任务 {task_id} 到数据库成功")
                self.append_tips(f"任务 {task_id} 已自动保存到数据库")
            else:
                print(f"自动保存任务 {task_id} 到数据库失败")
                self.append_tips(f"任务 {task_id} 自动保存到数据库失败")
                
        except Exception as e:
            print(f"自动保存到数据库失败: {e}")

    def cancel_countdown(self):
        """取消倒计时"""
        if hasattr(self, '_countdown_timer') and self._countdown_timer:
            self._countdown_timer.stop()
        self._lbl_countdown.hide()
        self.update_tips("倒计时已取消")

    def updateLabelTakeName(self):
        # 已移除标题控件，保留逻辑生成名称给内部使用
        # 不再更新任何标签，函数保留以兼容旧调用
        return

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
        
        # 更新初始设备列表，用于检测修改
        self.init_device_list = []
        for d in devices:
            self.init_device_list.append({
                'name': d.name,
                'address': d.address,
                'status': d.status
            })
        
        # 连接CMAvatar设备的信号
        self.connect_avatar_signals()

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
        
    