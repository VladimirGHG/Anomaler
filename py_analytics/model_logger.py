import logging
import os
import sys

class ModelLogger:
    def __init__(self, model_name: str, log_dir: str = "logs"):
        self.model_name = model_name
        self.log_dir = log_dir

        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = logging.getLogger(self.model_name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        file_path = os.path.join(self.log_dir, f"{model_name}.log")
        file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)

        console_formatter = logging.Formatter(f'\033[94m[{model_name}]\033[0m %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)