from itertools import combinations

from scipy.stats import pearsonr
import numpy as np

from ..stream_series import StreamSeries
from ...data.group_data_storage import GroupDataStorage
from .relationship_measure import RelationshipMeasure

class PearsonCorrelation(RelationshipMeasure):
    """
    Pearson Correlation Coefficient (PCC) is a measure of the linear correlation between two variables.
    It ranges from -1 to 1, where:
        1 indicates a perfect positive linear relationship,
        -1 indicates a perfect negative linear relationship,
        0 indicates no linear relationship.
    """
    def __init__(self, group_config):
        super().__init__(group_config=group_config)

    def compute(self, data_sources: list[str], data_storage: GroupDataStorage, method) -> float:
        """
        Compute the Spearman rank correlation coefficient between two variables.

        Parameters:
            data_sources (list): A list of data sources to analyze.
            data_batch (list): A list of data batches to analyze.
            method: how provided sources should be compared.

        Returns:
            float: Pearson correlation coefficient.
        """

        prepared_data: dict[str, StreamSeries] = self.prepare(data_sources, data_storage)
        for name, series in prepared_data.items():
            
            print(
                name,
                len(series.values),
                series.timestamps[0],
                series.timestamps[-1],
            )

        if method == "pairwise":
            return self._compute_pairwise(prepared_data)

        elif method == "multivariate":
            return self._compute_multivariate(prepared_data)

        raise ValueError(f"Unknown correlation method: {method}")

    def _compute_pairwise(self, data: dict[str, StreamSeries]):
        results = {}
        
        for (source_a, series_a), (source_b, series_b) in combinations(data.items(), 2):
            correlation, p_value = pearsonr(series_a.values, series_b.values)

            results[(source_a, source_b)] = {"correlation": correlation, "p_value": p_value}

        return results

    def _compute_multivariate(self, data: dict[str, StreamSeries]):        
        X = self._build_matrix(data)
        correlation_matrix, p_values = pearsonr(X)

        return correlation_matrix, p_values

    def _build_matrix(self, data: dict[str, StreamSeries]) -> np.array:
            rows = []
    
            for series in data.values():
                rows.append(series.values)
    
            return np.array(rows).T