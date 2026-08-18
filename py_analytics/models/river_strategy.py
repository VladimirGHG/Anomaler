from river import anomaly

from py_analytics.models.base import Strategy, RiverDriftPolicy

class RiverStrategy(Strategy):
    """Implements a streaming anomaly detection strategy using River's online training HalfSpaceTrees."""
    def __init__(self, window_size: int = 250, drift_policy: RiverDriftPolicy = RiverDriftPolicy.RESET):
        super().__init__("RiverHalfSpaceTrees")
        self.window_size = window_size
        self.drift_policy = drift_policy
        self._init_model()

    def _init_model(self):
        self.model = anomaly.HalfSpaceTrees(window_size=self.window_size, n_trees=25, limits={"v": (-100, 100)})

    @property
    def is_fitted(self):
        # The model is "fitted" if it has processed at least one full window
        return self.count >= self.window_size
    
    def process_batch(self, mad, median, new_values) -> list[dict]:

        results = []
        for time_, v in new_values.items():
            feature_dict = {"v": v}
            self.drift_detector.update(v)

            if self.drift_detector.drift_detected:
                if self.drift_policy == RiverDriftPolicy.RESET:

                    # print(f"\n[DRIFT] Concept drift detected at value: {v}. Retraining model...")
                    self.logger.info(f"\n[DRIFT] Concept drift detected at value: {v}. Resetting model...") 

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