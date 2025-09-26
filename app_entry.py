import mylogger
import sys,os

from mainwnd import MainWindow, AppName
from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import (QApplication)
from PySide6.QtGui import QIcon

APP_UNIQUE_KEY = "mutex_name_cmcapture"

class QtSingleApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.shared_memory = QSharedMemory(APP_UNIQUE_KEY)

        if self.shared_memory.attach():
            mylogger.info('Another instance is already running.')
            sys.exit(0)

        self.shared_memory.create(1)

if __name__ == '__main__':

    # Init log module.
    mylogger.initLog()
    mylogger.info(f'{AppName} startup.')

    app = QtSingleApplication(sys.argv)

    # 创建一个 QIcon 对象
    icon = QIcon.fromTheme('app-icon', QIcon(':/images/app_icon'))
    if icon is not None:
        # 将该 QIcon 对象设置为 QApplication 的属性
        app.setWindowIcon(icon)

    # Get current work folder.
    cur_work_dir = os.getcwd()
    mylogger.info(f'Current work directory: {cur_work_dir}')
    sys.path.append(cur_work_dir + '\\python')

    main_win = MainWindow()
    #main_win.setGeometry(50, 50, 1280, 960)
    main_win.showMaximized()

    app_result = app.exec()
    mylogger.info(f'{AppName} shutdown. exitcode: {app_result}')
    sys.exit(app_result)
