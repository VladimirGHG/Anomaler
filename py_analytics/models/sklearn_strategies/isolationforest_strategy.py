import time
from datetime import datetime  

import numpy as np
from sklearn.utils import shuffle
from sklearn.ensemble import IsolationForest

from py_analytics.models.base import AnomalyModel, BatchBufferPolicy
from py_analytics.models.base import AnomalyModel

class IsolationForestStrategy(AnomalyModel):
    """Implements a batch-based Isolation Forest strategy with a warmup phase and periodic retraining."""
    def __init__(self, contamination: float = 0.01, buffer_limit: int = 50, max_buffer_size: int = 200, buffer_policy: BatchBufferPolicy = BatchBufferPolicy.CLEAR_ON_DRIFT):

        super().__init__("SKlearnIsolatedForest")
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.buffer_limit = buffer_limit # Minimum number of data points to start training, even if we detect drift before reaching this limit. This allows us to have a stable initial model before we start reacting to drift.
        self.max_buffer_size = max_buffer_size # Maximum number of data points to keep in the buffer for training, even if we clear on drift. This allows us to have a sliding window of recent data for training after a drift event.
        self.buffer_policy = buffer_policy # Policy to determine how to manage the buffer when drift is detected. CLEAR_ON_DRIFT will clear the buffer immediately, while KEEP_WINDOW will keep the last max_buffer_size data points as a sliding window for training.
        self.retrain_needed = False

    def process_batch(self, mad, median, new_values) -> list[dict]:
        self.data_buffer.extend(list(new_values.values()))

        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer = self.data_buffer[-self.max_buffer_size:]

        for time_, v in new_values.items():
            self.drift_detector.update(v)
            if self.drift_detector.drift_detected:

                # print(f"\n[DRIFT] Concept drift detected at value: {v}. Retraining model...")
                self.logger.info(f"\n[DRIFT] Concept drift detected at value: {v}. Retraining model...")

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
        # print(f"\n[TRAINING] Fitting IsolationForest with {len(self.data_buffer)} data points...")
        self.logger.info(f"\n[TRAINING] Fitting IsolationForest with {len(self.data_buffer)} data points...")

        X = np.array(self.data_buffer).reshape(-1, 1)
        self.model.fit(shuffle(X, random_state=42))
        self.is_fitted = True

    def _generate_results(self, mad, median, new_values) -> list[dict]:
        """Generates results for the current batch of new values based on the model's predictions."""
        results = []
        if not self.is_fitted:
            # Still in Warmup
            for time_, v in new_values.items():
                # print(f"\n[DEBUG] Processing value: {v} (WARMUP)")
                self.logger.debug(f"Processing value: {v} (WARMUP)")
                results.append({"val": v, "is_anomaly": False, "anomaly_level": -1, "status": "WARMUP"})
        else:
            # Model is ready, predict the batch
            pred_start_time = time.time()
            predictions = self.model.predict(np.array(list(new_values.values())).reshape(-1, 1))
            pred_end_time = time.time()
            total_pred_time = pred_end_time - pred_start_time
            time_format = "%Y-%m-%d %H:%M:%S.%f"
            on_each_time = total_pred_time / len(new_values) if new_values else 0
            for i, ((time_, v), pred) in enumerate(zip(new_values.items(), predictions)):
                # print(f"time_: {time_}\n")
                comp_time = float(time_) if isinstance(time_, (int, float)) else datetime.strptime(time_, time_format).timestamp()
                total_process_time = (pred_start_time - comp_time) + i * on_each_time # Approximate the time taken for the entire process of this value.
                results.append({"val": v, "is_anomaly": (pred == -1), "anomaly_level": self.anomaly_level(mad, median, v), "processed_in": total_process_time, "status": "READY"})

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