import numpy as np

class StreamSeries:
    def __init__(self, stream_id, batches):
        self.stream_id = stream_id
        self.datapoints = []
        for batch in batches:
            self.datapoints.append(batch)

        self.datapoints.sort(key=lambda dp: dp["timestamp"])

    @property
    def values(self) -> np.ndarray:
        return np.asarray([point["value"] for point in self.datapoints], dtype=float)

    @property
    def timestamps(self):
        return [point["timestamp"] for point in self.datapoints]
    
    def __str__(self):
        return f"{self.datapoints}"