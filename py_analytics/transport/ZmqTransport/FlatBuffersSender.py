import flatbuffers
from datetime import datetime

from py_analytics.serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb, TelemetryMessage as tm


class FlatBuffersSender:
    def __init__(self, zmq_socket):
        self.zmq_socket = zmq_socket
        
    def send(self, source_name: str, datapoints: list[dict]):
        """Serialize a TelemetryBatch to FlatBuffers and send it over the ZMQ socket."""
        telemetry_batch = self._create_batch(source_name, datapoints)
        serialized_bytes = self.serialize(telemetry_batch)

        self.zmq_socket.send(serialized_bytes)
        print(f"--- [INFO] Sent {len(datapoints)} datapoints over ZMQ socket.")

    def _create_batch(self, source_name: str, datapoints: list[dict]) -> tb.TelemetryBatchT:
        batch = tb.TelemetryBatchT()
        batch.sourceName = source_name

        batch.datapoints = [
            tm.TelemetryMessageT(
                timestamp=self._datetime_to_timestamp(point["timestamp"]),
                value=point["value"],
            ) for point in datapoints
        ]

        return batch

    @staticmethod
    def _datetime_to_timestamp(timestamp: datetime) -> int:
        return int(timestamp.timestamp() * 1000)

    def serialize(self, telemetry_batch: tb.TelemetryBatchT) -> bytes:
        builder = flatbuffers.Builder(1024)

        offset = telemetry_batch.Pack(builder)
        builder.Finish(offset)

        return builder.Output()