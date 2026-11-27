import os
import logging
import time
import json
from datetime import datetime

import zmq
import numpy as np

from ..config.worker_context import WorkerContext
from ..models.factory import create_strategy
from ..model_logger import ModelLogger
from ..sensor_logger import SensorLogger
from ..transport.FlatBuffers.FlatBuffersSender import FlatBuffersSender
from .buffer_scrap_methods.greedy_read import greedy_read

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTER_DIR = os.path.dirname(BASE_DIR)
MODELS_DIR = os.path.join(OUTER_DIR, "models_saved")

class ZMQWorker:
    """Worker process that receives data batches via ZeroMQ, processes them with the given anomaly detection strategy, and reports results."""
    def __init__(self, worker_config: WorkerContext, group_runtime_port: int, load_path: str = "", save_every: int = 15, max_snapshots: int = 10, log=True):
        self._group_config = worker_config.group_runtime.config
        self._stream_config = worker_config.stream_config

        self.communication_host = self._group_config.communication_host
        self.pca_n_timestamps = self._group_config.pca_n_timestamps
        self._n_timestamps = 0
        self.port = worker_config.stream_config.port
        self.serialization = worker_config.stream_config.serialization

        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.connect(f"tcp://127.0.0.1:{self.port}")
        self.batch_id = 0

        self.all_new_values = []

        group_runtime_sender = context.socket(zmq.PUSH)
        group_runtime_sender.connect(f"tcp://{self.communication_host}:{group_runtime_port}")

        self.flatBuffersSender = None
        if self._stream_config.source_name in self._group_config.connections:
            self.flatBuffersSender = FlatBuffersSender(group_runtime_sender)

        self.median = 0
        self.mad = 1 # MAD / Median Absolute Deviation
        self.tp = 0 # True Positives
        self.fn = 0 # False Negatives
        
        self.load_path = load_path
        self.save_every = save_every
        self.max_snapshots = max_snapshots

        folder = "./py_analytics/models"
        self.strategy = create_strategy(worker_config.stream_config.strategy, folder)
        self.source_logger = SensorLogger(
            worker_config.stream_config.source_name,
            self.strategy.name if self.strategy is not None else None,
        )
        if self.strategy is not None:
            sensor_name = worker_config.stream_config.source_name
            self.strategy.logger = ModelLogger(
                f"{sensor_name}_{self.strategy.name}_v{self.strategy.version}_{self.strategy.config_hash[:8]}"
            )

        if self.serialization.lower() not in ["json", "flatbuffers"]:
            raise ValueError(f"Unsupported serialization protocol: {self.serialization}. Supported: 'json', 'flatbuffers'")
        elif self.serialization.lower() == "flatbuffers":
            self.func = self._decode_flatbuffer
        else:       
            self.func = self._decode_json

    def get_median_mad(self, data_points: list[int]):
        arr = np.asarray(data_points, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return
        self.median = np.median(arr)
        self.mad = np.median(np.abs(arr - self.median)) * 1.4826 # A scaling factor to make MAD comparable to STD for normal data distributions
    
    def start(self):

        if self.load_path:
            if self.strategy is None:
                raise ValueError("Cannot load a model when no strategy is configured")
            loaded_strategy = self.strategy.load_model(self.load_path)
            if loaded_strategy.name != self.strategy.name:
                raise ValueError(f"Loaded strategy {loaded_strategy.name!r} does not match configured strategy {self.strategy.name!r}")
            self.strategy = loaded_strategy
            sensor_name = self._stream_config.source_name
            self.strategy.logger = ModelLogger(
                f"{sensor_name}_{self.strategy.name}_v{self.strategy.version}_{self.strategy.config_hash[:8]}"
            )

        while True:
            if os.getppid() == 1: break
            # Check if there is data
            if self.receiver.poll(1000):
                batch_of_packets, status = greedy_read(self.receiver, self.func)

                if status == 0:
                    new_values = []
                    batch_ids = []
                    for received_packet in batch_of_packets:
                        received_id = received_packet.get("ID", self.batch_id)
                        if received_id != self.batch_id:
                            message = f"Batch sequence gap: received {received_id}, expected {self.batch_id}"
                            if self.strategy is not None:
                                self.strategy.logger.warning(message)
                            else:
                                logging.getLogger(__name__).warning(message)
                            continue
                        self.batch_id += 1
                        for datapoint in received_packet.get("datapoints", []):
                            timestamp = datapoint["timestamp"]
                            value = datapoint["value"]
                            new_values.append((timestamp, value))
                            batch_ids.append(received_id)
                            self.source_logger.log_datapoint(received_id, timestamp, value)

                    if not new_values:
                        continue

                    self.all_new_values.extend(
                        {"timestamp": timestamp, "value": value}
                        for timestamp, value in new_values
                    )

                    if self.flatBuffersSender and len(self.all_new_values) >= self.pca_n_timestamps:
                        self.flatBuffersSender.send(self._stream_config.source_name, self.all_new_values)
                        self.all_new_values = []

                    if self.strategy == None:
                        continue
                    else:
                        if self.strategy.name == "SKlearnIsolatedForest" and self.strategy.data_buffer:
                            self.get_median_mad(self.strategy.data_buffer)
                        
                        results = []
                            
                        # If there are newly received data points process them and report the results.
                        if new_values:
                            results = self.strategy.process_batch(self.mad, self.median, new_values)
                            self.report(results, batch_ids)

                        # If the current model with which the ZMQWorker works does not have a set last_save_time of the model, set it.
                        # Elif last snapshot was made more than SELF.SAVE_EVERY seconds ago, save it.
                        if self.strategy.last_save_time is None:
                            self.strategy.last_save_time = time.time()
                        elif time.time() - self.strategy.last_save_time > self.save_every: # Save every X seconds 
                            if self.strategy.model_snapshot >= self.max_snapshots: # Keep only last Y snapshots
                                self.strategy.model_snapshot = 0
                                self.strategy.logger.info(
                                    f"Snapshot limit ({self.max_snapshots}) reached; rotating snapshots"
                                )

                            os.makedirs(MODELS_DIR, exist_ok=True) # Double check it exists
                            self.strategy.save_model(os.path.join(MODELS_DIR, self.strategy.name))
                            self.strategy.last_save_time = time.time()
                            self.strategy.model_snapshot += 1

                        # if results:
                        #     self.calculate_precision(results, batch_of_packets, results[-1].get("status"))

    def report(self, results: list[dict], batch_ids: list[int]):
        """Write anomaly events and concise model summaries to their logs."""
        if not results:
            return

        anomalies = [r for r in results if r.get("is_anomaly")]
        status = results[-1].get("status")
        if self.strategy.name == "SKlearnIsolatedForest": level = results[-1].get("anomaly_level", -1)
        elif self.strategy.name == "RiverHalfSpaceTrees": level = results[-1].get("score", -1)
        else: level = -1
        
        if status == "WARMUP":
            self.strategy.logger.info(f"Warmup: processed {len(results)} points")
        elif anomalies:
            for index, result in enumerate(results):
                if not result.get("is_anomaly"):
                    continue
                timestamp = result.get("timestamp")
                score = result.get("anomaly_score", result.get("score"))
                self.source_logger.log_anomaly(
                    batch_ids[index] if index < len(batch_ids) else "unknown",
                    timestamp,
                    result.get("val"),
                    score,
                )
            self.strategy.logger.warning(
                f"Anomalies detected: {len(anomalies)}/{len(results)} points; level={level}"
            )
        
    def calculate_precision(self, results, data_points, status):
        """Calculates precision based on the results and any available ground truth."""
        if status == "WARMUP":
            return
        for r, dp in zip(results, data_points[0].get("datapoints")):
            if r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                self.strategy.logger.info(f"True positive: detected {r['val']} as anomaly")
                self.tp += 1
            elif not r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                self.strategy.logger.warning(f"False negative: missed anomaly {r['val']}")
                self.fn += 1
        precision = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0
        self.strategy.logger.info(f"Recall: {precision:.2f} (TP: {self.tp}, FN: {self.fn})")

    def _decode_json(self, raw: bytes):
        s = raw.decode('utf-8')
        packet = json.loads(s)

        # In case of leading zeroes being stripped.
        datapoints = packet.get("datapoints", [])
        for datapoint in datapoints:
            timestamp = datapoint.get("timestamp", [])
            base, frac = timestamp.rsplit('.', 1)
            frac = frac.zfill(3)[:3]
            datapoint["timestamp"] = datetime.strptime(f"{base}.{frac}", "%Y-%m-%d %H:%M:%S.%f")
        return packet
    
    def _decode_flatbuffer(self, raw: bytes):
        """Decode a FlatBuffers TelemetryBatch from raw bytes by dynamically finding the vector field."""
        try:
            from ..serialization.generated.python.Anomaler.Serialization import TelemetryBatch as tb
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
        except Exception:
            logging.getLogger(__name__).exception("Could not decode FlatBuffers payload")

        return None
