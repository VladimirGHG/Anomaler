import time
from datetime import datetime  

import numpy as np
from sklearn.model_selection import KFold
from sklearn.utils import shuffle
from sklearn.ensemble import IsolationForest

from py_analytics.models.base import AnomalyModel, BatchBufferPolicy

class IsolationForestStrategy(AnomalyModel):
    """Implements a batch-based Isolation Forest strategy with a warmup phase and periodic retraining."""
    def __init__(self, contamination: float = None, buffer_limit: int = 200, max_buffer_size: int = 400, buffer_policy: BatchBufferPolicy = BatchBufferPolicy.CLEAR_ON_DRIFT, k: float = 3.0):

        super().__init__("SKlearnIsolatedForest")
        if contamination:
            self.model = IsolationForest(contamination=contamination, random_state=42, max_samples=min(256, buffer_limit))
        else:
            self.model = IsolationForest(random_state=42, max_samples=min(256, buffer_limit))
        self.buffer_limit = buffer_limit # Minimum number of data points to start training, even if we detect drift before reaching this limit. This allows us to have a stable initial model before we start reacting to drift.
        self.max_buffer_size = max_buffer_size # Maximum number of data points to keep in the buffer for training, even if we clear on drift. This allows us to have a sliding window of recent data for training after a drift event.
        self.buffer_policy = buffer_policy # Policy to determine how to manage the buffer when drift is detected. CLEAR_ON_DRIFT will clear the buffer immediately, while KEEP_WINDOW will keep the last max_buffer_size data points as a sliding window for training.
        self.k = k # The number of standard deviations below the mean score to set the anomaly threshold. A higher k will make the model more conservative in flagging anomalies, while a lower k will make it more sensitive.
        self.retrain_needed = False
        self.score_threshold = None # Will be set after the first training to determine anomaly threshold based on model's score distribution.
        self.min_retrain_interval_s = 30 # Minimum time interval in seconds between retraining events to avoid excessive retraining in rapid succession.
        self._last_retrain_time = 0

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
            if time.time() - self._last_retrain_time < self.min_retrain_interval_s:
                self.logger.debug("Drift detected but retrain cooldown active, deferring")
            else:
                self._train_model()
                self._last_retrain_time = time.time()
                self.retrain_needed = False

        return self._generate_results(mad, median, new_values)
    
    def _train_model(self):

        self.logger.info(f"\n[TRAINING] Fitting IsolationForest with {len(self.data_buffer)} data points...")
        X = np.array(self.data_buffer).reshape(-1, 1)

        if not np.all(np.isfinite(X)):
            self.logger.warning("Non-finite values in buffer, filtering before training")
            X = X[np.isfinite(X).flatten()]

        if len(X) < self.buffer_limit:
            self.logger.warning("Insufficient valid data to train, skipping")
            return
        
        try:
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            oof_scores = np.zeros(len(X))

            for train_idx, test_idx in kf.split(X):
                fold_model = IsolationForest(random_state=42)
                fold_model.fit(X[train_idx])
                oof_scores[test_idx] = fold_model.score_samples(X[test_idx])

            self.model.fit(shuffle(X, random_state=42))
            self.is_fitted = True
        except Exception:
            self.logger.exception("Model training failed, keeping previous model state")
            return
        
        train_scores = self.model.score_samples(X)
        score_median = np.median(train_scores)
        score_mad = np.median(np.abs(train_scores - score_median))
        self.score_threshold = score_median - self.k * 1.4826 * score_mad
        self.logger.warning(
            f"[SCORE DIAG] min={oof_scores.min():.4f} p1={np.percentile(oof_scores,1):.4f} "
            f"median={score_median:.4f} mad={score_mad:.4f} threshold={self.score_threshold:.4f} max={oof_scores.max():.4f}"
        )

    def _generate_results(self, mad, median, new_values) -> list[dict]:
        """Generates results for the current batch of new values based on the model's predictions."""
        results = []
        if not self.is_fitted:
            # Still in Warmup
            for time_, v in new_values.items():
                self.logger.debug(f"Processing value: {v} (WARMUP)")
                results.append({"val": v, "is_anomaly": False, "anomaly_level": -1, "status": "WARMUP"})
        else:
            # Model is ready, predict the batch
            pred_start_time = time.time()
            X_batch = np.array(list(new_values.values())).reshape(-1, 1)
            scores = self.model.score_samples(X_batch)
            pred_end_time = time.time()
            total_pred_time = pred_end_time - pred_start_time
            time_format = "%Y-%m-%d %H:%M:%S.%f"
            on_each_time = total_pred_time / len(new_values) if new_values else 0

            for i, ((time_, v), score) in enumerate(zip(new_values.items(), scores)):
                try:
                    comp_time = float(time_) if isinstance(time_, (int, float)) else datetime.strptime(time_, time_format).timestamp()
                except (ValueError, TypeError):
                    self.logger.warning(f"\n[ERROR] Malformed timestamp: {time_!r}, using current time")
                    comp_time = pred_start_time

                total_process_time = (pred_start_time - comp_time) + i * on_each_time # Approximate the time taken for the entire process of this value.
                print(f"[PREDICTION] Value: {v}, Score: {score:.4f}, Processed in: {total_process_time:.4f}s")
                is_anomaly = score < self.score_threshold
                results.append({
                    "val": v,
                    "is_anomaly": is_anomaly,
                    "anomaly_score": float(score),
                    "anomaly_level": self.anomaly_level(mad, median, v),
                    "processed_in": total_process_time,
                    "status": "READY"
                })

        return results
    
    def anomaly_level(self, mad: int, median: int, check_value: int):
        """Dynamically identify anomaly levels for any distribution"""

        if mad == 0:
            return 0
        
        diff = np.abs(check_value - median)

        if diff > 4 * mad: return 3
        elif diff > 3 * mad: return 2
        elif diff > 2 * mad: return 1
        return 0

    def __str__(self):
        return self.name