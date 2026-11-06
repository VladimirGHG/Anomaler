from fractions import Fraction
from functools import reduce
import logging
from math import gcd, lcm
import os
import re

from dataclasses import dataclass, field

from ..config.group_config import GroupConfig
from ..config.stream_config import StreamConfig
from ..data.group_data_storage import GroupDataStorage
from ..virtual_sensors.relationship.spearman_correlation import SpearmanCorrelation
from ..virtual_sensors.relationship.pearson_correlation import PearsonCorrelation

@dataclass
class GroupRuntime:
    group_id: str
    config: GroupConfig

    stream_configs: dict[str, StreamConfig] = field(default_factory=dict)
    data_storage: GroupDataStorage = field(default_factory=GroupDataStorage)
    virtual_sensors: list = field(default_factory=list)

    def _correlation_logger(self):
        safe_group_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(self.group_id)).strip("._") or "group"
        logger = logging.getLogger(f"py_analytics.correlation.{safe_group_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            correlation_dir = os.path.join("logs", "analysis", "correlation")
            os.makedirs(correlation_dir, exist_ok=True)
            handler = logging.FileHandler(os.path.join(correlation_dir, f"correlation_{safe_group_id}.log"))
            handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            logger.addHandler(handler)
        return logger

    @property
    def periods(self) -> list[float]:
        return [config.frequency for config in self.stream_configs.values()]

    @property
    def common_sampling_period(self) -> float:
        return self._common_sampling_period(self.periods)

    def register_worker(self, contexts: list[StreamConfig] | StreamConfig) -> None:
        """Register a worker belonging to this group, by passing its stream config."""
        if not isinstance(contexts, list):
            contexts = [contexts]

        for context in contexts:
            source_name = context.source_name

            if source_name in self.stream_configs:
                raise ValueError(
                    f"Worker for source '{source_name}' "
                    f"is already registered in group '{self.group_id}'."
                )

            self.stream_configs[source_name] = context

    def handle_worker_batch(self, batch):
        rel = PearsonCorrelation(self.config)
        self.data_storage.add_source_data(batch["source_name"], batch["datapoints"])

        required_sources = list(self.config.connections or [])
        if len(required_sources) < 2:
            return

        window_size = max(1, self.config.pca_n_timestamps)
        # Keep enough history for modest arrival skew, but cap memory usage.
        max_points = window_size * 4
        source_points = self.data_storage.data[batch["source_name"]]
        if len(source_points) > max_points:
            self.data_storage.data[batch["source_name"]] = source_points[-max_points:]

        if not all(
            source in self.data_storage.data
            for source in required_sources
        ):
            return

        prepared = rel.prepare(required_sources, self.data_storage)
        aligned_count = min((len(series) for series in prepared.values()), default=0)
        if aligned_count < window_size:
            return

        result = rel.compute(
            data_sources=list(required_sources),
            data_storage=self.data_storage,
            method="pairwise",
            prepared_data=prepared,
        )

        logger = self._correlation_logger()
        for (source_a, source_b), metrics in result.items():
            logger.info(
                "group=%s sources=%s,%s aligned_points=%d pearson_r=%.6f p_value=%.6g",
                self.group_id,
                source_a,
                source_b,
                aligned_count,
                metrics["correlation"],
                metrics["p_value"],
            )

        return result

    def add_data(self, source_name: str, data) -> None:
        """Add data received from a worker to its group buffer."""

        if source_name not in self.stream_configs:
            raise ValueError(
                f"Source '{source_name}' is not registered "
                f"in group '{self.group_id}'."
            )

        self.data_storage.add_source_data(source_name, data)

    def is_window_ready(self) -> bool:
        """
        Determine whether enough data is available to process a virtual-sensor window.
        """
        required_sources = [
            context.source_name for context in self.stream_configs.values()
            if context.source_name in self.config.connections
        ]

        if not required_sources:
            return False

        for source in required_sources:
            if len(self.data_storage.get_source_data(source)) < self.config.pca_n_timestamps:
                return False

        return True

    def process_virtual_sensors(self) -> None:
        """
        Process the currently available synchronized data using the group's virtual sensors.
        """
        pass

    @staticmethod
    def _common_sampling_period(periods: list[float]) -> float:
        fractions = [Fraction(str(p)) for p in periods]

        denominator_lcm = reduce(lcm, (p.denominator for p in fractions))
        scaled = [p.numerator * (denominator_lcm // p.denominator) for p in fractions]

        common_numerator = reduce(lcm, scaled)

        return common_numerator / denominator_lcm
