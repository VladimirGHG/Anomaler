from fractions import Fraction
from functools import reduce
from math import gcd, lcm

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
        print(f"[RELATIONSHIP] Received {batch["source_name"]}")

        self.data_storage.add_source_data(batch["source_name"], batch["datapoints"])

        required_sources = {
            "source1",
            "source2",
            "source4",
        }

        print(
            f"[RELATIONSHIP] Available sources: "
            f"{set(self.data_storage.data.keys())}"
        )

        if not all(
            source in self.data_storage.data
            for source in required_sources
        ):
            print("[RELATIONSHIP] Waiting for all sources")
            return

        print("[RELATIONSHIP] All required sources available")

        for source in required_sources:
            print(
                f"[RELATIONSHIP] {source}: "
                f"{len(self.data_storage.data[source])} points"
            )

        if not all(
            len(self.data_storage.data[source]) >= 120
            for source in required_sources
        ):
            print("[RELATIONSHIP] Not enough data yet")
            return

        print("[RELATIONSHIP] Calling correlation")

        result = rel.compute(
            data_sources=list(required_sources),
            data_storage=self.data_storage,
            method="pairwise",
        )

        print(f"[RELATIONSHIP] RESULT: {result}")

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