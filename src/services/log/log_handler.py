import logging

class LoggingService():
    def __init__(self, file_dir:str):
        common_format = logging.Formatter('[%(levelname)s] %(asctime)s | %(message)s')

        # handlers
        self.logger = logging.getLogger(__name__)
        
        self.c_handler = logging.StreamHandler()
        self.f_handler = logging.FileHandler(file_dir)
        
        # set level
        self.c_handler.setLevel(logging.WARNING)
        self.f_handler.setLevel(logging.ERROR)

        # set formatter to common format
        self.c_handler.setFormatter(common_format)
        self.f_handler.setFormatter(common_format)
        
        # add handlers
        self.logger.addHandler(self.c_handler)
        self.logger.addHandler(self.f_handler)

    # logs warning
    def log_warning(self, file_name:str, func_name:str, msg:str):
        self.logger.warning(f'{file_name.split("/")[-1]}:{func_name}() - {msg}')
        
    # logs error
    def log_error(self, file_name:str, func_name:str, msg:str):
        self.logger.error(f'{file_name.split("/")[-1]}:{func_name}() - {msg}')