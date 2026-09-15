from dataclasses import dataclass

@dataclass
class GroupConfig:
    frequency : float
    targets: list[str] | None
    connections: list[str]
    pca_n_timestamps: int
    communication_host: str
    communication_port_range: list[int]

    @classmethod
    def from_dict(cls, data: dict) -> "GroupConfig":
        synchronization = data.get("synchronization", {})
        virtual_sensor = data.get("virtual_sensor", {})
        communication = data.get("communication", {})
        return cls(frequency=synchronization.get("frequency", 0.5),
            targets=virtual_sensor.get("target"),
            connections=virtual_sensor.get("connections", []),
            pca_n_timestamps=virtual_sensor.get("pca_n_timestamps", 10),
            communication_host=communication.get("host", "127.0.0.1"),
            communication_port_range=communication.get("port_range", [5560, 5565]))