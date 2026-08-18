from dataclasses import dataclass

from .group_config import GroupConfig

@dataclass(frozen=True)
class WorkerContext:
    group_id: str
    group_config: GroupConfig