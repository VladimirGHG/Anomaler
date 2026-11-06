from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FlatBuffersReceiver:
    def __init__(self, zmq_socket):
        self.zmq_socket = zmq_socket

    def receive(self):
        message = self.zmq_socket.recv()
        return self.deserialize(message)

    def deserialize(self, raw: bytes):
        """Decode a FlatBuffers TelemetryBatch from raw bytes by dynamically finding the vector field."""
        try:
            from py_analytics.serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb
            batch = tb.TelemetryBatch.GetRootAs(raw, 0)

            source_name = batch.SourceName()
            if isinstance(source_name, bytes):
                source_name = source_name.decode("utf-8")

            methods = dir(batch)
            vector_base = None
            for kw in ["Messages", "Datapoints", "Samples", "Frames", "Data"]:
                if f"{kw}Length" in methods:
                    vector_base = kw
                    break
            
            if not vector_base:
                # Fallback to looking for anything ending in Length to prevent failure
                length_methods = [m for m in methods if m.endswith("Length")]
                if length_methods:
                    vector_base = length_methods[0].replace("Length", "")
            
            if not vector_base:
                return None
            
            # Extract bound accessors dynamically based on your compiled .fbs file
            length_func = getattr(batch, f"{vector_base}Length")
            vector_func = getattr(batch, vector_base)
            
            datapoints = []
            num_elements = length_func()
            
            # Extract raw floats from binary memory sequentially
            for i in range(num_elements):
                msg = vector_func(i)
                datapoints.append({
                    "timestamp": datetime.fromtimestamp(msg.Timestamp() / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "value": msg.Value()
                })
            
            if datapoints:
                return {"source_name": source_name, "datapoints": datapoints}
            
        except Exception:
            logger.exception("Could not decode FlatBuffers payload")
