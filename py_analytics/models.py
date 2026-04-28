from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np
from river import drift, anomaly
from enum import Enum
import joblib
import hashlib
import os
import time
from sklearn.ensemble import IsolationForest
from sklearn.utils import shuffle

class RiverDriftPolicy(Enum):
    RESET = "reset" # Reset the model to scratch
    ADAPT = "adapt" # Let the model adapt naturally to new data

class BatchBufferPolicy(Enum):
    CLEAR_ON_DRIFT = "clear_on_drift" # Clear the buffer when drift is detected
    KEEP_WINDOW = "keep_window" # Keep the last N data points as a sliding window, even after drift

class AnomalyModel(ABC):
    model: Any
    last_report_time: Optional[float]

    def __init__(self):
        self.name = None
        self.model = None
        self.last_save_time = None
        self.drift_detector = None
        self.data_buffer = []
        self.config_hash = self._generate_config_hash()
        self.version = "1.0.0"
        self.is_fitted = False
        self.model_snapshot = 0
        self.window_size = 0
        self.median = 0
        self.count = 0
        self.mad = 0

        self.samples_seen_at_last_save = 0

    @abstractmethod
    def process_batch(self, mad, median, new_values: list[int]) -> list[dict]:
        """Processes a batch of values. Handles its own printing."""
        pass
    
    def save_model(self, path, metrics = None):
        """Saves the whole AnomalyModel object with the model to disk."""
        was_retrained = False
    
        if self.name == "RiverHalfSpaceTrees":
            samples_since_save = self.count - self.samples_seen_at_last_save
            if self.count == 0 or samples_since_save >= self.window_size:
                was_retrained = True
                self.samples_seen_at_last_save = self.count
                
        elif self.name == "SKlearnIsolatedForest":
            if self.is_fitted:
                was_retrained = True

        new_version = self._get_next_version(was_retrained) # Major.Minor.Patch
        self.version = new_version
        self.config_hash = self._generate_config_hash()

        metadata = {
            "strategy_name": self.name,
            "version": new_version, # Major.Minor.Patch
            "parent_hash": getattr(self, 'current_hash', None),
            "current_hash": self.config_hash,
            "metrics": metrics or {},
            "timestamp": time.time()
        }
        bundle = {
            "metadata": metadata,
            "model_state": self 
        }
    
        filename = f"{self.name}_{metadata['version']}_{self.config_hash}.pkl"

        if not os.path.exists(path):
            os.makedirs(path)

        joblib.dump(bundle, os.path.join(path, filename))
        self.last_save_time = time.time()
        print(f"[DISK] AnomalyModel saved to {path}")

    @staticmethod
    def load_model(path):
        """Loads the bundle and returns the restored AnomalyModel object."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")

        bundle = joblib.load(path)
        
        metadata = bundle.get("metadata", {})
        model_obj = bundle.get("model_state")

        print(f"--- Loading Model ---")
        print(f"Strategy: {metadata.get('strategy_name')}")
        print(f"Version:  {metadata.get('version')}")
        print(f"Created:  {time.ctime(metadata.get('timestamp'))}")
        
        actual_hash = model_obj._generate_config_hash()
        if actual_hash != metadata.get("current_hash"):
            print("[WARNING] Config hash mismatch! Model might have been modified.")

        return model_obj
    
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
    
class RiverStrategy(AnomalyModel):
    """Implements a streaming anomaly detection strategy using River's online training HalfSpaceTrees."""
    def __init__(self, window_size=250, drift_policy=RiverDriftPolicy.RESET):
        
        self.name = "RiverHalfSpaceTrees"
        self.window_size = window_size
        self.drift_policy = drift_policy
        self._init_model()
        self.model_snapshot = 0
        self.last_save_time = None
        self.count = 0 # Counts how many data points have been processed, used for warmup phase control

        self.drift_detector = drift.ADWIN()

    def _init_model(self):
        self.model = anomaly.HalfSpaceTrees(window_size=self.window_size, n_trees=25, limits={"v": (-100, 100)})

    @property
    def is_fitted(self):
        # The model is "fitted" if it has processed at least one full window
        return self.count >= self.window_size
    
    def process_batch(self, mad, median, new_values) -> list[dict]:

        results = []
        for v in new_values:
                feature_dict = {"v": v}
                self.drift_detector.update(v)

                if self.drift_detector.drift_detected:
                    if self.drift_policy == RiverDriftPolicy.RESET:
                        print(f"\n[DRIFT] Concept drift detected at value: {v}. Retraining model...")
                        self._init_model()
                        self.count = 0 # Reset warmup count as well
                        self.samples_seen_at_last_save = -1
                    
                # Still in Warmup
                if self.count < self.window_size:
                    self.model.learn_one(feature_dict)
                    results.append(
                        {"val": v, "is_anomaly": False, "score": -1, "status": "WARMUP"})
                    self.count += 1
                else:
                    score = self.model.score_one(feature_dict)
                    self.model.learn_one(feature_dict)
                    results.append({
                        "val": v,
                        "is_anomaly": score > 0.7,
                        "score": score,
                        "status": "READY"
                    })
        return results

    def __str__(self) -> str:
        return self.name

