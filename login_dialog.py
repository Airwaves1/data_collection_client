"""
用户登录对话框
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QTabWidget, QWidget, QFormLayout, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
import app_css
from factory_widget import QtWidgetFactory
from service.db_controller import DBController
from PySide6.QtCore import QSettings


class LoginDialog(QDialog):
    """用户登录对话框"""
    
    # 登录成功信号
    login_success = Signal(dict)  # 传递用户信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据采集系统 - 用户登录")
        # 允许调整大小，设置合理的最小尺寸，避免控件拥挤
        self.setMinimumSize(520, 400)
        self.setModal(True)
        
        # 设置窗口图标
        self.setWindowIcon(QIcon(':/images/app_icon'))
        
        # 初始化数据库控制器
        self.db_controller = DBController()
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 标题
        title_label = QLabel("数据采集系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e88; margin: 10px;")
        layout.addWidget(title_label)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        
        # 登录选项卡
        self.login_tab = self.create_login_tab()
        self.tab_widget.addTab(self.login_tab, "登录")
        
        # 注册选项卡
        self.register_tab = self.create_register_tab()
        self.tab_widget.addTab(self.register_tab, "注册")

        # 服务器设置选项卡
        self.server_tab = self.create_server_tab()
        self.tab_widget.addTab(self.server_tab, "服务器设置")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)
        
        self.login_button = QtWidgetFactory.create_QPushButton("登录", app_css.SheetStyle_PushButton, self.login)
        self.register_button = QtWidgetFactory.create_QPushButton("注册", app_css.SheetStyle_PushButton, self.register)
        self.cancel_button = QtWidgetFactory.create_QPushButton("取消", app_css.SheetStyle_PushButton, self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addStretch(1)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接选项卡切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
    def create_login_tab(self):
        """创建登录选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        layout.setFormAlignment(Qt.AlignTop)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)
        
        # 用户名
        self.login_username = QtWidgetFactory.create_QLineEdit("")
        self.login_username.setMinimumWidth(280)
        self.login_username.setPlaceholderText("请输入用户名")
        layout.addRow("用户名:", self.login_username)
        
        # 密码
        self.login_password = QtWidgetFactory.create_QLineEdit("")
        self.login_password.setMinimumWidth(280)
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText("请输入密码")
        layout.addRow("密码:", self.login_password)
        
        # 记住密码复选框
        self.remember_password = QCheckBox("记住密码")
        layout.addRow("", self.remember_password)
        
        tab.setLayout(layout)
        return tab
        
    def create_register_tab(self):
        """创建注册选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        layout.setFormAlignment(Qt.AlignTop)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)
        
        # 用户名
        self.register_username = QtWidgetFactory.create_QLineEdit("")
        self.register_username.setMinimumWidth(280)
        self.register_username.setPlaceholderText("请输入用户名")
        layout.addRow("用户名:", self.register_username)
        
        # 密码
        self.register_password = QtWidgetFactory.create_QLineEdit("")
        self.register_password.setMinimumWidth(280)
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_password.setPlaceholderText("请输入密码")
        layout.addRow("密码:", self.register_password)
        
        # 确认密码
        self.register_confirm_password = QtWidgetFactory.create_QLineEdit("")
        self.register_confirm_password.setMinimumWidth(280)
        self.register_confirm_password.setEchoMode(QLineEdit.Password)
        self.register_confirm_password.setPlaceholderText("请再次输入密码")
        layout.addRow("确认密码:", self.register_confirm_password)
        
        # 采集者信息
        self.collector_id = QtWidgetFactory.create_QLineEdit("")
        self.collector_id.setMinimumWidth(280)
        self.collector_id.setPlaceholderText("请输入采集者ID")
        layout.addRow("采集者ID:", self.collector_id)
        
        self.collector_name = QtWidgetFactory.create_QLineEdit("")
        self.collector_name.setMinimumWidth(280)
        self.collector_name.setPlaceholderText("请输入采集者姓名")
        layout.addRow("采集者姓名:", self.collector_name)
        
        self.collector_organization = QtWidgetFactory.create_QLineEdit("")
        self.collector_organization.setMinimumWidth(280)
        self.collector_organization.setPlaceholderText("请输入组织名称")
        layout.addRow("组织名称:", self.collector_organization)
        
        tab.setLayout(layout)
        return tab

    def create_server_tab(self):
        """创建服务器设置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        layout.setFormAlignment(Qt.AlignTop)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        settings = QSettings("CHINGMU", "CMCapture")
        server_host = str(settings.value("ServerHost", "localhost"))
        server_port = str(settings.value("ServerPort", "8000"))
        api_prefix = str(settings.value("ServerApiPrefix", "/api"))

        self.server_host = QtWidgetFactory.create_QLineEdit(server_host)
        self.server_port = QtWidgetFactory.create_QLineEdit(server_port)
        self.server_api_prefix = QtWidgetFactory.create_QLineEdit(api_prefix)

        self.server_host.setPlaceholderText("例如: 192.168.1.100 或 localhost")
        self.server_port.setPlaceholderText("例如: 8000")
        self.server_api_prefix.setPlaceholderText("例如: /api")

        layout.addRow("服务器地址:", self.server_host)
        layout.addRow("服务器端口:", self.server_port)
        layout.addRow("API前缀:", self.server_api_prefix)

        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_save = QtWidgetFactory.create_QPushButton("保存设置", app_css.SheetStyle_PushButton, self.save_server_settings)
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_save)
        layout.addRow("", btn_layout)

        tab.setLayout(layout)
        return tab
        
    def on_tab_changed(self, index):
        """选项卡切换时的处理"""
        # 登录页显示“登录”按钮；注册页显示“注册”按钮；服务器设置页隐藏两者
        if index == 0:
            self.login_button.setVisible(True)
            self.register_button.setVisible(False)
        elif index == 1:
            self.login_button.setVisible(False)
            self.register_button.setVisible(True)
        else:
            self.login_button.setVisible(False)
            self.register_button.setVisible(False)
            
    def login(self):
        """处理登录"""
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入用户名和密码")
            return
            
        # 调用API进行登录验证
        try:
            result = self.db_controller.login_collector(username, password)
            if result and 'message' in result:
                self.login_success.emit(result)
                self.accept()
            else:
                error_msg = result.get('error', '登录失败') if result else '网络连接失败'
                QMessageBox.warning(self, "登录失败", error_msg)
        except Exception as e:
            QMessageBox.warning(self, "登录失败", f"登录过程中发生错误: {str(e)}")
            
    def register(self):
        """处理注册"""
        username = self.register_username.text().strip()
        password = self.register_password.text().strip()
        confirm_password = self.register_confirm_password.text().strip()
        collector_id = self.collector_id.text().strip()
        collector_name = self.collector_name.text().strip()
        collector_organization = self.collector_organization.text().strip()
        
        # 验证输入
        if not all([username, password, collector_id, collector_name, collector_organization]):
            QMessageBox.warning(self, "注册失败", "请填写所有必填字段")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "注册失败", "两次输入的密码不一致")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "注册失败", "密码长度至少6位")
            return
            
        # 调用API进行注册
        try:
            collector_data = {
                'username': username,
                'password': password,
                'collector_id': collector_id,
                'collector_name': collector_name,
                'collector_organization': collector_organization
            }
            
            result = self.db_controller.register_collector(collector_data)
            if result and 'message' in result:
                QMessageBox.information(self, "注册成功", f"用户 {username} 注册成功！")
                
                # 切换到登录选项卡
                self.tab_widget.setCurrentIndex(0)
                
                # 清空注册表单
                self.register_username.clear()
                self.register_password.clear()
                self.register_confirm_password.clear()
                self.collector_id.clear()
                self.collector_name.clear()
                self.collector_organization.clear()
            else:
                error_msg = result.get('error', '注册失败') if result else '网络连接失败'
                QMessageBox.warning(self, "注册失败", error_msg)
        except Exception as e:
            QMessageBox.warning(self, "注册失败", f"注册过程中发生错误: {str(e)}")

    def save_server_settings(self):
        """保存服务器地址与端口配置"""
        host = self.server_host.text().strip() if hasattr(self, 'server_host') else "localhost"
        port = self.server_port.text().strip() if hasattr(self, 'server_port') else "8000"
        prefix = self.server_api_prefix.text().strip() if hasattr(self, 'server_api_prefix') else "/api"

        if not host:
            QMessageBox.warning(self, "参数错误", "服务器地址不能为空")
            return
        if not port.isdigit():
            QMessageBox.warning(self, "参数错误", "服务器端口必须是数字")
            return
        if not prefix:
            prefix = "/api"
        if not prefix.startswith("/"):
            prefix = "/" + prefix

        settings = QSettings("CHINGMU", "CMCapture")
        settings.setValue("ServerHost", host)
        settings.setValue("ServerPort", port)
        settings.setValue("ServerApiPrefix", prefix)

        QMessageBox.information(self, "保存成功", f"已保存服务器设置:\n{host}:{port}{prefix}")
