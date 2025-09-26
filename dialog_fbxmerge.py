from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, QWidget, 
                               QGroupBox, QHBoxLayout, QVBoxLayout, QSplitter, QLabel, QMessageBox)
import os
import app_css
import app_const
from worker_fbxmerge import MergeFbxFilesThread
from factory_widget import QtWidgetFactory

reg_fbx_merge_dir = "FbxMergeDirectory"

class FbxMergeDialog(QtWidgets.QDialog):
    #  ["Device", "No", "TakeName", "CMTracker", "Vrtrix", "Merge Result"]
    COL_DEVICE = 0
    COL_NO = 1
    COL_TAKENAME = 2
    COL_CMTRACKER = 3
    COL_VRTRIX = 4
    COL_MERGE_RESULT = 5

    def __init__(self, settings, merge_list, merge_row_count, parent):
        super(FbxMergeDialog, self).__init__(parent)

        # from peel.DEVICES - list of peel_device.PeelDevice objects
        self.devices = []
        self.merge_list = merge_list
        self.merge_file_count = 0
        self.table_row_count = merge_row_count
        self.current_process = None
        self.total_copied = None
        self.total_failed = None
        self.total_skipped = None
        self.running = None
        self.work_threads = []

        self.setWindowTitle(self.tr("Merge Fbx File"))

        if settings is None:
            self.settings = QtCore.QSettings(app_const.CompanyName, app_const.AppName)
        else:
            self.settings = settings

        layout = QVBoxLayout()

        data_dir = self.settings.value(reg_fbx_merge_dir)
        if data_dir is None or len(data_dir) == 0:
            data_dir = os.getcwd() + "\\data"
            self.settings.setValue(reg_fbx_merge_dir, data_dir)

        # File Path Browser
        file_layout = QHBoxLayout()
        self.path = QtWidgetFactory.create_QLineEdit(str(data_dir))
        self.path_button = QtWidgetFactory.create_QPushButton(". . .", app_css.SheetStyle_PushButton, self.browse)
        self.path_button.setFixedSize(55, 22)
        file_layout.addWidget(self.path)
        file_layout.addWidget(self.path_button)
        file_layout.setSpacing(6)
        layout.addItem(file_layout)

        self.splitter = QSplitter(QtCore.Qt.Vertical)
        self.splitter.setSizes([2, 1, 1, 1])
        #body and hands nodes input
        widget_node = self.create_node_layout()
        self.splitter.addWidget(widget_node)

        #take list table
        self._takelist_table = self.create_merge_table()
        self.selected_devices = None
        self.splitter.addWidget(self._takelist_table)
        
        # Log
        self.log = QtWidgetFactory.create_QPlainTextEdit('', app_css.SheetStyle_Edit_Log)
        self.splitter.addWidget(self.log)
        layout.addWidget(self.splitter)

        # InfoLabel
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #ccc")
        layout.addWidget(self.info_label)

        # Progress bar
        self.progress_bar = QtWidgetFactory.create_QProgressBar(app_css.SheetStyle_ProgressBar)
        layout.addWidget(self.progress_bar)

        # Buttons
        self.go_button = QtWidgetFactory.create_QPushButton(self.tr("Merge Files"), app_css.SheetStyle_PushButton, self.go)
        self.close_button = QtWidgetFactory.create_QPushButton(self.tr("Close"), app_css.SheetStyle_PushButton, self.teardown)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.go_button)
        button_layout.addWidget(self.close_button)

        layout.addItem(button_layout)
        self.setLayout(layout)
        self.resize(500, 800)

        geo = self.settings.value("mergeGeometry")
        if geo:
            self.restoreGeometry(geo)

        sizes = self.settings.value("mergeSplitterGeometry")
        if sizes:
            self.splitter.setSizes([int(i) for i in sizes])

    def create_node_layout(self):
        # 创建主布局
        bodynode_layout = QHBoxLayout()

        # Body Group
        result_body = self.create_node_group(self.tr("Body Node Name"))
        self.body_left_node = result_body[1]
        self.body_right_node = result_body[2]
        bodynode_layout.addWidget(result_body[0])

        # Hand Group
        result_hand = self.create_node_group(self.tr("Hand Node Name"))
        self.hand_left_node = result_hand[1]
        self.hand_right_node = result_hand[2]
        bodynode_layout.addWidget(result_hand[0])

        node_widget = QWidget()
        node_widget.setLayout(bodynode_layout)
        return node_widget
    
    def create_node_group(self, title):
        group_node = QGroupBox(title)
        group_layout_node = QVBoxLayout()
        group_node.setLayout(group_layout_node)

        layout_left_node = QHBoxLayout()
        label_left_node = QLabel(self.tr(" Left Node:"))
        edit_left_node = QtWidgetFactory.create_QLineEdit("LeftHand")
        layout_left_node.addWidget(label_left_node)
        layout_left_node.addWidget(edit_left_node)
        group_layout_node.addLayout(layout_left_node)

        layout_right_node = QHBoxLayout()
        label_right_node = QLabel(self.tr("Right Node:"))
        edit_right_node = QtWidgetFactory.create_QLineEdit("RightHand")
        layout_right_node.addWidget(label_right_node)
        layout_right_node.addWidget(edit_right_node)
        group_layout_node.addLayout(layout_right_node)

        return group_node, edit_left_node, edit_right_node

    # 创建 QTableWidget
    def create_merge_table(self):
        
        takelistWidget = QTableWidget()
        # 设置列名
        header_labels = [self.tr("Device"), 
                         self.tr("No"), 
                         self.tr("TakeName"), 
                         self.tr("CMTracker"), 
                         self.tr("Vrtrix"), 
                         self.tr("Merge Result")]
        takelistWidget.setColumnCount(len(header_labels))
        takelistWidget.setHorizontalHeaderLabels(header_labels)

        # 设置表头字体颜色为黑色
        takelistWidget.horizontalHeader().setStyleSheet("QHeaderView::section {background-color: #404143;color: white;}")

        # 设置表头字体颜色为黑色
        takelistWidget.verticalHeader().setStyleSheet("QHeaderView::section {background-color: #404143;color: white;}")
        takelistWidget.itemDoubleClicked.connect(self.handleItemDoubleClicked)

        # 设置表格样式
        takelistWidget.setStyleSheet(app_css.SheetStyle_TableWidget)

        row = 0
        job_no = 1
        # 先设置TableWidget的行数，再设置数据，不然会显示空白
        takelistWidget.setRowCount(self.table_row_count)

        for key, value in self.merge_list.items():
            self.set_table_item(takelistWidget, row, self.COL_DEVICE, key)
            row += 1
            for take_item in value:
                self.set_table_item(takelistWidget, row, self.COL_NO, str(job_no))
                self.set_table_item(takelistWidget, row, self.COL_TAKENAME, take_item['shot_name'])
                body_filename = os.path.basename(take_item['body_fullpath'])
                self.set_table_item(takelistWidget, row, self.COL_CMTRACKER, body_filename)
                hand_files = take_item['hand_files']
                hand_text = ""
                for hand in hand_files:
                    hand_filename = os.path.basename(hand)
                    hand_text += hand_filename + '\r\n'

                if len(hand_text) > 0:
                    hand_text = hand_text[:-1]

                self.set_table_item(takelistWidget, row, self.COL_VRTRIX, hand_text)
                row += 1
                job_no += 1
        self.merge_file_count = job_no - 1

        # 让列宽根据内容自动调整
        takelistWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        takelistWidget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # # 将所有单元格设为不可编辑
        # for i in range(takelistWidget.rowCount()):
        #     for j in range(takelistWidget.columnCount()):
        #         item = takelistWidget.item(i, j)
        #         if item is not None:
        #             item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

        return takelistWidget
    
    def set_table_item(self, table_widget, row, col, value):
        twItem = QTableWidgetItem(value)
        twItem.setFlags(twItem.flags() & ~QtCore.Qt.ItemIsEditable)
        table_widget.setItem(row, col, twItem)


    def handleItemDoubleClicked(self, item):
        # row = item.row()
        # column = item.column()
        # value = item.text()
        # item_selected = self._takelist[row]
        pass

    def teardown(self):
        self.running = False
        if self.current_process is not None:
            self.current_process.teardown()
        self.close()

    def __del__(self):
        self.settings.setValue("mergeGeometry", self.saveGeometry())
        self.settings.setValue("mergeSplitterGeometry", self.splitter.sizes())
        self.teardown()

    def go(self):
        if self.go_button.text() == self.tr("Cancel"):
            self.running = False
            if self.current_process is not None:
                self.current_process.teardown()
            self.go_button.setText(self.tr("Merge Files"))
            return
        
        text_output_dir = self.path.text()
        if len(text_output_dir) == 0:
            QMessageBox.warning(self, self.tr("Merge Fbx File"), self.tr("Output directory can't empty."))
            return
        
        text_body_left_node = self.body_left_node.text()
        if len(text_body_left_node) == 0:
            QMessageBox.warning(self, self.tr("Merge Fbx File"), self.tr("Body left node can't empty."))
            return
        
        text_body_right_node = self.body_right_node.text()
        if len(text_body_right_node) == 0:
            QMessageBox.warning(self, self.tr("Merge Fbx File"), self.tr("Body right node can't empty."))
            return
        
        text_hand_left_node = self.hand_left_node.text()
        if len(text_hand_left_node) == 0:
            QMessageBox.warning(self, self.tr("Merge Fbx File"), self.tr("Hand left node can't empty."))
            return
        
        text_hand_right_node = self.hand_right_node.text()
        if len(text_hand_right_node) == 0:
            QMessageBox.warning(self, self.tr("Merge Fbx File"), self.tr("Hand right node can't empty."))
            return
        
        dict_node = {'body_left_node': text_body_left_node, 
                     'body_right_node': text_body_right_node, 
                     'hand_left_node': text_hand_left_node,
                     'hand_right_node': text_hand_right_node}
        
        self.running = True
        self.total_copied = 0
        self.total_failed = 0
        self.total_skipped = 0

        if self.current_process is not None:
            print("Finished: " + str(self.current_process))

        self.update_gui()

        if not self.running:
            print("Not running")
            return

        self.progress_bar.setValue(0)
        self.info_label.setText("")

        self.current_process = MergeFbxFilesThread(dict_node, self.merge_list, self.merge_file_count, text_output_dir)
        self.current_process.tick.connect(self.progress, QtCore.Qt.QueuedConnection)
        self.current_process.file_start.connect(self.file_start, QtCore.Qt.QueuedConnection)
        self.current_process.file_process.connect(self.file_process, QtCore.Qt.QueuedConnection)
        self.current_process.file_done.connect(self.file_done, QtCore.Qt.QueuedConnection)
        self.current_process.all_done.connect(self.all_file_done, QtCore.Qt.QueuedConnection)
        self.current_process.message.connect(self.log_message, QtCore.Qt.QueuedConnection)
        self.current_process.finished.connect(self.device_cleanup)
        self.work_threads.append(self.current_process)
        self.current_process.start()


    def update_gui(self):
        if self.running:
            self.path.setEnabled(False)
            self.path_button.setEnabled(False)
            self.go_button.setText(self.tr("Cancel"))
        else:
            self.path.setEnabled(True)
            self.path_button.setEnabled(True)
            self.go_button.setText(self.tr("Merge Files"))

    def log_message(self, message):
        self.log.appendPlainText(message)
        #print("> " + message)

    def is_done(self):
        return self.current_device >= len(self.selected_devices)

    def all_file_done(self):
        self.running = False
        self.update_gui()
        self.info_label.setText('')
        pass

    def device_cleanup(self):
        device_thread = self.sender()
        print("Thread done: " + str(device_thread))
        self.work_threads.remove(device_thread)

    def file_start(self):
        for row_index in range(self.table_row_count):
            self.set_table_item(self._takelist_table, row_index, self.COL_MERGE_RESULT, '')

        pass

    def file_process(self, row_index):
        self.set_table_item(self._takelist_table, row_index, self.COL_MERGE_RESULT, self.tr("Processing..."))
        pass

    def file_done(self, row_index, name, copy_state, error):
        if copy_state == MergeFbxFilesThread.MERGE_OK:
            self.set_table_item(self._takelist_table, row_index, self.COL_MERGE_RESULT, self.tr("OK"))
            merged = self.tr('MERGED')
            self.log.appendPlainText(f"{merged}: {name}")
            self.total_copied += 1
        elif copy_state == MergeFbxFilesThread.MERGE_SKIP:
            skipped = self.tr('SKIPPED')
            self.set_table_item(self._takelist_table, row_index, self.COL_MERGE_RESULT, self.tr("Skip"))
            self.log.appendHtml(f"<FONT COLOR=\"#444\">{skipped}: {name} ({error})</FONT>")
            self.total_skipped += 1
        elif copy_state == MergeFbxFilesThread.MERGE_FAIL:
            self.set_table_item(self._takelist_table, row_index, self.COL_MERGE_RESULT, self.tr("Failed"))
            failed = self.tr('FAILED')
            self.log.appendHtml(f"<FONT COLOR=\"#933\">{failed}: {name}: {str(error)}</FONT>")
            self.total_failed += 1
        pass

    def progress(self, minor):
        self.progress_bar.setValue(int(minor * 100.0))
        if self.current_process.current_file is not None:
            merging = self.tr('Merging')
            self.info_label.setText(f"{merging}: {str(self.current_process.current_file)}")

    def browse(self):
        d = self.settings.value(reg_fbx_merge_dir)
        if d is None or len(d) == 0:
            d = os.getcwd() + "/data"
            self.settings.setValue(reg_fbx_merge_dir, d)

        ret = QtWidgets.QFileDialog.getExistingDirectory(self, "Shoot Dir", d)
        if ret:
            self.path.setText(ret)
            self.settings.setValue(reg_fbx_merge_dir, ret)


