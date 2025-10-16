# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

# 设置输出目录
DISTPATH = '../dist'  # 相对于当前目录的上级目录下的dist文件夹
WORKPATH = './build'  # 构建临时文件目录

# 收集所有需要的模块
hiddenimports = [
    'pkgutil', 'inspect', 'pythonosc', 'json', 'xml.etree.ElementTree', 
    'requests', 'pandas', 'openpyxl', 'PySide6', 'PySide6.QtCore',
    'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtNetwork',
    'service.db_controller', 'export_manager', 'login_dialog',
    'task_list_widget', 'task_property_widget', 'factory_widget',
    'dict_shotname', 'takeitem', 'dialog_takeitem', 'app_config',
    'app_json', 'app_common', 'app_css', 'app_const', 'mylogger',
    # 添加项目特定的模块 - 使用相对导入
    'PeelApp', 'PeelApp.cmd',
    'peel', 'peel.harvest',
    'peel_devices', 'peel_devices.avatar', 'peel_devices.avatary',
    'peel_devices.common', 'peel_devices.device_util', 'peel_devices.files_download',
    'peel_devices.motionbuilder2', 'peel_devices.osc', 'peel_devices.tracker',
    'peel_devices.unreal', 'peel_devices.vrtrix', 'peel_devices.xml_udp'
]
hiddenimports += collect_submodules('pythonosc')
hiddenimports += collect_submodules('PySide6')

# 收集数据文件
datas = [
    ('images', 'images'),  # 复制images文件夹
    ('i18n', 'i18n'),      # 复制i18n文件夹
    ('mainwnd.qrc', '.'),  # 复制资源文件
    ('python', 'python'),  # 复制python模块目录
]

# 收集二进制文件
binaries = [
    ('FbxMergeHelper.dll', '.'),
    ('libfbxsdk.dll', '.'),
    ('Qt6Core.dll', '.'),
]

a = Analysis(
    ['app_entry.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CMCapture',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/app_icon.png',  # 暂时注释掉图标，避免PIL依赖
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CMCapture',
    distpath=DISTPATH,  # 指定输出目录
)