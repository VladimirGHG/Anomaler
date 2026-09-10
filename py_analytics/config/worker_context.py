from dataclasses import dataclass

from ..manager.group_runtime import GroupRuntime

from .stream_config import StreamConfig

@dataclass(frozen=True)
class WorkerContext:
    group_id: str
    group_runtime: GroupRuntime
    stream_config: StreamConfig