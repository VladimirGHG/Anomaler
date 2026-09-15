from dataclasses import dataclass

from ..manager.group_runtime import GroupConfig

from .stream_config import StreamConfig

@dataclass(frozen=True)
class WorkerContext:
    group_id: str
    group_runtime: GroupConfig
    stream_config: StreamConfig