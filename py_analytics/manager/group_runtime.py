from fractions import Fraction
from functools import reduce
from math import gcd, lcm
from time import time

from dataclasses import dataclass, field

from ..config.group_config import GroupConfig
from ..config.stream_config import StreamConfig


@dataclass
class GroupRuntime:
    group_id: str
    config: GroupConfig

    stream_configs: dict[str, StreamConfig] = field(default_factory=dict)
    data_buffers: dict[str, list] = field(default_factory=dict)
    virtual_sensors: list = field(default_factory=list)

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
            self.data_buffers[source_name] = []

    def add_data(self, source_name: str, data) -> None:
        """Add data received from a worker to its group buffer."""

        if source_name not in self.stream_configs:
            raise ValueError(
                f"Source '{source_name}' is not registered "
                f"in group '{self.group_id}'."
            )

        self.data_buffers[source_name].append(data)

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
            if len(self.data_buffers[source]) < self.config.pca_n_timestamps:
                return False

        return True

    def process_virtual_sensors(self) -> None:
        """
        Process the currently available synchronized data using the group's virtual sensors.
        """
        pass

    @classmethod
    def _common_sampling_period(periods: list[float]) -> float:
        fractions = [Fraction(str(p)) for p in periods]

        denominator_lcm = reduce(lcm, (p.denominator for p in fractions))
        scaled = [p.numerator * (denominator_lcm // p.denominator) for p in fractions]

        common_numerator = reduce(lcm, scaled)

        return common_numerator / denominator_lcm