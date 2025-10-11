
from PySide6.QtWidgets import (QComboBox, QLineEdit, QPushButton, QPlainTextEdit, QProgressBar, QTextEdit)
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6 import QtNetwork
import app_css, app_const

class QtWidgetFactory():

    @staticmethod
    def create_QPushButton(text, css, event_click):
        button = QPushButton(text)
        button.setStyleSheet(css)
        button.pressed.connect(event_click)
        return button
    
    @staticmethod
    def create_QLineEdit(text, css=app_css.SheetStyle_Edit_All, read_only=False):
        edtLine = QLineEdit()
        edtLine.setStyleSheet(css)
        edtLine.setText(text)
        edtLine.setReadOnly(read_only)
        return edtLine
    
    @staticmethod
    def create_QLineEdit_IP(text):
        edtLine = QtWidgetFactory.create_QLineEdit(text)
        edtLine.setInputMask("000.000.000.000")
        return edtLine
    
    @staticmethod
    def create_QLineEdit_port(text):
        edtLine = QtWidgetFactory.create_QLineEdit(text)
        edtLine.setMaxLength(5)
        # 设置整数验证器
        reg_number = QRegularExpression(app_const.Regular_Number)
        validator = QRegularExpressionValidator()
        validator.setRegularExpression(reg_number)
        edtLine.setValidator(validator)
        return edtLine

    @staticmethod
    def create_QPlainTextEdit(text, css=app_css.SheetStyle_Edit_All):
        edtPlain = QPlainTextEdit()
        edtPlain.setStyleSheet(css)
        edtPlain.setPlainText(text)
        return edtPlain
    
    @staticmethod
    def create_QProgressBar(css, max=100):
        progress_bar = QProgressBar()
        progress_bar.setStyleSheet(css)
        progress_bar.setRange(0, max)
        return progress_bar
    
    @staticmethod
    def create_QComboBox(candidate, selected_text, css=app_css.SheetStyle_Combo_All):
        comboBox = QComboBox()
        comboBox.addItems(candidate)
        comboBox.setStyleSheet(css)
        comboBox.setCurrentText(selected_text)
        return comboBox
    
    @staticmethod
    def create_QComboBox_IP(current_ip):
        return InterfaceCombo(False, current_ip)
    
    @staticmethod
    def create_QComboBox_IP_Editable(current_ip):
        """创建可编辑的IP地址组合框，支持手动输入和选择网络接口"""
        return EditableInterfaceCombo(False, current_ip)
    

class InterfaceCombo(QComboBox):
    def __init__(self, show_all, current_text="", parent=None):

        super(InterfaceCombo, self).__init__(parent)
        self.setStyleSheet(app_css.SheetStyle_Combo_All)
        if show_all:
            self.addItem(self.tr("--all--"))

        # Interface to listen on
        for i in QtNetwork.QNetworkInterface.allInterfaces():
            if not (i.flags() & QtNetwork.QNetworkInterface.IsUp):
                continue
            for j in i.addressEntries():
                if j.ip().protocol() != QtNetwork.QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    continue
                self.addItem(j.ip().toString())

        self.setCurrentText(current_text)

    def ip(self):
        if self.currentText() == self.tr("--all--"):
            return ""
        else:
            return self.currentText()


class EditableInterfaceCombo(QComboBox):
    """可编辑的IP地址组合框，支持手动输入和选择网络接口"""
    
    def __init__(self, show_all, current_text="", parent=None):
        super(EditableInterfaceCombo, self).__init__(parent)
        self.setStyleSheet(app_css.SheetStyle_Combo_All)
        self.setEditable(True)  # 允许编辑
        
        # 添加常用IP地址选项
        common_ips = [
            "127.0.0.1",      # 本地回环
            "192.168.1.1",    # 常见路由器IP
            "192.168.0.1",    # 常见路由器IP
            "10.0.0.1",       # 内网IP
            "172.16.0.1",     # 内网IP
        ]
        
        if show_all:
            self.addItem(self.tr("--all--"))
        
        # 添加常用IP地址
        for ip in common_ips:
            if ip not in [self.itemText(i) for i in range(self.count())]:
                self.addItem(ip)
        
        # 添加网络接口IP地址
        for i in QtNetwork.QNetworkInterface.allInterfaces():
            if not (i.flags() & QtNetwork.QNetworkInterface.IsUp):
                continue
            for j in i.addressEntries():
                if j.ip().protocol() != QtNetwork.QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    continue
                ip_str = j.ip().toString()
                if ip_str not in [self.itemText(k) for k in range(self.count())]:
                    self.addItem(ip_str)
        
        # 设置当前文本
        if current_text:
            self.setCurrentText(current_text)
        else:
            # 默认选择第一个可用的IP地址
            for i in range(self.count()):
                if self.itemText(i) != self.tr("--all--"):
                    self.setCurrentIndex(i)
                    break
    
    def ip(self):
        """获取当前选择的IP地址"""
        current_text = self.currentText().strip()
        if current_text == self.tr("--all--"):
            return ""
        else:
            return current_text
    
    def validate_ip(self, ip_text):
        """验证IP地址格式"""
        import re
        ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(ip_pattern, ip_text)
        if not match:
            return False
        
        # 检查每个数字是否在0-255范围内
        for group in match.groups():
            if int(group) > 255:
                return False
        return True
