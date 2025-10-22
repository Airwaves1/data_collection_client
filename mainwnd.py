import sys, os, importlib, json, requests
from PySide6.QtCore import Qt, QTimer, QTime, QTranslator, Signal
from PySide6.QtGui import (QAction, QIcon, QKeySequence, QTextCursor, QTextCharFormat, QColor, QFont, QBrush)
from PySide6.QtWidgets import (QApplication, QDockWidget, QSplitter, QGridLayout, QLabel, QDialog, QMenu,
    QFileDialog, QMainWindow, QMessageBox, QWidget, QTableWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QSpacerItem, QSizePolicy, QHeaderView, QPushButton,
                   QLineEdit, QListWidget, QTextEdit, QComboBox, QProgressBar, QCheckBox, QDateTimeEdit)

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
from login_dialog import LoginDialog

import mylogger
from factory_widget import QtWidgetFactory
import app_const
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
        self._is_downloading = False  # 当前是否正在下载

        # 采集导出进度对话框状态
        self._collect_progress_dialog = None
        self._collect_total = 0
        self._collect_done = 0
        self._export_tasks = []  # 导出任务列表：[{"take_name": str, "status": str, "message": str}]

        self.init_device_list = []

        # 录制面板初始数据
        self.init_take_no = app_const.Defualt_Edit_Take_No
        # 不再保存项目级takename
        self.init_take_name = ""
        self.init_take_notes = ''
        self.init_take_desc = ''

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
        
        # 调试信息：打印用户信息
        print(f"[DEBUG] 登录成功的用户信息: {user_info}")
        
        # 更新状态栏显示当前用户
        self.statusBar().showMessage(f"当前用户: {user_info.get('collector_name', 'Unknown')}")
        
        # 更新右下角永久标签显示：组织_ID号_姓名
        collector_id = user_info.get('collector_id', 'Unknown')
        collector_name = user_info.get('collector_name', 'Unknown')
        collector_organization = user_info.get('collector_organization', 'Unknown')
        
        display_text = f"{collector_organization}_{collector_id}_{collector_name}"
        self._collector_label.setText(display_text)
        
        # 加载当前采集者的所有任务数据
        self.load_collector_tasks()
        
        # 可以在这里添加其他登录后的初始化操作
        mylogger.info(f"用户登录成功: {user_info.get('username', 'Unknown')}")
        
    def check_login_status(self):
        """检查登录状态"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "未登录", "请先登录后再进行操作")
            return False
        return True

    def load_collector_tasks(self):
        """加载当前采集者的任务数据（使用当前时间段筛选）"""
        if not self.current_collector:
            print("[WARN] 没有当前采集者信息，无法加载任务数据")
            return
        
        try:
            collector_id = self.current_collector.get('collector_id')
            if not collector_id:
                print("[WARN] 采集者ID为空，无法加载任务数据")
                return
            
            print(f"[INFO] 开始加载采集者 {collector_id} 的任务数据...")
            
            # 获取当前时间段筛选器的时间范围
            start_time = self._start_datetime.dateTime().toPython()
            end_time = self._end_datetime.dateTime().toPython()
            
            print(f"[DEBUG] 使用时间段筛选: {start_time} 到 {end_time}")
            
            # 使用时间段筛选获取任务列表
            tasks = self.db_controller.list_tasks_by_collector_with_time_range(
                collector_id, start_time, end_time, limit=1000, offset=0
            )
            
            if not tasks:
                print("[INFO] 指定时间段内没有找到任务数据")
                return
            
            print(f"[INFO] 找到 {len(tasks)} 个任务，开始转换...")
            
            # 清空当前任务列表
            self._takelist.clear()
            self._dict_takename.clear()
            
            # 按创建时间排序（最新的在前）
            def sort_key(task):
                created_at = task.get('created_at', '')
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime
                        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        return datetime.min
                elif created_at:
                    return created_at
                else:
                    return datetime.min
            
            tasks.sort(key=sort_key, reverse=True)
            
            # 转换数据库任务为TakeItem对象
            for task_data in tasks:
                try:
                    take_item = self._convert_db_task_to_take_item(task_data)
                    if take_item:
                        self._takelist.append(take_item)
                        # 添加到字典中用于查找
                        self._dict_takename[take_item._task_id] = take_item
                except Exception as e:
                    print(f"[ERROR] 转换任务数据失败: {task_data.get('task_id', 'Unknown')}, 错误: {e}")
                    continue
            
            # 更新UI显示
            self._update_task_list_ui()
            
            print(f"[INFO] 成功加载 {len(self._takelist)} 个任务到任务列表")
            
        except Exception as e:
            print(f"[ERROR] 加载采集者任务数据失败: {e}")
            QMessageBox.warning(self, "加载失败", f"加载任务数据失败: {e}")

    def _convert_db_task_to_take_item(self, task_data):
        """将数据库任务数据转换为TakeItem对象"""
        try:
            # 创建TakeItem对象
            take_item = TakeItem()
            
            # 设置基本信息
            take_item._task_id = str(task_data.get('task_id', ''))
            # 使用数据库中的任务名称（现在保存的是中文名称，如果有的话）
            take_item._task_name = task_data.get('task_name', '')
            take_item._episode_id = task_data.get('episode_id', '')
            
            # 设置时间信息
            created_at = task_data.get('created_at')
            recording_end_time = task_data.get('recording_end_time')
            
            if created_at:
                if isinstance(created_at, str):
                    # 如果是字符串，尝试解析
                    from datetime import datetime
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now()
                take_item._start_time = created_at
            else:
                take_item._start_time = datetime.now()
            
            # 设置结束时间
            if recording_end_time:
                if isinstance(recording_end_time, str):
                    from datetime import datetime
                    try:
                        recording_end_time = datetime.fromisoformat(recording_end_time.replace('Z', '+00:00'))
                    except:
                        recording_end_time = take_item._start_time
                take_item._end_time = recording_end_time
                print(f"[DEBUG] 设置结束时间: {take_item._end_time}")
            else:
                take_item._end_time = take_item._start_time
                print(f"[DEBUG] 没有录制结束时间，使用开始时间: {take_item._end_time}")
            
            # 计算持续时间（暂时设为0）
            take_item._due = 0.0
            
            # 设置其他信息
            take_item._take_notes = task_data.get('init_scene_text', '')
            take_item._take_desc = task_data.get('task_name', '')
            
            # 设置动作配置
            action_config = task_data.get('action_config', [])
            if isinstance(action_config, str):
                try:
                    import json
                    action_config = json.loads(action_config)
                except:
                    action_config = []
            take_item._actions = action_config if isinstance(action_config, list) else []
            
            # 设置任务状态
            take_item._task_status = task_data.get('task_status', 'pending')
            # 设置是否已导出（用于主界面着色）
            try:
                take_item._exported = bool(task_data.get('exported', False))
            except Exception:
                take_item._exported = False
            
            # 设置默认导出勾选状态
            take_item._export_selected = True
            
            # 生成take_name
            take_item._generate_take_name()
            
            return take_item
            
        except Exception as e:
            print(f"[ERROR] 转换任务数据失败: {e}")
            return None

    def _update_task_list_ui(self):
        """更新任务列表UI显示"""
        try:
            row_count = len(self._takelist)
            self._table_takelist.setRowCount(row_count)
            
            # 更新每一行
            for row, take_item in enumerate(self._takelist):
                self.updateTakeRow(row, take_item)
            
            print(f"[INFO] 任务列表UI已更新，显示 {row_count} 个任务")
            # 应用导出着色（确保从数据库加载时也能正确着色）
            self._apply_exported_coloring_to_main_list()
            
        except Exception as e:
            print(f"[ERROR] 更新任务列表UI失败: {e}")

    def _apply_exported_coloring_to_main_list(self):
        """根据 _takelist 中的 _exported 状态，为主界面列表逐行着色"""
        try:
            if not hasattr(self, '_table_takelist') or not self._table_takelist:
                return
            total_rows = min(self._table_takelist.rowCount(), len(self._takelist))
            for row in range(total_rows):
                take_item = self._takelist[row]
                exported_status = getattr(take_item, '_exported', False)
                # 更新是否导出列（第7列）
                exported_item = self._table_takelist.item(row, 7)
                if exported_item:
                    exported_item.setText("True" if exported_status else "False")
                    if exported_status:
                        exported_item.setForeground(QColor(100, 149, 237))  # 淡蓝色
                    else:
                        exported_item.setForeground(QColor(255, 255, 255))  # 白色
        except Exception as e:
            print(f"[ERROR] 应用导出着色失败: {e}")

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
            self._takelist = []
            self._all_device = []
            self.init_device_list = []  # 重置初始设备列表
            
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
        
        return False

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

        # 清空录制列表
        self._takelist.clear()
        
        # 设置UI状态：不从项目文件填充描述与脚本
        self._table_takelist.setRowCount(0)

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
        # 导出勾选框
        checkbox = QCheckBox()
        # 根据take_item的_export_selected属性设置勾选状态
        export_selected = getattr(take_item, '_export_selected', True)
        checkbox.setChecked(export_selected)
        # 设置勾选框样式为透明背景，保持原始勾选效果
        checkbox.setStyleSheet("""
            QCheckBox {
                background: transparent;
            }
        """)
        # 连接勾选状态变更事件（以录制ID作为标识）
        checkbox.stateChanged.connect(lambda state, r=row: self.on_export_checkbox_changed(r, state))
        self._table_takelist.setCellWidget(row, 0, checkbox)
        
        print(f"[DEBUG] updateTakeRow: 第{row}行任务 {take_item._task_id} 勾选框设置为: {export_selected}")
        
        # 任务ID
        twItem = QTableWidgetItem(take_item._task_id)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 1, twItem)

        # 录制ID (episode_id)
        episode_id = getattr(take_item, '_episode_id', '')
        twItem = QTableWidgetItem(episode_id)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 2, twItem)

        # 任务名称
        twItem = QTableWidgetItem(take_item._task_name)
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        # 若已导出，则着色为暗蓝色（白字）
        if getattr(take_item, '_exported', False):
            twItem.setBackground(QColor(10, 36, 106))
            twItem.setForeground(QColor(255, 255, 255))
        self._table_takelist.setItem(row, 3, twItem)
        
        # 开始时间
        twItem = QTableWidgetItem(take_item._start_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 4, twItem)

        # 结束时间
        twItem = QTableWidgetItem(take_item._end_time.strftime('%H:%M:%S'))
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        self._table_takelist.setItem(row, 5, twItem)
        
        # 是否导出
        exported_status = getattr(take_item, '_exported', False)
        twItem = QTableWidgetItem("True" if exported_status else "False")
        twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
        # 根据导出状态设置字体颜色
        if exported_status:
            twItem.setForeground(QColor(100, 149, 237))  # 淡蓝色
        else:
            twItem.setForeground(QColor(255, 255, 255))  # 白色
        self._table_takelist.setItem(row, 6, twItem)
        
        # 状态下拉框（仅两个选项，默认"接受"）
        status_combo = QComboBox()
        status_combo.addItems(["接受", "拒绝"])  # 仅保留两个选项
        status_combo.setCurrentText("接受")
        
        # 设置下拉框样式为透明背景，保持原始样式
        status_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                font-size: 11px;
            }
        """)
        
        # 连接状态变更事件
        status_combo.currentTextChanged.connect(lambda text, r=row: self.on_status_changed(r, text))
        
        self._table_takelist.setCellWidget(row, 7, status_combo)

    def on_export_checkbox_changed(self, row, state):
        """处理导出勾选框状态变更事件"""
        try:
            if 0 <= row < len(self._takelist):
                take_item = self._takelist[row]
                is_checked = state == Qt.Checked
                # 同步更新TakeItem的勾选状态
                take_item._export_selected = is_checked
                episode_id = getattr(take_item, '_episode_id', '')
                print(f"[DEBUG] 录制 {episode_id} 导出状态变更: {'勾选' if is_checked else '取消勾选'}")
        except Exception as e:
            print(f"[ERROR] 处理导出勾选框状态变更失败: {e}")

    def on_status_changed(self, row, status_text):
        """处理状态变更事件"""
        try:
            if 0 <= row < len(self._takelist):
                take_item = self._takelist[row]

                # 将中文状态转换为英文状态
                status_map = {
                    "接受": "accepted",
                    "拒绝": "rejected"
                }
                new_status = status_map.get(status_text, "accepted")

                # 更新TakeItem状态
                take_item._task_status = new_status

                print(f"任务 {take_item._task_id} 状态已更新为: {status_text} ({new_status})")

                # 如果任务已保存到数据库，则更新数据库状态
                if hasattr(take_item, '_episode_id') and take_item._episode_id:
                    self._update_task_status_in_db(take_item._episode_id, new_status)
        except Exception as e:
            print(f"更新状态失败: {e}")

    def _update_task_status_in_db(self, episode_id, status):
        """更新数据库中的任务状态"""
        try:
            if self.db_controller:
                success = self.db_controller.update_task_status(episode_id, status)
                if success:
                    print(f"数据库任务 {episode_id} 状态已更新为: {status}")
                else:
                    print(f"更新数据库任务 {episode_id} 状态失败")
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
        
        # 只保存设备配置信息，不包含takes数据
        devices = self.mod_peel.get_device_config_data()
        
        # 获取表格文件路径
        excel_file_path = ""
        if hasattr(self, '_taskListWidget') and self._taskListWidget:
            # 获取当前加载的Excel文件路径（如果有的话）
            excel_file_path = getattr(self._taskListWidget, '_current_excel_path', "")
        
        json_data = { 
                     'devices': devices,
                     'excel_file_path': excel_file_path
                     }
        
        save_result = app_json.save_json_file(self._save_fullpath, json_data)
        if save_result == False:
            QMessageBox.warning(self, AppName, self.tr("Project file saved failed: ") + self._save_fullpath)

        return save_result

    def collect_file(self):
        """收集文件：驱动设备导出，监听回调，发送给fileservice"""
        # 若正在等待上一次导出回调，阻止重复触发
        if getattr(self, '_waiting_for_export', False):
            self.statusBar().showMessage("正在等待设备导出完成，请稍后再试...", 3000)
            return
        # 检查是否有设备连接
        has_connection, message = self.check_device_connection()
        if not has_connection:
            QMessageBox.warning(self, "设备连接检查", message)
            return
        
        # 连接CMAvatar设备信号（如果还没有连接）
        self.connect_avatar_signals()
        
        # 计算本次需要导出的总数（以当前录制条目数为准）
        try:
            # 在导出前，用UI勾选框状态回写_take_item._export_selected，确保设备侧读取一致
            for row in range(self._table_takelist.rowCount()):
                if row < len(self._takelist):
                    take_item = self._takelist[row]
                    checkbox = self._table_takelist.cellWidget(row, 0)
                    if checkbox and hasattr(checkbox, 'isChecked'):
                        take_item._export_selected = bool(checkbox.isChecked())

            # 获取所有勾选的任务 - 直接检查UI勾选框状态
            self._export_tasks = []
            for row in range(self._table_takelist.rowCount()):
                if row < len(self._takelist):
                    take_item = self._takelist[row]
                    # 检查UI勾选框状态（第0列）
                    checkbox = self._table_takelist.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        self._export_tasks.append({
                            'take_name': take_item._take_name,
                            'status': 'waiting',
                            'message': '等待导出'
                        })
            
            self._collect_total = len(self._export_tasks)
            if self._collect_total == 0:
                QMessageBox.warning(self, "导出提示", "没有选择要导出的任务")
                return
        except Exception as e:
            print(f"[ERROR] 初始化导出任务失败: {e}")
            self._collect_total = 1
            self._export_tasks = [{'take_name': '未知任务', 'status': 'waiting', 'message': '等待导出'}]
        self._collect_done = 0
        self._show_collect_progress_dialog()

        # 发送导出命令（设备将按任务逐条回调 exportFinish，多次触发）
        # try:
        self.mod_peel.command('Export', '')
        self.statusBar().showMessage("已发送导出命令，等待设备回调...", 3000)
        # except Exception as e:
        #     print(f"[ERROR] 发送导出命令失败: {e}")
        #     QMessageBox.warning(self, "导出失败", f"发送导出命令失败: {e}")
        #     return

    def _on_export_timeout(self):
        """导出超时处理（已不使用）"""
        self.statusBar().showMessage("导出超时", 2000)

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
            print(f"[DEBUG] 尝试获取任务信息: task_id={task_id}")
            print(f"[DEBUG] _taskListWidget存在: {hasattr(self, '_taskListWidget')}")
            if hasattr(self, '_taskListWidget'):
                print(f"[DEBUG] _taskListWidget不为空: {self._taskListWidget is not None}")
                if self._taskListWidget:
                    print(f"[DEBUG] data_manager存在: {hasattr(self._taskListWidget, 'data_manager')}")
                    if hasattr(self._taskListWidget, 'data_manager'):
                        task = self._taskListWidget.data_manager.get_task_by_id(task_id)
                        if task:
                            task_info = {
                                'task_name_en': task.task_name_en,
                                'task_name_cn': task.task_name_cn,
                                'scenarios': task.scenarios,
                                'action_text_en': task.action_text_en,
                                'action_text_cn': task.action_text_cn
                            }
                            print(f"[DEBUG] 获取到任务信息: task_id={task_id}, task_name_cn={task.task_name_cn}, task_name_en={task.task_name_en}")
                            return task_info
                        else:
                            print(f"[DEBUG] 未找到任务 {task_id}")
                    else:
                        print(f"[DEBUG] data_manager不存在")
                else:
                    print(f"[DEBUG] _taskListWidget为空")
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
                
                # 优先使用中文任务名称，如果没有则使用英文名称
                task_name_cn = self._clean_text(task_info.get('task_name_cn', ''))
                task_name_en = self._clean_text(task_info.get('task_name_en', ''))
                
                # 确定最终使用的任务名称（优先中文）
                final_task_name = task_name_cn if task_name_cn else task_name_en
                if not final_task_name:
                    final_task_name = self._clean_text(take_item._take_desc)
                
                # 使用场景信息
                scene_text = self._clean_text(task_info.get('scenarios', ''))
                if not scene_text:
                    scene_text = f"Task {task_id}: {final_task_name}"
                
                # 更新现有的TaskInfo记录，而不是创建新的
                update_data = {
                    'task_name': final_task_name,  # 保存中文名称（如果有的话）
                    'task_name_cn': task_name_cn,  # 保存中文名称
                    'init_scene_text': scene_text,
                    'action_config': action_config,
                    'task_status': 'pending',  # 默认为待审核状态
                    'recording_end_time': take_item._end_time.isoformat()  # 保存录制结束时间（转换为ISO格式字符串）
                }
                
                print(f"[DEBUG] 保存任务到数据库: task_id={task_id}, task_name_cn={task_name_cn}, recording_end_time={take_item._end_time}")
                
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
                statusTip=self.tr("将录制文件下载保存"), triggered=self.collect_file)

        icon = QIcon(':/images/export_files')
        self._export_file_act = QAction(icon, self.tr("Export File"), self, shortcut="Ctrl+B",
                statusTip=self.tr("从服务器导出文件到指定文件夹"), triggered=self.export_file)

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
        self._file_tool_bar.addAction(self._export_file_act)

    def create_status_bar(self):
        self.statusBar().showMessage("就绪...", 2000)
        # 显示当前采集者
        self._collector_label = QLabel(self.tr("未登录采集者"))
        # 设置右边距，避免文字太靠右
        self._collector_label.setStyleSheet("QLabel { margin-right: 20px; }")
        self.statusBar().addPermanentWidget(self._collector_label)

    def create_takelist(self, splitter):
        # 创建 QTableWidget
        takelistWidget = QTableWidget(splitter)
        # 设置列名 - 优化后的列名，添加勾选框列
        header_labels = ["导出", 
                         "任务ID", 
                         "录制ID", 
                         "任务名称", 
                         "开始时间", 
                         "结束时间", 
                         "是否导出",
                         "状态"]
        takelistWidget.setColumnCount(len(header_labels))
        takelistWidget.setHorizontalHeaderLabels(header_labels)
        
        # 为导出列设置固定宽度，为按钮预留空间
        takelistWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        takelistWidget.setColumnWidth(0, 100)  # 设置导出列宽度
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
        takelistWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 导出勾选框
        takelistWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 任务ID
        takelistWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 录制ID
        takelistWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)           # 任务名称
        takelistWidget.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 开始时间
        takelistWidget.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 结束时间
        takelistWidget.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 是否导出
        takelistWidget.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 状态

        # 设置行高
        takelistWidget.verticalHeader().setDefaultSectionSize(32)  # 设置默认行高为32px

        return takelistWidget


    def create_time_filter_widget(self, splitter):
        """创建时间段筛选组件"""
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        
        # 开始时间标签
        start_label = QLabel("开始时间:")
        filter_layout.addWidget(start_label)
        
        # 开始日期时间选择器
        self._start_datetime = QDateTimeEdit()
        self._start_datetime.setDisplayFormat("yyyy-MM-dd hh:mm")
        self._start_datetime.setCalendarPopup(True)
        # 设置为当天开始时间
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._start_datetime.setDateTime(today)
        filter_layout.addWidget(self._start_datetime)
        
        # 结束时间标签
        end_label = QLabel("结束时间:")
        filter_layout.addWidget(end_label)
        
        # 结束日期时间选择器
        self._end_datetime = QDateTimeEdit()
        self._end_datetime.setDisplayFormat("yyyy-MM-dd hh:mm")
        self._end_datetime.setCalendarPopup(True)
        # 设置为当天结束时间
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
        self._end_datetime.setDateTime(today_end)
        filter_layout.addWidget(self._end_datetime)
        
        # 筛选按钮
        filter_btn = QPushButton("筛选")
        filter_btn.clicked.connect(self.apply_time_filter)
        filter_layout.addWidget(filter_btn)
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_time_filter)
        filter_layout.addWidget(reset_btn)
        
        # 分隔线
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; font-weight: bold;")
        filter_layout.addWidget(separator)
        
        # 全选导出按钮
        select_all_btn = QPushButton("全选导出")
        select_all_btn.clicked.connect(self.select_all_export)
        filter_layout.addWidget(select_all_btn)
        
        # 取消全选导出按钮
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all_export)
        filter_layout.addWidget(deselect_all_btn)
        
        # 添加弹性空间
        filter_layout.addStretch()
        
        return filter_widget

    def select_all_export(self):
        """全选所有导出任务"""
        try:
            for row in range(self._table_takelist.rowCount()):
                checkbox = self._table_takelist.cellWidget(row, 0)
                if checkbox and hasattr(checkbox, 'setChecked'):
                    checkbox.setChecked(True)
                    # 同时更新TakeItem的_export_selected属性
                    if row < len(self._takelist):
                        take_item = self._takelist[row]
                        take_item._export_selected = True
        except Exception as e:
            print(f"[ERROR] 全选导出任务失败: {e}")

    def deselect_all_export(self):
        """取消全选所有导出任务"""
        try:
            for row in range(self._table_takelist.rowCount()):
                checkbox = self._table_takelist.cellWidget(row, 0)
                if checkbox and hasattr(checkbox, 'setChecked'):
                    checkbox.setChecked(False)
                    # 同时更新TakeItem的_export_selected属性
                    if row < len(self._takelist):
                        take_item = self._takelist[row]
                        take_item._export_selected = False
        except Exception as e:
            print(f"[ERROR] 取消全选导出任务失败: {e}")

    def apply_time_filter(self):
        """应用时间段筛选"""
        try:
            if not self.current_collector:
                QMessageBox.warning(self, "筛选提示", "请先登录采集者")
                return
            
            # 获取时间范围
            start_time = self._start_datetime.dateTime().toPython()
            end_time = self._end_datetime.dateTime().toPython()
            
            print(f"[DEBUG] 应用时间段筛选: {start_time} 到 {end_time}")
            
            # 调用数据库控制器获取筛选后的任务
            collector_id = self.current_collector.get('collector_id')
            if collector_id:
                # 这里需要修改API调用，传递时间参数
                tasks_data = self.db_controller.list_tasks_by_collector_with_time_range(
                    collector_id, start_time, end_time
                )
                
                if tasks_data:
                    # 清空当前列表
                    self._takelist.clear()
                    
                    # 转换并添加任务
                    for task_data in tasks_data:
                        take_item = self._convert_db_task_to_take_item(task_data)
                        if take_item:
                            self._takelist.append(take_item)
                    
                    # 更新UI
                    self._update_task_list_ui()
                    print(f"[INFO] 筛选完成，显示 {len(self._takelist)} 个任务")
                else:
                    print("[INFO] 筛选结果为空")
                    self._takelist.clear()
                    self._update_task_list_ui()
            else:
                print("[ERROR] 无法获取采集者ID")
                
        except Exception as e:
            print(f"[ERROR] 应用时间段筛选失败: {e}")
            QMessageBox.warning(self, "筛选失败", f"筛选失败: {e}")

    def reset_time_filter(self):
        """重置时间段筛选"""
        try:
            # 重置为当天开始到结束
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
            
            self._start_datetime.setDateTime(today)
            self._end_datetime.setDateTime(today_end)
            
            # 重新加载任务列表
            if self.current_collector:
                self.load_collector_tasks()
            
            print("[DEBUG] 时间段筛选已重置")
            
        except Exception as e:
            print(f"[ERROR] 重置时间段筛选失败: {e}")
    
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
                take_item = self._takelist.pop(row)
                # 删除设备中的take数据
                if getattr(take_item, "_take_name", None):
                    self.delete_device_take(take_item._take_name)
            
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
        tips_content = """1. 点击开始录制有3秒准备等待时间。
2. 点击停止录制有3秒结束等待时间。
"""
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

        # 创建时间段筛选组件
        self._time_filter_widget = self.create_time_filter_widget(splitter)
        
        self._table_takelist = self.create_takelist(splitter)
        self._widget_recordPanel = self.create_recordpanel(splitter)

        # 创建布局
        #layout = QVBoxLayout()
        splitter.addWidget(self._time_filter_widget)
        splitter.addWidget(self._table_takelist)
        splitter.addWidget(self._widget_recordPanel)

        # 设置 QSplitter 的尺寸
        splitter.setSizes([50, 300, 500])  # 筛选组件50px，任务列表300px，录制面板500px

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
    

    def connect_avatar_signals(self):
        """连接CMAvatar设备的信号"""
        # 连接CMAvatar设备信号
        
        # 从peel模块获取真正的设备对象
        try:
            # 使用主窗口已经导入的peel模块的DEVICES（DeviceCollection）
            if hasattr(self.mod_peel, 'DEVICES') and self.mod_peel.DEVICES:
                # 调试：设备数量
                
                # 查找CMAvatar设备（真正的Python设备对象）
                avatar_devices = [d for d in self.mod_peel.DEVICES if d.device() == "CMAvatar"]
                # 调试：找到的CMAvatar设备数量
                
                for avatar_device in avatar_devices:
                    # 处理找到的设备
                    print(f"[DEBUG] 设备类型: {type(avatar_device)}")
                    if hasattr(avatar_device, 'export_completed'):
                        try:
                            # 断开之前的连接（如果有的话）
                            avatar_device.export_completed.disconnect()
                            # 清理旧连接
                        except TypeError:
                            # 如果没有连接过，会抛出TypeError，忽略即可
                            print(f"[DEBUG] 没有之前的信号连接")
                            pass
                        
                        # 连接新的信号
                        avatar_device.export_completed.connect(self._on_avatar_export_completed)
                        # 信号连接成功
                        
                        # 连接设备主动停止录制信号
                        if hasattr(avatar_device, 'recording_stopped'):
                            try:
                                avatar_device.recording_stopped.disconnect()
                            except TypeError:
                                pass
                            avatar_device.recording_stopped.connect(self._on_avatar_recording_stopped)
                            print(f"[DEBUG] 已连接Avatar设备停止录制信号")
                        print(f"[DEBUG] 设备对象: {avatar_device}")
                        # 信号对象
                    else:
                        print(f"[ERROR] 设备 {avatar_device.name} 没有 export_completed 信号")
            else:
                print(f"[ERROR] mod_peel.DEVICES 为空或不存在")
        except Exception as e:
            print(f"[ERROR] 获取设备失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_avatar_recording_stopped(self):
        """处理Avatar设备主动停止录制的信号"""
        print("[DEBUG] 收到Avatar设备主动停止录制信号")
        self._handle_device_stop_recording()

    def _on_avatar_export_completed(self, export_result, export_message, take_name, file_paths=None):
        """处理CMAvatar设备导出完成回调"""
        print(f"[DEBUG] 收到导出完成回调: result={export_result}, message={export_message}, take_name={take_name}, file_paths={file_paths}")
        # 无论成功失败，结束等待状态
        self._waiting_for_export = False
        
        # 更新任务状态
        self._update_task_status(take_name, export_result, export_message)
        
        if export_result and take_name and file_paths:
            # 停止超时定时器
            if hasattr(self, '_export_timeout_timer') and self._export_timeout_timer is not None:
                try:
                    self._export_timeout_timer.stop()
                    print(f"[DEBUG] 停止导出超时定时器")
                except Exception as e:
                    print(f"[DEBUG] 停止超时定时器失败: {e}")
            
            # 导出成功，发送给fileservice
            print(f"[DEBUG] 导出完成，发送给fileservice: {take_name}, 文件数量: {len(file_paths)}")
            self._send_to_fileservice(take_name, file_paths)

            # 标记后端 exported=true，并更新UI着色
            try:
                # 从 _takelist 中找到此 take 的 episode_id
                episode_id = None
                for ti in self._takelist:
                    if getattr(ti, '_take_name', '') == take_name:
                        episode_id = getattr(ti, '_episode_id', None)
                        # 本地状态标记为已导出，便于立即刷新主列表着色
                        setattr(ti, '_exported', True)
                        break
                if episode_id:
                    # 调用后端置导出标志
                    if hasattr(self, 'db_controller') and self.db_controller:
                        self.db_controller.set_task_exported(episode_id, True)
                    # 主界面take列表着色（通过列2匹配episode_id，给列3着色）
                    self._mark_take_exported_in_main_list(episode_id)
                    # 更新导出进度弹窗内该行的颜色（任务名称列）
                    if hasattr(self, '_export_table') and self._export_table:
                        row_count = self._export_table.rowCount()
                        for r in range(row_count):
                            name_item = self._export_table.item(r, 0)
                            if name_item and name_item.text() == take_name:
                                name_item.setBackground(QColor(10, 36, 106))  # 暗蓝色
                                name_item.setForeground(QColor(255, 255, 255))  # 白字以便可读
                                break
                else:
                    print(f"[WARN] 未找到对应的episode_id用于设置exported: {take_name}")
            except Exception as e:
                print(f"[ERROR] 设置导出标志或更新着色失败: {e}")
        else:
            # 导出失败
            self.statusBar().showMessage(f"导出失败: {export_message}", 3000)
            print(f"[ERROR] 导出失败: {export_message}")

    def _mark_take_exported_in_main_list(self, episode_id: str):
        """在主界面take列表中，依据episode_id精确匹配并将是否导出列更新为True"""
        try:
            if not hasattr(self, '_table_takelist') or not self._table_takelist:
                return
            for row in range(self._table_takelist.rowCount()):
                item_episode = self._table_takelist.item(row, 2)  # 列2是录制ID(episode_id)
                if item_episode and item_episode.text() == str(episode_id):
                    # 更新是否导出列（第7列）
                    exported_item = self._table_takelist.item(row, 7)
                    if exported_item:
                        exported_item.setText("True")
                        exported_item.setForeground(QColor(100, 149, 237))  # 淡蓝色
                    break
        except Exception as e:
            print(f"[ERROR] 主界面着色失败: {e}")

    def _update_task_status(self, take_name, success, message):
        """更新导出任务状态"""
        try:
            # 查找对应的任务
            for task in self._export_tasks:
                if task['take_name'] == take_name:
                    if success:
                        task['status'] = 'success'
                        task['message'] = '导出成功'
                    else:
                        task['status'] = 'failed'
                        task['message'] = f'导出失败: {message}'
                    break
            
            # 更新表格显示
            self._update_export_table()
            # 若成功则在表格中将名称列标记为暗蓝色
            if success and hasattr(self, '_export_table') and self._export_table:
                row_count = self._export_table.rowCount()
                for r in range(row_count):
                    name_item = self._export_table.item(r, 0)
                    if name_item and name_item.text() == take_name:
                        name_item.setBackground(QColor(10, 36, 106))
                        name_item.setForeground(QColor(255, 255, 255))
                        break
            
            # 检查是否所有任务都完成了
            all_completed = all(task['status'] in ['success', 'failed'] for task in self._export_tasks)
            if all_completed:
                self.statusBar().showMessage("所有任务导出完成", 3000)
                
        except Exception as e:
            print(f"[ERROR] 更新任务状态失败: {e}")

    def _show_collect_progress_dialog(self):
        """显示非模态采集导出进度对话框，以列表形式显示任务状态"""
        try:
            if self._collect_progress_dialog is None:
                dlg = QDialog(self)
                dlg.setWindowTitle("导出进度")
                dlg.setModal(False)
                dlg.resize(500, 400)
                
                # 构建UI
                layout = QVBoxLayout(dlg)
                
                # 标题
                title_label = QLabel("正在导出任务...")
                title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
                layout.addWidget(title_label)
                
                # 任务列表
                self._export_table = QTableWidget()
                self._export_table.setColumnCount(2)
                self._export_table.setHorizontalHeaderLabels(["任务名称", "状态"])
                self._export_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                self._export_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
                self._export_table.setAlternatingRowColors(True)
                self._export_table.setSelectionBehavior(QTableWidget.SelectRows)
                layout.addWidget(self._export_table)
                
                # 关闭按钮
                close_btn = QPushButton("关闭")
                close_btn.clicked.connect(dlg.close)
                layout.addWidget(close_btn)
                
                # 保存引用
                dlg._export_table = self._export_table
                self._collect_progress_dialog = dlg
            
            # 初始化任务列表
            self._update_export_table()
            self._collect_progress_dialog.show()
        except Exception as e:
            print(f"[WARN] 显示进度对话框失败: {e}")

    def _update_export_table(self):
        """更新导出任务表格"""
        try:
            if not self._collect_progress_dialog or not hasattr(self, '_export_table'):
                return
            
            self._export_table.setRowCount(len(self._export_tasks))
            
            for row, task in enumerate(self._export_tasks):
                # 任务名称
                name_item = QTableWidgetItem(task['take_name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self._export_table.setItem(row, 0, name_item)
                
                # 状态
                status_item = QTableWidgetItem(task['message'])
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                
                self._export_table.setItem(row, 1, status_item)
            
            # 自动调整行高
            self._export_table.resizeRowsToContents()
            
        except Exception as e:
            print(f"[WARN] 更新导出表格失败: {e}")

    def _send_to_fileservice(self, take_name, file_paths):
        """发送文件路径给fileservice"""
        try:
            if not file_paths:
                print(f"[ERROR] 没有文件路径")
                return
            
            # 直接使用第一个文件路径（从日志看只有一个文件路径）
            file_path = file_paths[0]
            
            print(f"[DEBUG] 发送给fileservice: 文件路径={file_path}")
            
            # 获取CMAvatar设备的fileservice配置
            harvest_devices = [d for d in self.mod_peel.DEVICES if d.device() == "CMAvatar"]
            if len(harvest_devices) == 0:
                print(f"[ERROR] 没有找到CMAvatar设备")
                QMessageBox.warning(self, "设备错误", "没有找到CMAvatar设备")
                return
            
            device = harvest_devices[0]
            fileservice_url = f"http://{device.device_ip}:{device.fileservice_port}"
            
            print(f"[DEBUG] 使用fileservice URL: {fileservice_url}")
            
            # 准备发送给fileservice的数据
            upload_data = {
                "folder_paths": [file_path],  # 直接发送文件路径
                "auth_token": "default_token_123"
            }
            
            # 发送请求给fileservice
            response = requests.post(
                f"{fileservice_url}/fileservice/upload/",
                json=upload_data,
                timeout=20  # 增加超时时间到20秒，文件上传可能需要更长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result["task_id"]
                print(f"[DEBUG] Fileservice任务创建成功: {task_id}")
                self.statusBar().showMessage(f"文件已发送给fileservice，任务ID: {task_id}", 5000)
            else:
                print(f"[ERROR] Fileservice请求失败: {response.status_code}, {response.text}")
                self.statusBar().showMessage(f"发送给fileservice失败: {response.status_code}", 3000)
                QMessageBox.warning(self, "上传失败", f"发送给fileservice失败: {response.text}")
                
        except Exception as e:
            print(f"[ERROR] 发送给fileservice异常: {e}")
            self.statusBar().showMessage(f"发送给fileservice异常: {e}", 3000)
            QMessageBox.warning(self, "上传异常", f"发送给fileservice异常: {e}")


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
        
        # 调试：找到的CMAvatar设备数量
        
        if not avatar_devices:
            return False, "没有找到CMAvatar设备"
        
        avatar_device = avatar_devices[0]  # 只使用第一个CMAvatar设备
        
        print(f"[DEBUG] 选择的CMAvatar设备: name={avatar_device.name}, status={getattr(avatar_device, 'status', 'N/A')}")
        
        # 检查设备状态
        if hasattr(avatar_device, 'status'):
            device_status = avatar_device.status
            if device_status == "ONLINE" or device_status == "RECORDING":
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
        
        # 正在录制时，直接停止（不做设备连接检查，避免RECORDING被误判离线）
        if self._recording:
            # 录制中 - 停止录制
            self.stop_recording()
        else:
            # 仅在准备开始录制时检查设备连接
            has_connection, message = self.check_device_connection()
            if not has_connection:
                QMessageBox.warning(self, "设备连接检查", message)
                return
            # 未录制 - 开始录制
            self.start_recording()

    def start_recording(self):
        """开始录制流程"""
        print("[DEBUG] 开始录制流程")
        
        shot_name = self._edt_shotName.text()
        take_no = 1
        
        # 开始3秒倒计时
        self.start_countdown(3, "准备开始录制")
        
        # 禁用录制按钮防止重复点击
        self._btn_record.setEnabled(False)
        
        self._will_save = True

    def stop_recording(self):
        """停止录制流程（用户主动停止）"""
        print("[DEBUG] 用户主动停止录制流程")
        self._stop_recording_internal(user_initiated=True)

    def _stop_recording_internal(self, user_initiated=True):
        """内部停止录制流程
        
        Args:
            user_initiated: True表示用户主动停止，False表示设备主动停止
        """
        try:
            # 如果是用户主动停止，需要发送停止命令给设备
            if user_initiated:
                # 计算停止ID（若有正在记录的take则优先使用其record_id，否则兜底0或当前行数）
                stop_id = 0
                if self._takelist:
                    last_take = self._takelist[-1]
                    stop_id = getattr(last_take, "_record_id", None) or len(self._takelist)

                print(f"[DEBUG] 发送停止命令给设备，stop_id={stop_id}")
                self.mod_peel.command('stop', str(stop_id))
            else:
                print("[DEBUG] 设备主动停止，不发送停止命令")

            # 更新UI状态
            self._btn_record.setText("录制")
            self._record_secord = 0
            self._recording = False
            self._time_record.stop()

            # 若存在有效take，则更新结束时间与时长并刷新表格
            if self._takelist:
                take_last = self._takelist[-1]
                try:
                    take_last._end_time = datetime.now()
                    take_last._due = (take_last._end_time - take_last._start_time).total_seconds()

                    row_count = len(self._takelist)
                    lastRow = row_count - 1

                    str_end_time = take_last._end_time.strftime('%H:%M:%S')
                    twItem = QTableWidgetItem(str_end_time)
                    twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
                    self._table_takelist.setItem(lastRow, 4, twItem)

                    twItem = QTableWidgetItem(f"{'{:.1f}'.format(take_last._due)} sec")
                    twItem.setFlags(twItem.flags() & ~Qt.ItemIsEditable)
                    self._table_takelist.setItem(lastRow, 5, twItem)
                except Exception as e:
                    print(f"[WARN] 更新录制行显示失败: {e}")

            # 重新启用设备管理按钮与录制按钮
            self._device_add.setEnabled(True)
            self._device_del.setEnabled(True)
            self._btn_record.setEnabled(True)

            self.statusBar().showMessage("就绪...", 2000)
            self.update_tips("录制完成", 3000)
            self.save(True)

            # 保存任务到数据库（若有take）
            try:
                if self._takelist:
                    last_take = self._takelist[-1]
                    task_id = getattr(last_take, '_task_id', None)
                    if task_id is not None:
                        self._save_task_to_database(task_id, [last_take])
                        # 保存成功后，重新加载任务列表以显示最新数据
                        self.load_collector_tasks()
            except Exception as e:
                print(f"[WARN] 停止后保存数据库失败: {e}")
                
        except Exception as e:
            print(f"[ERROR] 停止录制流程失败: {e}")

    

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

    def start_countdown(self, seconds=3, message="准备开始录制"):
        """开始倒计时
        
        Args:
            seconds: 倒计时秒数，默认3秒
            message: 倒计时期间显示的消息
        """
        self._countdown_seconds = seconds
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
            self.update_tips(f"准备开始录制\n倒计时: {self._countdown_seconds}秒")
        else:
            # 倒计时结束
            self._countdown_timer.stop()
            self._lbl_countdown.hide()
            self.update_tips("录制开始！")
            # 触发实际的录制开始逻辑
            self._on_countdown_finished()

    def _on_countdown_finished(self):
        """倒计时结束后的回调，开始实际录制"""
        print("[DEBUG] 倒计时结束，开始录制")
        
        # 重新启用录制按钮
        self._btn_record.setEnabled(True)
        
        # 开始实际录制
        shot_name = self._edt_shotName.text()
        take_no = 1  # 固定为1
        record_id = len(self._takelist) + 1

        # 直接从任务模板获取中英文名称
        task_template = None
        task_name_en = ""
        task_name_cn = ""
        
        try:
            if hasattr(self, '_taskListWidget') and self._taskListWidget:
                task_template = self._taskListWidget.data_manager.get_task_by_id(shot_name)
                if task_template:
                    task_name_en = task_template.task_name_en
                    task_name_cn = task_template.task_name_cn
                    print(f"[DEBUG] 从任务模板获取: task_name_en={task_name_en}, task_name_cn={task_name_cn}")
                else:
                    print(f"[WARN] 未找到任务模板: {shot_name}")
                    task_name_en = shot_name  # 回退到任务ID
        except Exception as e:
            print(f"[ERROR] 获取任务模板失败: {e}")
            task_name_en = shot_name  # 回退到任务ID

        # 在录制开始时保存到数据库，同时保存中英文名称
        episode_id_str = ""
        try:
            collector_id = 0
            if self.current_collector and isinstance(self.current_collector, dict):
                collector_id = self.current_collector.get('collector_id') or self.current_collector.get('id') or 0
            
            action_config = []
            init_scene_text = self._edt_desc.text() if hasattr(self, '_edt_desc') else ""
            task_status = 'pending'
            
            # 保存到数据库，同时传递中英文名称
            task_info_id = self.db_controller.save_full_episode(
                int(collector_id or 0), 
                "", 
                shot_name, 
                task_name_en,  # 英文名称
                init_scene_text, 
                action_config, 
                task_status,
                task_name_cn    # 中文名称
            )
            
            # 获取episode_id
            task_info = self.db_controller.get_task_info_by_task_id(shot_name)
            if task_info:
                episode_id_val = task_info.get('episode_id')
                if episode_id_val is not None:
                    episode_id_str = str(episode_id_val)
                    print(f"[DEBUG] 获取到episode_id: {episode_id_str}")
        except Exception as e:
            print(f"[ERROR] 保存到数据库失败: {e}")
            episode_id_str = ""

        # 创建TakeItem（直接使用任务模板的数据）
        temp_take_item = TakeItem(
            task_id=shot_name,
            task_name=task_name_en,      # 直接使用英文名称
            episode_id=episode_id_str,
            take_name_cn=task_name_cn    # 直接使用中文名称
        )
        
        # 使用TakeItem的take_name作为录制参数
        take_name = temp_take_item._take_name

        # 发送录制命令
        self.mod_peel.command('shotName', shot_name)
        self.mod_peel.command('takeNumber', take_no)
        self.mod_peel.command('record', take_name)
        
        # 更新UI状态
        self._btn_record.setText('00:00:00')
        self._time_record.start(1000)
        self._recording = True
        
        # 禁用设备管理按钮
        self._device_add.setEnabled(False)
        self._device_del.setEnabled(False)
        
        # 更新状态栏
        self.statusBar().showMessage("正在录制...", 0)
        self.update_tips("录制中...")
        
        print(f"[DEBUG] 录制已开始: take_name={take_name}")

        # 已移除动作脚本的录制期高亮逻辑

        strDesc = self._edt_desc.text()
        strNotes = '\n'.join(self.get_notes_text())
        
        # 使用新的构造函数创建TakeItem（直接使用任务模板的数据）
        takeItem = TakeItem(
            task_id=shot_name,
            task_name=task_name_en,      # 直接使用英文名称
            episode_id=episode_id_str,
            take_desc=strDesc,
            take_note=strNotes,
            record_id=record_id,
            take_name_cn=task_name_cn    # 直接使用中文名称
        )
        
        # 设置默认导出勾选状态
        takeItem._export_selected = True
        
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

    def _handle_device_stop_recording(self):
        """处理设备主动停止录制的情况"""
        try:
            # 检查是否正在录制
            if not self._recording:
                print("[DEBUG] 当前没有在录制，忽略设备停止信号")
                return
            
            print("[DEBUG] 设备主动停止录制，执行停止录制流程")
            # 调用统一的停止录制流程，但不发送停止命令给设备
            self._stop_recording_internal(user_initiated=False)
                
        except Exception as e:
            print(f"[ERROR] 处理设备停止录制失败: {e}")

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
        
    