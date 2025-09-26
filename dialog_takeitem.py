from PySide6 import QtWidgets
from PySide6.QtWidgets import (QGridLayout, QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QMessageBox)
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
import app_const
import app_css
import app_common
from factory_widget import QtWidgetFactory

class TakeItemDialog(QtWidgets.QDialog):
    def __init__(self, takeItem, dict_takename, parent):
        super(TakeItemDialog, self).__init__(parent)

        # from peel.DEVICES - list of peel_device.PeelDevice objects
        self._takeItem = takeItem
        self._dict_takename = dict_takename
        self.setWindowTitle("CMCapture")
        self._modify = False

        vBoxLayout = QVBoxLayout()

        # 创建 QGridLayout
        gridLayout = QGridLayout()
        lblShotName = QLabel(self.tr("Shot Name:"))
        gridLayout.addWidget(lblShotName, 0, 0)
        self._edt_shotName = QtWidgetFactory.create_QLineEdit(self._takeItem._shot_name)
        self._edt_shotName.setMaxLength(app_const.Max_Shot_Name)
        # 设置半角字符验证器
        reg_half = QRegularExpression(app_const.Regular_Char_Half)
        validator_half = QRegularExpressionValidator(self)
        validator_half.setRegularExpression(reg_half)
        self._edt_shotName.setValidator(validator_half)
        gridLayout.addWidget(self._edt_shotName, 0, 1)

        lblTakeName = QLabel(self.tr("Take#:"))
        gridLayout.addWidget(lblTakeName, 1, 0)
        self._edt_takeNo = QtWidgetFactory.create_QLineEdit(str(self._takeItem._take_no))
        self._edt_takeNo.setMaxLength(app_const.Max_Take_No)
        # 设置整数验证器
        reg_number = QRegularExpression(app_const.Regular_Number)
        validator = QRegularExpressionValidator(self)
        validator.setRegularExpression(reg_number)
        self._edt_takeNo.setValidator(validator)
        gridLayout.addWidget(self._edt_takeNo, 1, 1)

        lblDesc = QLabel(self.tr("Description:"))
        gridLayout.addWidget(lblDesc, 2, 0)
        self._edt_desc = QtWidgetFactory.create_QPlainTextEdit(self._takeItem._take_desc)
        gridLayout.addWidget(self._edt_desc, 2, 1)

        lblNotes = QLabel(self.tr("Notes:"))
        gridLayout.addWidget(lblNotes, 3, 0)
        self._edt_notes = QtWidgetFactory.create_QPlainTextEdit(self._takeItem._take_notes)
        gridLayout.addWidget(self._edt_notes, 3, 1)
        
        gridLayout.addWidget(QLabel(self.tr("Record Time:")), 4, 0)
        hBoxRecordTime = QHBoxLayout()

        #start record time
        start_time = self._takeItem._start_time.strftime(app_const.TimeFormat)
        self._edt_start_time = QtWidgetFactory.create_QLineEdit(start_time, 
                                                                app_css.SheetStyle_Edit_ReadOnly, 
                                                                True)

        hBoxRecordTime.addWidget(self._edt_start_time)
        hBoxRecordTime.addWidget(QLabel(" - "))
        #stop record time
        end_time = self._takeItem._end_time.strftime(app_const.TimeFormat)
        self._edt_end_time = QtWidgetFactory.create_QLineEdit(end_time, 
                                                                app_css.SheetStyle_Edit_ReadOnly, 
                                                                True)
        hBoxRecordTime.addWidget(self._edt_end_time)
        gridLayout.addLayout(hBoxRecordTime, 4, 1)

        gridLayout.addWidget(QLabel(self.tr("Grade:")), 5, 0)
        self._cmb_eval = QtWidgetFactory.create_QComboBox(app_const.ComboBox_Eval_Default, takeItem._eval, app_css.SheetStyle_Combo_All)
        gridLayout.addWidget(self._cmb_eval, 5, 1)
        # self.cmbEval.setCurrentText(takeItem._eval)
        gridLayout.setRowStretch(2, 1)
        gridLayout.setRowStretch(3, 3)
        vBoxLayout.addLayout(gridLayout)

        hBoxButtons = QHBoxLayout()

        self._shot_spacer = QSpacerItem(35, 35, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hBoxButtons.addItem(self._shot_spacer)

        self._btn_OK = QtWidgetFactory.create_QPushButton(self.tr("OK"), app_css.SheetStyle_PushButton, self.ok_clicked)
        self._btn_OK.setFixedSize(55, 25)
        hBoxButtons.addWidget(self._btn_OK)

        self._btn_cancel = QtWidgetFactory.create_QPushButton(self.tr("Cancel"), app_css.SheetStyle_PushButton, self.cancel_clicked)
        self._btn_cancel.setFixedSize(55, 25)
        hBoxButtons.addWidget(self._btn_cancel)
        vBoxLayout.addLayout(hBoxButtons)
        
        self.setLayout(vBoxLayout)

    def ok_clicked(self):
        new_takename = app_common.get_shot_name(self._edt_shotName, self._edt_takeNo)
        if new_takename in self._dict_takename and self._takeItem._take_name != new_takename:
            msg = self.tr(" has existed. Please modify shot name or take no.")
            QMessageBox.warning(self, app_const.AppName, new_takename + msg)
            return
        
        # Take Name为索引
        if self._takeItem._take_name != new_takename:
            self._dict_takename.pop(self._takeItem._take_name)
            self._dict_takename[new_takename] = ''
            self._takeItem._take_name = new_takename
            self._modify = True
            
        # shot name
        if self._takeItem._shot_name != self._edt_shotName.text():
            self._takeItem._shot_name = self._edt_shotName.text()
            self._modify = True

        # take#
        takeNo = int(self._edt_takeNo.text())
        if self._takeItem._take_no != takeNo:
            self._takeItem._take_no = takeNo
            self._modify = True

        # 描述
        if self._takeItem._take_desc != self._edt_desc.toPlainText():
            self._takeItem._take_desc = self._edt_desc.toPlainText()
            self._modify = True

        # 笔记
        if self._takeItem._take_notes != self._edt_notes.toPlainText():
            self._takeItem._take_notes = self._edt_notes.toPlainText()
            self._modify = True

        # 评分
        if self._takeItem._eval != self._cmb_eval.currentText():
            self._takeItem._eval = self._cmb_eval.currentText()
            self._modify = True

        self.accept()

    def cancel_clicked(self):
        self.reject()
    