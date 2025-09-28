"""
任务列表组件
"""
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from task_data_model import TaskData, TaskDataManager
from typing import List, Optional


class TaskListWidget(QWidget):
    """任务列表组件"""
    
    task_selected = Signal(TaskData)  # 任务选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = TaskDataManager()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # 场景过滤下拉框
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 4, 8, 4)
        
        filter_label = QLabel("场景:")
        filter_label.setFont(QFont("Microsoft YaHei", 10))
        filter_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        
        self.scenario_combo = QComboBox()
        self.scenario_combo.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #EAEAEA;
                padding: 4px 8px;
                border-radius: 2px;
                font-family: 'Microsoft YaHei';
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 1px solid #DADADA;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #404040;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #FFFFFF;
                margin-right: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #EAEAEA;
                selection-background-color: #707070;
            }
        """)
        self.scenario_combo.currentTextChanged.connect(self.filter_by_scenario)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.scenario_combo, 1)
        layout.addLayout(filter_layout)

        # 任务树
        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderLabel("动作捕捉任务")
        self.task_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #404040;
                color: #FFFFFF;
                border: 2px groove gray;
                font-family: 'Microsoft YaHei';
                font-size: 10pt;
                outline: none;
                gridline-color: #808080;
            }
            QTreeWidget::item {
                height: 24px;
                padding: 2px 4px;
                border-bottom: 1px solid #808080;
            }
            QTreeWidget::item:selected {
                background-color: #707070;
                color: #FFFFFF;
            }
            QTreeWidget::item:hover {
                background-color: #505050;
            }
            QTreeWidget::branch {
                background: #404040;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: none;
                border: none;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {
                border-image: none;
                image: none;
            }
            QHeaderView::section {
                background-color: #404143;
                color: white;
                border: 1px solid #808080;
                padding: 4px;
                font-weight: bold;
            }
        """)
        self.task_tree.itemClicked.connect(self.on_task_clicked)
        
        layout.addWidget(self.task_tree)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #808080;
                border-bottom: 1px solid #EAEAEA;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)

        # 导入按钮
        import_btn = QPushButton("导入Excel")
        import_btn.setStyleSheet("""
            QPushButton {
                font-family: 'Microsoft YaHei';
                font-size: 10pt;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010);
                border: 1px solid #EAEAEA;
                color: #FFFFFF;
                padding: 6px 12px;
                border-radius: 2px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2a2d2e, stop: 1 #202020);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #101010, stop: 1 #16191a);
            }
        """)
        import_btn.clicked.connect(self.import_excel)

        layout.addWidget(import_btn)
        layout.addStretch()

        return toolbar

    def import_excel(self):
        """导入Excel文件"""
        file_dialog = QFileDialog(self, "Import Motion Capture Tasks")
        file_dialog.setNameFilter("Excel Files (*.xlsx *.xls)")
        
        if file_dialog.exec() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            print(f"[DEBUG] 选择的文件路径: {file_path}")
            
            if self.data_manager.load_from_excel(file_path):
                print(f"[DEBUG] Excel导入成功，任务数量: {len(self.data_manager.tasks)}")
                self.refresh_ui()
                QMessageBox.information(self, "Success", 
                                      f"Successfully imported {len(self.data_manager.tasks)} tasks")
            else:
                print(f"[DEBUG] Excel导入失败")
                QMessageBox.warning(self, "Error", "Failed to import Excel file")

    def refresh_ui(self):
        """刷新界面"""
        print(f"[DEBUG] 刷新UI，当前任务数量: {len(self.data_manager.tasks)}")
        self.update_scenario_filter()
        self.update_task_tree()

    def update_scenario_filter(self):
        """更新场景过滤器"""
        self.scenario_combo.clear()
        self.scenario_combo.addItem("All")
        
        scenarios = self.data_manager.get_scenarios()
        for scenario in scenarios:
            self.scenario_combo.addItem(scenario)

    def update_task_tree(self, scenario_filter: str = "All"):
        """更新任务树"""
        self.task_tree.clear()
        
        if scenario_filter == "All":
            # 按场景分组显示
            scenarios = self.data_manager.get_scenarios()
            for scenario in scenarios:
                tasks = self.data_manager.get_tasks_by_scenario(scenario)
                if tasks:
                    scenario_item = QTreeWidgetItem([f"{scenario} ({len(tasks)})"])
                    scenario_item.setFont(0, QFont("Microsoft YaHei", 10, QFont.Bold))
                    
                    for task in tasks:
                        task_item = QTreeWidgetItem([task.get_display_name()])
                        task_item.setData(0, Qt.UserRole, task)
                        scenario_item.addChild(task_item)
                    
                    self.task_tree.addTopLevelItem(scenario_item)
                    scenario_item.setExpanded(True)
        else:
            # 单一场景显示
            tasks = self.data_manager.get_tasks_by_scenario(scenario_filter)
            for task in tasks:
                task_item = QTreeWidgetItem([task.get_display_name()])
                task_item.setData(0, Qt.UserRole, task)
                self.task_tree.addTopLevelItem(task_item)

    def filter_by_scenario(self, scenario: str):
        """按场景过滤"""
        self.update_task_tree(scenario)

    def on_task_clicked(self, item, column):
        """任务点击事件"""
        task_data = item.data(0, Qt.UserRole)
        if task_data and isinstance(task_data, TaskData):
            self.data_manager.set_current_task(task_data)
            self.task_selected.emit(task_data)

    def get_current_task(self) -> Optional[TaskData]:
        """获取当前选中的任务"""
        return self.data_manager.current_task