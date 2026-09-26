class StreamSeries:
    def __init__(self, stream_id, batches):
        self.stream_id = stream_id
        self.datapoints = []

        for batch in batches:
            self.datapoints.extend(batch["datapoints"])

        self.datapoints.sort(key=lambda dp: dp["timestamp"])

    def __str__(self):
        return f"{self.datapoints}"