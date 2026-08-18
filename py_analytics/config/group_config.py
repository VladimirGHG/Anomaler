from dataclasses import dataclass

@dataclass
class GroupConfig:
    frequency : float
    targets: list[str] | None
    connections: list[str]
    pca_n_timestamps: int

    @classmethod
    def from_dict(cls, data: dict) -> "GroupConfig":
        synchronization = data.get("synchronization", {})
        virtual_sensor = data.get("virtual_sensor", {})

        return cls(frequency=synchronization.get("frequency", 0.5),
            targets=virtual_sensor.get("target"),
            connections=virtual_sensor.get("connections", []),
            pca_n_timestamps=virtual_sensor.get("pca_n_timestamps", 10))