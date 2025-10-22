# import configparser
from PySide6.QtCore import QSettings
import os
import app_const
import mylogger

class AppConfig:
    def __init__(self):
        self._settings = QSettings(app_const.CompanyName, app_const.AppName)
        self._current_path = os.path.dirname(__file__)

    def save_ui_config(self, mainWnd):
        try:
            self.save_ui_table_info('TakeTable', mainWnd._table_takelist)
            self.save_ui_table_info('DeviceTable', mainWnd._deviceTable)
        except Exception as e:
            msg = f'Save UI info to register failed, Exception: {e}'
            mylogger.error(msg)
            return None
        
    def load_ui_config(self, mainWnd):
        """加载UI配置，失败时跳过"""
        try:
            # 加载表格列宽信息
            self.load_ui_table_info('TakeTable', mainWnd._table_takelist)
            self.load_ui_table_info('DeviceTable', mainWnd._deviceTable)

            # 加载文件路径信息
            mainWnd._save_fullpath = self._settings.value('LastOpenFile', '')
            mainWnd._open_folder = self._settings.value('LastOpenFolder', self._current_path)
            
            # 读取当前采集者
            try:
                cur = self._settings.value('CurrentCollectorJson')
                if cur:
                    import json
                    mainWnd.current_collector = json.loads(cur)
                    if hasattr(mainWnd, '_collector_label') and mainWnd._collector_label:
                        name = mainWnd.current_collector.get('collector_name','')
                        cid = mainWnd.current_collector.get('collector_id','')
                        mainWnd._collector_label.setText(mainWnd.tr('采集者: ') + f"{name}({cid})")
            except Exception as e:
                print(f"加载采集者信息失败，跳过: {e}")
                pass
                
        except Exception as e:
            print(f"加载UI配置失败，跳过: {e}")
            return

    #设置TableWidget的宽度信息
    def save_ui_table_info(self, section, tableWidget):
        # QTableWidget column count
        device_column_count = tableWidget.columnCount()
        column_value = ''
        for i in range(device_column_count):
            column_value += str(tableWidget.columnWidth(i))
            column_value += ' '
        
        #去除尾部空格
        column_value = column_value.strip()
        self._settings.setValue(section + 'ColumnWidth', column_value)

    #保存当前工程文件的全路径
    def save_open_file(self, full_path):
        if full_path is None or len(full_path) == 0:
            return
        
        try:
            self._settings.setValue('LastOpenFile', full_path)
            # 获取目录部分
            last_open_folder = os.path.dirname(full_path)
            self._settings.setValue('LastOpenFolder', last_open_folder)
        except Exception as e:
            msg = f'Save opening full path to register, Exception: {e}'
            mylogger.error(msg)
            return None

    def load_ui_table_info(self, section, tableWidget):
        """加载表格列宽信息，失败时跳过"""
        try:
            take_column_width = self._settings.value(section + 'ColumnWidth')
            if take_column_width is None or len(take_column_width) == 0:
                return
            
            #去除尾部空格
            take_column_width = take_column_width.strip()
            str_col_w = take_column_width.split(' ')
            
            # 确保列数匹配
            current_column_count = tableWidget.columnCount()
            for i in range(min(len(str_col_w), current_column_count)):
                try:
                    col_width = int(str_col_w[i])
                    if col_width > 0:
                        tableWidget.setColumnWidth(i, col_width)
                except (ValueError, IndexError) as e:
                    print(f"跳过列 {i} 的宽度设置: {e}")
                    continue
                    
        except Exception as e:
            print(f"加载表格 {section} 列宽信息失败，跳过: {e}")
            return
