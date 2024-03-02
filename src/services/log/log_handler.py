import logging

def create_logging_service(file_dir: str) -> logging.Logger:
    logger = logging.getLogger(__name__)

    # handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('file.log')
    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    c_format = logging.Formatter('%(filename)s:%(funcName)s() - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(filename)s:%(funcName)s() - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger