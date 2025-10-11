"""
任务属性面板组件
"""
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from task_data_model import TaskData
from typing import List
import app_css


class PropertyItemWidget(QFrame):
    """单个属性项组件"""
    
    def __init__(self, key: str, value: str, parent=None):
        super().__init__(parent)
        self.setup_ui(key, value)

    def setup_ui(self, key: str, value: str):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            PropertyItemWidget {
                background-color: transparent;
                border-bottom: 1px solid #333333;
                padding: 4px;
            }
            PropertyItemWidget:hover {
                background-color: #2A2A2A;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # 属性名称
        key_label = QLabel(key + ":")
        key_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        key_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        key_label.setFixedWidth(150)
        key_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 属性值
        if len(str(value)) > 100:  # 长文本使用多行显示
            value_widget = QTextEdit()
            value_widget.setPlainText(str(value))
            value_widget.setMaximumHeight(80)
            value_widget.setReadOnly(True)
            value_widget.setStyleSheet("""
                QTextEdit {
                    background-color: #2A2A2A;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 2px;
                    font-family: 'Microsoft YaHei';
                    font-size: 10pt;
                    padding: 4px;
                }
            """)
        else:
            value_widget = QLabel(str(value) if value else "N/A")
            value_widget.setWordWrap(True)
            value_widget.setStyleSheet("""
                QLabel {
                    background-color: #2A2A2A;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 2px;
                    font-family: 'Microsoft YaHei';
                    font-size: 10pt;
                    padding: 4px;
                }
            """)

        layout.addWidget(key_label)
        layout.addWidget(value_widget, 1)


class TaskPropertyPanel(QWidget):
    """任务属性面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        self.title_label = QLabel("任务属性")
        self.title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: #303030;
                color: #4488dd;
                padding: 8px 12px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.title_label)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: #1F1F1F;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: #1F1F1F;
            }}
            {app_css.SheetStyle_ScrollBar}
        """)

        self.property_widget = QWidget()
        self.property_layout = QVBoxLayout(self.property_widget)
        self.property_layout.setContentsMargins(0, 0, 0, 0)
        self.property_layout.setSpacing(0)
        self.property_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.property_widget)
        layout.addWidget(scroll_area)

        # 初始状态 - 不显示任何内容
        self.current_task = None

    def show_empty_state(self):
        """显示空状态"""
        self.clear_properties()
        
        empty_label = QLabel("未选择任务")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-family: 'Microsoft YaHei';
                font-size: 14px;
                padding: 40px;
            }
        """)
        self.property_layout.addWidget(empty_label)

    def clear_properties(self):
        """清空属性显示"""
        for i in reversed(range(self.property_layout.count())):
            item = self.property_layout.itemAt(i)
            if item:
                if item.widget():
                    item.widget().setParent(None)
                elif item.spacerItem():
                    self.property_layout.removeItem(item)

    def display_task(self, task: TaskData):
        """显示任务属性"""
        if not task:
            self.clear_properties()
            self.title_label.setText("任务属性")
            return

        self.current_task = task
        
        # 更新标题标签
        self.title_label.setText(f"任务属性: {task.get_display_name()}")
        
        self.clear_properties()

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: #333333;
                background-color: #333333;
                border: none;
                height: 1px;
                margin: 8px 0px;
            }
        """)
        self.property_layout.addWidget(separator)

        # 添加所有属性
        properties = task.get_all_properties()
        for key, value in properties:
            if value:  # 只显示有值的属性
                property_item = PropertyItemWidget(key, value)
                self.property_layout.addWidget(property_item)

        # 添加底部间距
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.property_layout.addItem(spacer)