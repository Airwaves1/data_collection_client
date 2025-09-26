
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
            QPushButton{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ff0000, stop: 1 #a00000); font-size: 22px; font-family: Courier; font-weight: bold;
                color: white; border-radius: 5px; border: 2px white;
                border-style: outset;
            }
            QPushButton:pressed{
                            background-color:qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #a00000, stop: 1 #ff0000);
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
                border: 2px groove gray;  /* 去除表格的边框 */
                gridline-color: #808080;  /* 设置表格线的颜色为灰色 */
            }
            QTableWidget::item:selected {
                background-color: #707070;  /* 设置选中单元格的背景色为深灰色 */
            }
            QTableCornerButton::section { 
                background-color:#404040; /* 设置表格的背景色为偏黑色 */
            }
        """

SheetStyle_Label = """
            QLabel{background-color:rgb(166,166,166); color: black; border-radius: 5px; font-size: 16px; font-family: Courier;}
        """

SheetStyle_Label_Shot = """
            QLabel{background-color:rgb(67,25,8); color: rgb(255, 204, 204); border-radius: 5px; border: 2px solid rgb(255, 5, 5); font-size: 16px; font-family: Courier; }
        """

SheetStyle_Edit_All = """
                    font-family:'Microsoft YaHei';font-size:18pt; color:black; background-color:rgb(235,235,235); border-radius:2px; padding:0px
                    """
SheetStyle_Edit_ReadOnly = "color:black; background-color:rgb(166,166,166); border-radius:2px; padding:0px"
SheetStyle_Edit_Log = "background: #a6a6a6; color: black;"

SheetStyle_Combo_All = "color:black; background-color:rgb(235,235,235)"
SheetStyle_ProgressBar = "color: #ccc"

SheetStyle_TableWidget_Header = "QHeaderView::section {background-color: #404143;color: white;}"
