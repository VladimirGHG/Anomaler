from fractions import Fraction
from functools import reduce
from math import gcd, lcm

from dataclasses import dataclass, field

from ..config.group_config import GroupConfig
from ..config.stream_config import StreamConfig
from ..data.group_data_storage import GroupDataStorage
from ..virtual_sensors.relationship.relationship_measure import Relator

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

    def handle_worker_batch(self, batch: dict) -> None:
        source_name = batch["source_name"]

        self.add_data(source_name, batch)
        print(f"RECEIVED BATCH FROM {source_name}")
        if self.data_storage.get_source_data("source4"):
            rel = Relator(self.config)
            rel.prepare(data_sources=["source1", "source2"], data_storage=self.data_storage)

        if self.is_window_ready():
            self.process_virtual_sensors()

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