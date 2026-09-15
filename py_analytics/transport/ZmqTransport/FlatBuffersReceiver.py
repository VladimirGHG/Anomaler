from datetime import datetime

class FlatBuffersReceiver:
    def __init__(self, zmq_socket):
        self.zmq_socket = zmq_socket

    def receive(self):
        message = self.zmq_socket.recv()
        return self.deserialize(message)

    def deserialize(self, raw: bytes):
        """Decode a FlatBuffers TelemetryBatch from raw bytes by dynamically finding the vector field."""
        try:
            from ....serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb
            batch = tb.TelemetryBatch.GetRootAs(raw, 0)
            
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
                    "timestamp": datetime.fromtimestamp(msg.Timestamp()).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "value": msg.Value()
                })
            
            if datapoints:
                return {"datapoints": datapoints}
        except Exception as e:
            if e.__class__.__name__ == "ImportError":
                print(f"[DEBUG CRASH] Flatbuffer import failed: {e}. \
                        Ensure the generated code after compiling the .fbs \
                        is available from Anomaler/serialization/generated/python/Anomaler/Serialization.")
                
            print(f"[DEBUG CRASH] Flatbuffer unpack failed: {e}")
            pass