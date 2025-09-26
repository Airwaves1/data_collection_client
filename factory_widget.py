
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
