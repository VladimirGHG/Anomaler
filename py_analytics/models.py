from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np
import joblib
import time
from sklearn.ensemble import IsolationForest
from sklearn.utils import shuffle


class AnomalyModel(ABC):
    model: Any
    last_report_time: Optional[float]

    def __init__(self):
        self.last_save_time = None
        self.model_snapshot = 0

    @abstractmethod
    def process_batch(self, new_values) -> list[dict]:
        """Processes a batch of values. Handles its own printing."""
        pass

    def save_model(self, path):
        """Saves the model to disk."""
        joblib.dump(self.model, path)
        self.last_save_time = time.time()
        print(f"[DISK] Model saved to {path}")

    @staticmethod
    def load_model(path):
        """Loads the model from disk."""
        return joblib.load(path)


class RiverStrategy(AnomalyModel):
    """Implements a streaming anomaly detection strategy using River's online training HalfSpaceTrees."""
    def __init__(self, window_size=250):
        from river import anomaly

        self.window_size = window_size
        self.model = anomaly.HalfSpaceTrees(window_size=self.window_size, n_trees=25, limits={"v": (0, 100)})
        self.model_snapshot = 0
        self.last_save_time = None
        self.count = 0 # Counts how many data points have been processed, used for warmup phase control

    def process_batch(self, new_values) -> list[dict]:

        results = []
        for v in new_values:
                # Still in Warmup
                feature_dict = {"v": v}
                if self.count < self.window_size:
                    self.model.learn_one(feature_dict)
                    results.append(
                        {"val": v, "is_anomaly": False, "anomaly_level": -1, "status": "WARMUP"})
                    self.count += 1
                else:
                    score = self.model.score_one(feature_dict)
                    self.model.learn_one(feature_dict)
                    results.append({
                        "val": v,
                        "is_anomaly": score > 0.7,
                        "anomaly_level": self.anomaly_level(score),
                        "status": "READY"
                    })
        return results
    
    def anomaly_level(self, score: float) -> int:
        """Converts a raw anomaly score into a discrete level (0-5) for easier interpretation."""
        if self.count < self.window_size:
            return -1  # Still warming up, treat everything as normal
        
        if score < 0.3:
            return 0  # Normal
        elif score < 0.5:
            return 1  # Low Anomaly
        elif score < 0.7:
            return 2  # Moderate Anomaly
        elif score < 0.9:
            return 3  # High Anomaly
        elif score < 0.95:
            return 4  # Severe Anomaly
        else:
            return 5  # Extreme Anomaly

class IsolationForestStrategy(AnomalyModel):
    """Implements a batch-based Isolation Forest strategy with a warmup phase and periodic retraining."""
    def __init__(self, contamination=0.1):

        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.last_save_time = None
        self.model_snapshot = 0
        self.data_buffer = []
        self.buffer_limit = 50
        self.max_buffer_size = 200
        self.train_every_n_points = 1000
        self.points_since_last_train = 0
        self.is_fitted = False

    def process_batch(self, new_values) -> list[dict]:
        self.data_buffer.extend(new_values)
        self.points_since_last_train += len(new_values)

        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer = self.data_buffer[-self.max_buffer_size:]

        # If we have enough data and it's time to train (or first time training)
        if len(self.data_buffer) >= self.buffer_limit:
            if (
                not self.is_fitted
                or self.points_since_last_train >= self.train_every_n_points
            ):
                print(f"\n[TRAINING] Fitting IsolationForest with {len(self.data_buffer)} data points...")
                X = np.array(self.data_buffer).reshape(-1, 1)
                self.model.fit(shuffle(X, random_state=42))
                self.is_fitted = True
                self.points_since_last_train = 0

        results = []
        if not self.is_fitted:
            # Still in Warmup
            for v in new_values:
                print(f"\n[DEBUG] Processing value: {v} (WARMUP)")
                results.append(
                    {"val": v, "is_anomaly": False, "status": "WARMUP"})
        else:
            # Model is ready, predict the batch
            predictions = self.model.predict(
                np.array(new_values).reshape(-1, 1))
            for v, pred in zip(new_values, predictions):
                results.append(
                    {"val": v, "is_anomaly": (pred == -1), "status": "READY"}
                )

        return results