class IsolationForestStrategy(AnomalyModel):
    """Implements a batch-based Isolation Forest strategy with a warmup phase and periodic retraining."""
    def __init__(self, contamination=0.01, buffer_limit=50, max_buffer_size=200, buffer_policy=BatchBufferPolicy.CLEAR_ON_DRIFT):

        self.name = "SKlearnIsolatedForest"
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.data_buffer = []
        self.last_save_time = None
        self.model_snapshot = 0
        self.buffer_limit = buffer_limit # Minimum number of data points to start training, even if we detect drift before reaching this limit. This allows us to have a stable initial model before we start reacting to drift.
        self.max_buffer_size = max_buffer_size # Maximum number of data points to keep in the buffer for training, even if we clear on drift. This allows us to have a sliding window of recent data for training after a drift event.
        self.buffer_policy = buffer_policy #

        self.drift_detector = drift.ADWIN()
        self.is_fitted = False
        self.retrain_needed = False

    def process_batch(self, mad, median, new_values) -> list[dict]:
        self.data_buffer.extend(new_values)

        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer = self.data_buffer[-self.max_buffer_size:]

        for v in new_values:
            self.drift_detector.update(v)
            if self.drift_detector.drift_detected:
                print(f"\n[DRIFT] Concept drift detected at value: {v}. Retraining model...")
                self.retrain_needed = True
                if self.buffer_policy == BatchBufferPolicy.CLEAR_ON_DRIFT:
                    self.is_fitted = False # Reset fitted status to trigger warmup phase again
                    self.data_buffer = [] # Clear buffer immediately on drift detection
                break

        # Determine if we should train the model: either we're still in warmup and have enough data, or we've detected drift and need to retrain
        should_train = (not self.is_fitted and len(self.data_buffer) >= self.buffer_limit) or self.retrain_needed

        if should_train:
            self._train_model()
            self.retrain_needed = False

        return self._generate_results(mad, median, new_values)
    
    def _train_model(self):
        print(f"\n[TRAINING] Fitting IsolationForest with {len(self.data_buffer)} data points...")
        X = np.array(self.data_buffer).reshape(-1, 1)
        self.model.fit(shuffle(X, random_state=42))
        self.is_fitted = True

    def _generate_results(self, mad, median, new_values) -> list[dict]:
        """Generates results for the current batch of new values based on the model's predictions."""
        results = []
        if not self.is_fitted:
            # Still in Warmup
            for v in new_values:
                print(f"\n[DEBUG] Processing value: {v} (WARMUP)")
                results.append({"val": v, "is_anomaly": False, "anomaly_level": -1, "status": "WARMUP"})
        else:
            # Model is ready, predict the batch
            predictions = self.model.predict(np.array(new_values).reshape(-1, 1))
            for v, pred in zip(new_values, predictions):
                results.append({"val": v, "is_anomaly": (pred == -1), "anomaly_level": self.anomaly_level(mad, median, v),"status": "READY"})

        return results
    
    def anomaly_level(self, mad: int, median: int, check_value: int):
        """Dynamically identify anomaly levels for any distribution"""
        diff = np.abs(check_value - median)

        if diff > 4 * mad: return 3
        elif diff > 3 * mad: return 2
        elif diff > 2 * mad: return 1
        return 0

    def __str__(self):
        return self.name