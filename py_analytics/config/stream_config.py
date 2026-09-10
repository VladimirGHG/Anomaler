from dataclasses import dataclass

@dataclass
class StreamConfig:
    port: int
    strategy: str | None
    serialization: str
    source_name: int
    frequency: float

    @classmethod
    def from_dict(cls, data: dict) -> "StreamConfig":

        return cls(port=data.get("port"),
            strategy=data.get("ml_model"),
            serialization=data.get("serialization", "json"),
            source_name=data.get("source_name"),
            frequency = data.get("frequency"))