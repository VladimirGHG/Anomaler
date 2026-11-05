from abc import ABC
from bisect import bisect_left
from datetime import datetime
from math import ceil
from typing import Literal

import numpy as np

from ..stream_series import StreamSeries
from ...data.group_data_storage import GroupDataStorage

class RelationshipMeasure(ABC):
    """Abstract base class for relators that find relationships between data sources / sensors."""

    CorrelationMethod = Literal["pairwise", "multivariate"]

    def __init__(self, group_config):
        self.group_config = group_config
        self.stream_series: dict[str: StreamSeries] = {}

    def prepare(self, data_sources: list[str], data_storage: GroupDataStorage) -> dict[str, StreamSeries]:
        """Align sources to a fixed grid using the nearest reading within tolerance."""
        if not data_sources:
            return {}

        period = self.group_config.frequency
        if period is None or period <= 0:
            raise ValueError("A positive synchronization.frequency is required for time-grid alignment")
        tolerance = self.group_config.alignment_tolerance
        if tolerance is None:
            tolerance = period / 2
        if tolerance < 0 or tolerance > period / 2:
            raise ValueError("synchronization.alignment_tolerance must be between 0 and half the grid period")

        window_size = max(1, self.group_config.pca_n_timestamps)
        timed_points = {}
        for source in data_sources:
            points = [
                (self._to_epoch_seconds(point["timestamp"]), point["value"])
                for point in data_storage.get_source_data(source)
            ]
            points.sort(key=lambda item: item[0])
            timed_points[source] = points

        if any(not points for points in timed_points.values()):
            self.stream_series = {source: StreamSeries(source, []) for source in data_sources}
            return self.stream_series

        overlap_start = max(points[0][0] for points in timed_points.values())
        overlap_end = min(points[-1][0] for points in timed_points.values())
        first_tick = ceil(overlap_start / period)
        last_tick = int(overlap_end / period)
        aligned = {source: [] for source in data_sources}
        times_by_source = {
            source: [item[0] for item in points]
            for source, points in timed_points.items()
        }

        for tick in range(first_tick, last_tick + 1):
            grid_time = tick * period
            selected = {}
            for source, points in timed_points.items():
                times = times_by_source[source]
                index = bisect_left(times, grid_time)
                candidates = points[max(0, index - 1):min(len(points), index + 1)]
                nearest = min(candidates, key=lambda item: abs(item[0] - grid_time))
                if abs(nearest[0] - grid_time) > tolerance:
                    break
                selected[source] = nearest[1]
            if len(selected) == len(data_sources):
                grid_timestamp = datetime.fromtimestamp(grid_time).isoformat(timespec="milliseconds")
                for source in data_sources:
                    aligned[source].append({"timestamp": grid_timestamp, "value": selected[source]})

        self.stream_series = {
            source: StreamSeries(source, points[-window_size:])
            for source, points in aligned.items()
        }

        return self.stream_series

    @staticmethod
    def _to_epoch_seconds(timestamp) -> float:
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        if isinstance(timestamp, datetime):
            return timestamp.timestamp()
        return datetime.fromisoformat(timestamp).timestamp()

    def compute(self, data_sources: list[str], data_storage: GroupDataStorage, method: CorrelationMethod):
        """Find relationships between the given data sources.

        Args:
            data_sources (list): A list of data sources to analyze.
            data_batch (list): A list of data batches to analyze.
            method: how provided sources should be compared.
        Returns:
            dict: A dictionary containing the relationships found between the data sources.
        """
        raise NotImplementedError("Subclasses must implement this method.")

