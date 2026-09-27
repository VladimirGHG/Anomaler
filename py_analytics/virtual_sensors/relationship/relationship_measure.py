from abc import ABC
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

        for data_source in data_sources:
            self.stream_series[data_source] = StreamSeries(data_source, data_storage.data[data_source])

        return self.stream_series
    
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
        