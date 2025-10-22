"""
数据导出管理器
负责调用后端导出API，下载生成的CMAvatar_data目录到本地
"""

import os
import json
import shutil
import glob
import requests
import zipfile
import tempfile
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup
from PySide6.QtCore import QCoreApplication, QThread, Signal, Qt


class ExportWorker(QThread):
    """导出工作线程"""
    export_progress_updated = Signal(int, str)  # 导出进度, 消息
    download_progress_updated = Signal(int, str)  # 下载进度, 消息
    export_completed = Signal(bool, str)  # 成功, 消息
    
    def __init__(self, api_client, export_dir, selected_tasks=None):
        super().__init__()
        self.api_client = api_client
        self.export_dir = export_dir
        self.selected_tasks = selected_tasks  # 勾选的任务列表
    
    def run(self):
        try:
            # 1. 启动后端导出
            self.export_progress_updated.emit(10, "正在启动后端导出...")
            export_result = self.api_client.start_export(selected_tasks=self.selected_tasks)
            if not export_result:
                self.export_completed.emit(False, "启动后端导出失败")
                return
            
            export_id = export_result.get('export_id')
            if not export_id:
                self.export_completed.emit(False, "获取导出ID失败")
                return
            
            # 2. 等待导出完成
            self.export_progress_updated.emit(20, "等待后端导出完成...")
            while True:
                status_result = self.api_client.get_export_status(export_id)
                if not status_result:
                    self.export_completed.emit(False, "查询导出状态失败")
                    return
                
                status = status_result.get('status')
                progress = status_result.get('progress', 0)
                message = status_result.get('message', '')
                
                self.export_progress_updated.emit(progress, f"后端导出进度: {progress}% - {message}")
                
                if status == 'completed':
                    export_path = status_result.get('export_path')
                    print(f"[DEBUG] 导出完成，路径: {export_path}")
                    if not export_path:
                        self.export_completed.emit(False, "导出路径为空")
                        return
                    break
                elif status == 'failed':
                    error_msg = status_result.get('error_message', '未知错误')
                    self.export_completed.emit(False, f"后端导出失败: {error_msg}")
                    return
                
                self.msleep(1000)  # 等待1秒
            
            # 3. 下载导出的目录
            self.download_progress_updated.emit(0, "开始下载文件...")
            success = self._download_export_data(export_path, self.download_progress_updated)
            
            if success:
                export_folder_name = os.path.basename(export_path)
                final_path = os.path.join(self.export_dir, export_folder_name)
                self.export_completed.emit(True, f"导出完成，数据已保存到: {final_path}")
            else:
                self.export_completed.emit(False, "下载导出数据失败")
                
        except Exception as e:
            self.export_completed.emit(False, f"导出过程异常: {e}")
    
    def _download_export_data(self, server_export_path, progress_callback):
        """下载服务器导出的数据 - 逐个下载文件"""
        try:
            print(f"[DEBUG] 开始下载，服务器路径: {server_export_path}")
            
            # 创建子目录
            export_folder_name = os.path.basename(server_export_path)
            target_export_dir = os.path.join(self.export_dir, export_folder_name)
            print(f"[DEBUG] 目标目录: {target_export_dir}")
            
            # 1. 获取文件列表
            files_url = f"{self.api_client.base_url}/export/download_export/"
            params = {'export_path': server_export_path}
            
            print(f"[DEBUG] 获取文件列表: {files_url}")
            response = requests.get(files_url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"[DEBUG] 获取文件列表失败: {response.status_code}")
                print(f"[DEBUG] 响应内容: {response.text}")
                return False
            
            files_data = response.json()
            files = files_data.get('files', [])
            total_files = len(files)
            
            print(f"[DEBUG] 找到 {total_files} 个文件需要下载")
            
            if total_files == 0:
                print(f"[DEBUG] 没有文件需要下载")
                return True
            
            # 2. 逐个下载文件
            downloaded_count = 0
            for file_info in files:
                file_path = file_info['path']
                file_size = file_info['size']
                
                # 更新下载进度 (0-100%)
                download_progress = int((downloaded_count / total_files) * 100)
                progress_callback.emit(download_progress, f"正在下载: {file_path}")
                
                # 创建目标目录
                target_file_path = os.path.join(target_export_dir, file_path)
                target_dir = os.path.dirname(target_file_path)
                os.makedirs(target_dir, exist_ok=True)
                
                # 下载单个文件 - 增加超时时间
                file_url = f"{self.api_client.base_url}/export/download_file/"
                file_params = {
                    'export_path': server_export_path,
                    'file_path': file_path
                }
                
                try:
                    # 根据文件大小调整超时时间
                    timeout = max(120, file_size // (1024 * 1024) * 2)  # 每MB给2秒，最少120秒
                    file_response = requests.get(file_url, params=file_params, timeout=timeout)
                    
                    if file_response.status_code == 200:
                        with open(target_file_path, 'wb') as f:
                            f.write(file_response.content)
                        downloaded_count += 1
                        print(f"[DEBUG] 文件下载成功: {file_path}")
                    else:
                        print(f"[DEBUG] 文件下载失败: {file_path}, 状态码: {file_response.status_code}")
                        
                except Exception as e:
                    print(f"[DEBUG] 下载文件异常: {file_path}, 错误: {e}")
                    continue
            
            return downloaded_count > 0
                
        except Exception as e:
            print(f"[DEBUG] 下载导出数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False


class ExportOptionsDialog(QDialog):
    """导出选项对话框"""
    
    def __init__(self, parent=None, has_selected_tasks=False):
        super().__init__(parent)
        self.has_selected_tasks = has_selected_tasks
        self.export_mode = "all"  # 默认导出所有
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("选择导出方式")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("请选择要导出的数据：")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 单选按钮组
        self.button_group = QButtonGroup()
        
        # 导出所有数据
        self.radio_all = QRadioButton("导出所有数据")
        self.radio_all.setChecked(True)
        self.button_group.addButton(self.radio_all, 0)
        layout.addWidget(self.radio_all)
        
        # 导出勾选数据（仅当有勾选任务时显示）
        if self.has_selected_tasks:
            self.radio_selected = QRadioButton("仅导出勾选的数据")
            self.button_group.addButton(self.radio_selected, 1)
            layout.addWidget(self.radio_selected)
        else:
            # 如果没有勾选任务，显示提示
            no_selected_label = QLabel("（当前没有勾选的任务）")
            no_selected_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(no_selected_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_export_mode(self):
        """获取选择的导出模式"""
        if self.button_group.checkedId() == 0:
            return "all"
        else:
            return "selected"


class ExportManager:
    """数据导出管理器"""
    
    def __init__(self, db_controller, parent_widget=None):
        """
        初始化导出管理器
        
        Args:
            db_controller: 数据库控制器实例
            parent_widget: 父窗口组件，用于显示对话框
        """
        self.db_controller = db_controller
        self.parent_widget = parent_widget
        self.export_worker = None
        self.export_progress_dialog = None
        self.download_progress_dialog = None
    
    def export_data(self, takelist=None, open_folder=None):
        """
        调用后端导出API，下载生成的CMAvatar_data目录到本地
        
        Args:
            takelist: 录制列表，用于获取勾选的任务
            open_folder: 默认打开文件夹路径
        """
        # 获取勾选的任务
        selected_tasks = self._get_selected_tasks(takelist)
        has_selected_tasks = len(selected_tasks) > 0
        
        # 显示导出选项对话框
        options_dialog = ExportOptionsDialog(self.parent_widget, has_selected_tasks)
        if options_dialog.exec() != QDialog.Accepted:
            return
        
        export_mode = options_dialog.get_export_mode()
        
        # 根据选择确定要导出的任务
        if export_mode == "selected" and has_selected_tasks:
            tasks_to_export = selected_tasks
        else:
            tasks_to_export = None  # 导出所有
        
        # 选择导出根目录
        export_dir = QFileDialog.getExistingDirectory(
            self.parent_widget, 
            "选择导出文件夹", 
            open_folder or os.getcwd()
        )
        if not export_dir:
            return
        
        # 检查是否已有导出任务在运行
        if self.export_worker and self.export_worker.isRunning():
            QMessageBox.warning(
                self.parent_widget, 
                "导出进行中", 
                "已有导出任务在运行，请等待完成后再试"
            )
            return
        
        # 创建导出进度对话框
        self.export_progress_dialog = QProgressDialog("正在导出数据...", "取消", 0, 100, self.parent_widget)
        self.export_progress_dialog.setWindowTitle("数据导出")
        self.export_progress_dialog.setMinimumDuration(0)
        self.export_progress_dialog.setValue(0)
        
        # 创建并启动导出工作线程
        self.export_worker = ExportWorker(self.db_controller.api_client, export_dir, tasks_to_export)
        self.export_worker.export_progress_updated.connect(self._on_export_progress_updated)
        self.export_worker.download_progress_updated.connect(self._on_download_progress_updated)
        self.export_worker.export_completed.connect(self._on_export_completed)
        self.export_worker.start()
    
    def _get_selected_tasks(self, takelist):
        """从录制列表中获取勾选的任务"""
        selected_tasks = []
        
        # 如果takelist是列表，说明是旧的录制列表格式
        if isinstance(takelist, list):
            # 从主窗口获取任务表格
            if hasattr(self.parent_widget, '_table_takelist'):
                table_takelist = self.parent_widget._table_takelist
                if table_takelist:
                    # 获取表格中勾选的任务
                    selected_tasks = self._get_selected_tasks_from_table(table_takelist)
            return selected_tasks
        
        # 如果takelist是QTableWidget或类似组件
        if hasattr(takelist, 'rowCount'):
            selected_tasks = self._get_selected_tasks_from_table(takelist)
        
        return selected_tasks
    
    def _get_selected_tasks_from_table(self, table):
        """从表格中获取勾选的任务"""
        selected_tasks = []
        
        for row in range(table.rowCount()):
            # 检查导出勾选框状态（第0列）
            checkbox = table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # 从主窗口的_takelist中获取对应的TakeItem对象
                if hasattr(self.parent_widget, '_takelist') and row < len(self.parent_widget._takelist):
                    take_item = self.parent_widget._takelist[row]
                    if hasattr(take_item, '_take_name') and take_item._take_name:
                        selected_tasks.append(take_item._take_name)
                        print(f"[DEBUG] 找到勾选的任务: {take_item._take_name}")
                    else:
                        print(f"[DEBUG] 警告: 第{row}行的TakeItem没有_take_name")
                else:
                    print(f"[DEBUG] 警告: 无法获取第{row}行的TakeItem对象")
        
        print(f"[DEBUG] 总共找到 {len(selected_tasks)} 个勾选的任务")
        return selected_tasks
    
    def _get_selected_tasks_from_widget(self, task_list_widget):
        """从任务列表组件中获取勾选的任务"""
        selected_tasks = []
        
        # 遍历任务树的所有项目
        def traverse_tree(item):
            if item.childCount() > 0:
                # 这是一个父节点（场景），遍历子节点
                for i in range(item.childCount()):
                    traverse_tree(item.child(i))
            else:
                # 这是一个任务节点
                task_data = item.data(0, Qt.UserRole)
                if task_data and hasattr(task_data, 'task_id'):
                    # 检查是否勾选（这里需要根据实际的勾选机制来实现）
                    # 暂时返回所有任务，因为任务列表组件可能没有勾选功能
                    pass
        
        # 遍历根节点
        root = task_list_widget.task_tree.invisibleRootItem()
        for i in range(root.childCount()):
            traverse_tree(root.child(i))
        
        return selected_tasks
    
    def _on_export_progress_updated(self, progress, message):
        """更新导出进度"""
        if self.export_progress_dialog:
            self.export_progress_dialog.setValue(progress)
            self.export_progress_dialog.setLabelText(message)
    
    def _on_download_progress_updated(self, progress, message):
        """更新下载进度"""
        # 如果导出进度对话框还在显示，先关闭它
        if self.export_progress_dialog:
            self.export_progress_dialog.close()
            self.export_progress_dialog = None
        
        # 创建下载进度对话框
        if not self.download_progress_dialog:
            self.download_progress_dialog = QProgressDialog("正在下载文件...", "取消", 0, 100, self.parent_widget)
            self.download_progress_dialog.setWindowTitle("文件下载")
            self.download_progress_dialog.setMinimumDuration(0)
            self.download_progress_dialog.setValue(0)
            self.download_progress_dialog.show()
        
        self.download_progress_dialog.setValue(progress)
        self.download_progress_dialog.setLabelText(message)
        QCoreApplication.processEvents()
    
    def _on_export_completed(self, success, message):
        """导出完成回调"""
        # 关闭所有进度对话框
        if self.export_progress_dialog:
            self.export_progress_dialog.close()
            self.export_progress_dialog = None
        
        if self.download_progress_dialog:
            self.download_progress_dialog.close()
            self.download_progress_dialog = None
        
        if success:
            QMessageBox.information(
                self.parent_widget, 
                "导出完成", 
                message
            )
        else:
            QMessageBox.warning(
                self.parent_widget, 
                "导出失败", 
                message
            )
        
        # 清理工作线程
        if self.export_worker:
            self.export_worker.deleteLater()
            self.export_worker = None
    
