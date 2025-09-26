# install
python 3.12
vscode + python and python debugger plugin
pip install PySide6 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install python-osc -i https://pypi.tuna.tsinghua.edu.cn/simple

# Package to exe
# Generate translation files
pyside6-lupdate mainwnd.py dialog_fbxmerge.py dialog_takeitem.py worker_fbxmerge.py ./python/peel/__init__.py ./python/peel/harvest.py ./python/peel_devices/__init__.py ./python/peel_devices/avatar.py ./python/peel_devices/avatary.py ./python/peel_devices/motionbuilder2.py ./python/peel_devices/tracker.py ./python/peel_devices/unreal.py ./python/peel_devices/vrtrix.py ./python/peel_devices/files_download.py -ts i18n/zh_cn.ts

# Modify ts file by Qt Linguist
C:\qt_online\6.3.2\msvc2019_64\bin\linguist.exe

# Generate translation binary file
pyside6-lrelease i18n/zh_cn.ts -qm i18n/zh_cn.qm

# Generate resource python file from qrc file
pyside6-rcc mainwnd.qrc -o mainwnd_rc.py

# Package my product
Pyinstaller -D .\app_entry.py -n CMCapture --hidden-import pkgutil --hidden-import inspect --hidden-import pythonosc --collect-submodules pythonosc --hidden-import json --hidden-import xml.etree.ElementTree --hidden-import requests

