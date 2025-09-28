
SheetStyle_Window = """
                    QWidget{
                    background-color: #1F1F1F;
                    color: #FFFFFF;
                    font-family: Courier;
                    font-size: 14px;
                    }
                    """

SheetStyle_PushButton = """
            QPushButton {
                font-family:'Microsoft YaHei';
                font-size:10pt;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010);
                border: 1px solid #EAEAEA;
                color: #FFFFFF;
            }
        """

SheetStyle_ToolButton = """
            QPushButton {
                font-family:'Microsoft YaHei';
                font-size:10pt;
                background-color: #808080;  /* 设置按钮的背景为灰色 */
                color: #FFFFFF;  /* 设置按钮的字体颜色为白色 */
                border: 1px solid #EAEAEA;  /* 设置按钮的边框为淡白色 */
            }
            QPushButton:pressed {
                background-color: #A0A0A0;  /* 设置按钮按下时的背景为稍亮的灰色 */
                border: 1px solid #DADADA;  /* 设置按钮按下时的边框为稍亮的淡白色 */
            }
        """

SheetStyle_Button_Record = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff0000, stop: 1 #a00000);
                font-size: 18px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                color: white;
                border-radius: 4px;
                border: 2px solid #FFFFFF;
                border-style: outset;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff3333, stop: 1 #cc0000);
                border: 2px solid #E0E0E0;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #a00000, stop: 1 #ff0000);
                border-style: inset;
            }
        """

SheetStyle_DockWidget = """
            QDockWidget {
                background-color: #808080;  /* 设置标题栏背景色为灰色 */
            }
            QDockWidget QFrame {
                background-color: #808080;  /* 设置标题栏背景色为灰色 */
            }
            QDockWidget QFrame::title {
                background-color: #808080;  /* 设置标题栏背景色为灰色 */
                color: #FF0000;  /* 设置标题文字颜色为白色 */
                padding-left: 5px;  /* 设置标题文字的左内边距为 5px */
            }
        """

SheetStyle_TableWidget = """
            QTableWidget {
                background-color: #404040;  /* 设置表格的背景色为偏黑色 */
                color: #FFFFFF;  /* 设置表格的文本颜色为白色 */
                border: 1px solid #333333;  /* 优化边框样式 */
                gridline-color: #555555;  /* 优化表格线颜色 */
                font-family: 'Microsoft YaHei';  /* 统一字体 */
                font-size: 10pt;  /* 统一字体大小 */
                outline: none;  /* 去除焦点轮廓 */
            }
            QTableWidget::item {
                padding: 6px 8px;  /* 增加单元格内边距 */
                border-bottom: 1px solid #333333;  /* 添加底部边框 */
            }
            QTableWidget::item:selected {
                background-color: #0078D4;  /* 使用高级蓝色作为选中背景 */
                color: #FFFFFF;  /* 选中时文字颜色 */
            }
            QTableWidget::item:hover {
                background-color: #505050;  /* 悬停时的背景色 */
            }
            QTableCornerButton::section { 
                background-color: #404040; /* 设置表格的背景色为偏黑色 */
                border: 1px solid #333333;  /* 添加边框 */
            }
        """

SheetStyle_Label = """
            QLabel {
                background-color: #404040;
                color: #FFFFFF;
                border-radius: 2px;
                font-size: 10pt;
                font-family: 'Microsoft YaHei';
                padding: 4px 8px;
                border: 1px solid #333333;
            }
        """

SheetStyle_Label_Shot = """
            QLabel {
                background-color: #8B0000;
                color: #FFCCCC;
                border-radius: 4px;
                border: 2px solid #FF0000;
                font-size: 16px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                padding: 8px 12px;
            }
        """

SheetStyle_Edit_All = """
                    QLineEdit {
                        font-family: 'Microsoft YaHei';
                        font-size: 10pt;
                        color: #FFFFFF;
                        background-color: #2A2A2A;
                        border: 1px solid #333333;
                        border-radius: 2px;
                        padding: 6px 8px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #0078D4;
                        background-color: #333333;
                    }
                    QLineEdit:hover {
                        border: 1px solid #555555;
                    }
                    QLineEdit[readOnly="true"] {
                        background-color: #1A1A1A;
                        color: #CCCCCC;
                        border: 1px solid #444444;
                    }
                    QLineEdit[readOnly="true"]:hover {
                        border: 1px solid #666666;
                    }
                    """
SheetStyle_Edit_ReadOnly = """
                    QPlainTextEdit {
                        font-family: 'Microsoft YaHei';
                        font-size: 10pt;
                        color: #FFFFFF;
                        background-color: #2A2A2A;
                        border: 1px solid #333333;
                        border-radius: 2px;
                        padding: 6px 8px;
                    }
                    QPlainTextEdit:focus {
                        border: 1px solid #0078D4;
                        background-color: #333333;
                    }
                    QPlainTextEdit:hover {
                        border: 1px solid #555555;
                    }
                    QPlainTextEdit[readOnly="true"] {
                        background-color: #1A1A1A;
                        color: #CCCCCC;
                        border: 1px solid #444444;
                    }
                    QPlainTextEdit[readOnly="true"]:hover {
                        border: 1px solid #666666;
                    }
                    """
SheetStyle_Edit_Log = "background: #a6a6a6; color: black;"

SheetStyle_Combo_All = """
            QComboBox {
                font-family: 'Microsoft YaHei';
                font-size: 10pt;
                color: #FFFFFF;
                background-color: #2A2A2A;
                border: 1px solid #333333;
                border-radius: 2px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border: 1px solid #555555;
            }
            QComboBox:focus {
                border: 1px solid #0078D4;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #2A2A2A;
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
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #333333;
                selection-background-color: #0078D4;
            }
        """
SheetStyle_ProgressBar = "color: #ccc"

SheetStyle_ScrollBar = """
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #808080;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A0A0A0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #404040;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #808080;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #A0A0A0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """

SheetStyle_TableWidget_Header = """
            QHeaderView::section {
                background-color: #404143;
                color: white;
                border: 1px solid #333333;
                padding: 8px 12px;
                font-weight: bold;
                font-family: 'Microsoft YaHei';
                font-size: 10pt;
            }
            QHeaderView::section:hover {
                background-color: #505050;
            }
        """

SheetStyle_ListWidget = """
QListWidget {
    background-color: #1A1A1A;
    color: #CCCCCC;
    border: none;
    font-family: 'Microsoft YaHei';
    font-size: 10pt;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #333333;
    background-color: transparent;
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
"""
