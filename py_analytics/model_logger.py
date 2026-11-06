import logging
import os
import re
import sys

class ModelLogger:
    def __init__(self, model_name: str, log_dir: str = "logs/analysis/models"):
        self.model_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(model_name)).strip("._") or "model"
        self.log_dir = log_dir

        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = logging.getLogger(f"py_analytics.model.{self.model_name}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        # Recreating a strategy with the same identity must not duplicate output.
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        file_path = os.path.join(self.log_dir, f"{self.model_name}.log")
        file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)

        console_formatter = logging.Formatter(f'\033[94m[{self.model_name}]\033[0m %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)
