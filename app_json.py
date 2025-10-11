from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import mylogger
import json

def load_json_file(full_path):
    json_data = None
    try:
        with QApplication.setOverrideCursor(Qt.WaitCursor):
            with open(full_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)

        return json_data
    except Exception as e:
        msg = f'Open json file {full_path} Exception: {e}'
        mylogger.error(msg)
        return None
    
def save_json_file(full_path, json_data):
    try:
        import os
        # 确保目录存在
        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"创建目录: {directory}")
        
        with QApplication.setOverrideCursor(Qt.WaitCursor):
            json_data = json.dumps(json_data, default=encode_object, ensure_ascii=False, indent=2)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
        return True
    except Exception as e:
        msg = f'Save file Exception: {e}'
        mylogger.error(msg)
        return False
    
# 自定义编码器函数，处理对象的序列化
def encode_object(obj):
    class_name = type(obj).__name__
    
    if class_name == 'CaptureDevice' or class_name == 'TakeItem':
        return obj.__json__()
    else:
        return None
    #raise TypeError(f"Object of type '{type(obj).__name__}' is not JSON serializable")
