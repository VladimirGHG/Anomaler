import flatbuffers
from datetime import datetime

from py_analytics.serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb

class FlatBuffersSender:
    def __init__(self, zmq_socket):
        self.zmq_socket = zmq_socket
        
    def send(self, telemetry_batch: tb.TelemetryBatchT):
        """Serialize a TelemetryBatch to FlatBuffers and send it over the ZMQ socket."""
        serialized_bytes = self.serialize(telemetry_batch)

        self.zmq_socket.send(serialized_bytes)

    def serialize(self, telemetry_batch: tb.TelemetryBatchT):
        """Serialize a TelemetryBatch to FlatBuffers and return the raw bytes."""
        builder = flatbuffers.Builder(1024)

        for datapoint in telemetry_batch.datapoints:
            datapoint.timestamp = self._datetime_to_timestamp(datapoint.timestamp)

        telemetry_batch_offset = telemetry_batch.Pack(builder)
        builder.Finish(telemetry_batch_offset)

        return builder.Output()

    @staticmethod
    def _datetime_to_timestamp(timestamp: datetime | int) -> int:
        if isinstance(timestamp, datetime):
            return int(timestamp.timestamp() * 1000)

        if isinstance(timestamp, int):
            return timestamp

        raise TypeError(
            f"Unsupported timestamp type: {type(timestamp).__name__}"
        )