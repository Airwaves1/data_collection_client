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
    
    # 添加python目录到Python路径
    # 在打包环境中，python模块在_internal目录中
    internal_python_path = os.path.join(cur_work_dir, '_internal', 'python')
    if os.path.exists(internal_python_path):
        sys.path.insert(0, internal_python_path)
        mylogger.info(f'Added internal python path: {internal_python_path}')
    else:
        # 尝试在当前目录查找
        python_path = os.path.join(cur_work_dir, 'python')
        if os.path.exists(python_path):
            sys.path.insert(0, python_path)
            mylogger.info(f'Added python path: {python_path}')
        else:
            # 尝试在exe文件所在目录查找
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_python_path = os.path.join(exe_dir, 'python')
            if os.path.exists(exe_python_path):
                sys.path.insert(0, exe_python_path)
                mylogger.info(f'Added exe python path: {exe_python_path}')
            else:
                mylogger.error('Python module path not found')

    main_win = MainWindow()
    #main_win.setGeometry(50, 50, 1280, 960)
    main_win.showMaximized()

    app_result = app.exec()
    mylogger.info(f'{AppName} shutdown. exitcode: {app_result}')
    sys.exit(app_result)
