from abc import ABC, abstractmethod
from typing import Any
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.utils import shuffle


class AnomalyModel(ABC):
    model: Any

    @abstractmethod
    def process_batch(self, new_values) -> list[dict]:
        """Processes a batch of values. Handles its own printing."""
        pass


class RiverStrategy(AnomalyModel):
    """Implements a streaming anomaly detection strategy using River's online training HalfSpaceTrees."""
    def __init__(self):
        from river import anomaly

        self.model = anomaly.HalfSpaceTrees()

    def process_batch(self, new_values) -> list[dict]:
        results = []
        for v in new_values:
            score = self.model.score_one({"v": v})
            self.model.learn_one({"v": v})
            results.append({
                "val": v, 
                "is_anomaly": score > 0.7, 
                "status": "READY"
            })
        return results

class IsolationForestStrategy(AnomalyModel):
    """Implements a batch-based Isolation Forest strategy with a warmup phase and periodic retraining."""
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(contamination=contamination, random_state=42)
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
