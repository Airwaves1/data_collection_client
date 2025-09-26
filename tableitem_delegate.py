
from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

class CustomDelegateAlphaNumeric(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # 匹配英文和数字
        regex = QRegularExpression("[0-9]+")
        validator = QRegularExpressionValidator(regex)
        editor.setValidator(validator)
        return editor

class CustomDelegateAlphaNumericSymbol(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # 匹配英文、数字和符号
        regex = QRegularExpression("[A-Za-z0-9!@#$%^&*()-_+=]+")
        validator = QRegularExpressionValidator(regex)
        editor.setValidator(validator)
        return editor
