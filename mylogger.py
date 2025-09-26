import logging
import os

logger = None

def initLog():
    global logger
    if logger is None:
        logger = logging.getLogger('CMCapture')
    
    logger.setLevel(level = logging.INFO)

    log_dir = os.getcwd() + "\\log"
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    handler = logging.FileHandler("log\\CMCapture.txt")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def info(logmsg):
    global logger
    if logger is None:
        return
    
    logger.info(logmsg)


def error(logmsg):
    global logger
    if logger is None:
        return
    
    logger.error(logmsg)
