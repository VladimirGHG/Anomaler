import flatbuffers

from ....serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb

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
        telemetry_batch_offset = telemetry_batch.Pack(builder)
        builder.Finish(telemetry_batch_offset)

        return builder.Output()