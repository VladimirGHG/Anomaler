from abc import ABC, abstractmethod
from enum import Enum
import hashlib
import os
import time
from typing import Any, Optional

import joblib
from river import drift

from ..model_logger import ModelLogger

class RiverDriftPolicy(Enum):
    RESET = "reset" # Reset the model to scratch
    ADAPT = "adapt" # Let the model adapt naturally to new data

class BatchBufferPolicy(Enum):
    CLEAR_ON_DRIFT = "clear_on_drift" # Clear the buffer when drift is detected
    KEEP_WINDOW = "keep_window" # Keep the last N data points as a sliding window, even after drift

class Strategy(ABC):
    model: Any
    last_report_time: Optional[float]

    def __init__(self, name: str):
        self.name = name
        self.version = "1.0.0"
        self.is_fitted = False
        self.count = 0 # Counts how many data points have been processed, used for warmup phase control

        self.drift_detector = drift.ADWIN()
        self.data_buffer = []

        self.config_hash = self._generate_config_hash()
        self.last_save_time = time.time()
        self.model_snapshot = 0
        self.parent_hash = None

        self.samples_seen_at_last_save = 0

        # Create a unique identifier for the logger of the model.
        self.uid = f"{self.name}_v{self.version}_{self.config_hash[:8]}"
        self.logger = ModelLogger(self.uid)

    @abstractmethod
    def process_batch(self, mad, median, new_values: dict[str, int]) -> list[dict]:
        """Processes a batch of values. Handles its own printing."""
        pass
    
    def save_model(self, path, metrics=None):
        # Determine retraining status
        was_retrained = self._check_if_retrained()

        # Update Versioning
        self.version = self._get_next_version(was_retrained)
        self.config_hash = self._generate_config_hash()

        # Bundle and Save
        metadata = {
            "strategy": self.name,
            "version": self.version,
            "metrics": metrics or {},
            "parent_hash": getattr(self, "parent_hash", "None"),
            "timestamp": time.time(),
            "current_hash": self.config_hash
        }
        
        os.makedirs(path, exist_ok=True)
        filename = f"{self.version}_{self.config_hash[:8]}.pkl"
        full_save_path = os.path.join(path, filename)
        joblib.dump({"metadata": metadata, "model_state": self}, full_save_path)
        self.last_save_time = time.time()
        self.samples_seen_at_last_save = self.count

        # print(f"[DISK] Saved to {full_save_path}")
        self.logger.info(f"[DISK] Saved to {full_save_path}")

    @staticmethod
    def load_model(path):
        """Loads the bundle and returns the restored AnomalyModel object."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")

        bundle = joblib.load(path)
        
        metadata = bundle.get("metadata", {})
        model_obj = bundle.get("model_state")
        model_obj.parent_hash = metadata.get("current_hash", "None")
        print(f"--- Loading Model ---")
        print(f"Metadata: {metadata}")
        actual_hash = model_obj._generate_config_hash()
        if actual_hash != metadata.get("current_hash"):
            print("[WARNING] Config hash mismatch! Model might have been modified.")
            
        return model_obj
    
    def _check_if_retrained(self) -> bool:
        """Default logic for retraining check."""
        if self.name == "RiverHalfSpaceTrees":
            return self.count == 0 or (self.count - self.samples_seen_at_last_save) >= getattr(self, 'window_size', 250)
        return self.is_fitted

    def _generate_config_hash(self):
        """Creates a fingerprint of the hyperparameters only."""
        relevant_params = {k: v for k, v in self.__dict__.items() 
                          if isinstance(v, (int, float, str, bool, Enum))}
        return hashlib.md5(str(sorted(relevant_params.items())).encode()).hexdigest()

    def _get_next_version(self, was_retrained: bool):
        major, minor, patch = map(int, self.version.split('.'))

        current_config_hash = self._generate_config_hash()
        config_changed = current_config_hash != self.config_hash
        
        if was_retrained:
            minor += 1
            patch = 0
        elif config_changed:
            patch += 1
        else:
            patch += 1

        return f"{major}.{minor}.{patch}"