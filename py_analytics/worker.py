import os
import sys
import time
import json
from datetime import datetime

import zmq
import numpy as np

from .models.base import AnomalyModel


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models_saved")

class ZMQWorker:
    """Worker process that receives data batches via ZeroMQ, processes them with the given anomaly detection strategy, and reports results."""
    def __init__(self, port, strategy: AnomalyModel | None, serialization: str = "json", load_path: str = "", save_every: int = 15, max_snapshots: int = 10, log=True):
        self.port = port
        self.strategy = strategy

        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.connect(f"tcp://127.0.0.1:{self.port}")
        self.batch_id = 0

        self.median = 0
        self.mad = 1 # MAD / Median Absolute Deviation
        self.tp = 0 # True Positives
        self.fn = 0 # False Negatives
        
        self.load_path = load_path
        self.save_every = save_every
        self.max_snapshots = max_snapshots

        if serialization.lower() not in ["json", "flatbuffers"]:
            raise ValueError(f"Unsupported serialization protocol: {serialization}. Supported: 'json', 'flatbuffers'")
        elif serialization.lower() == "flatbuffers":
            self.func = self._decode_flatbuffer
        else:       
            self.func = self._decode_json

    def get_median_mad(self, data_points: list[int]):
        arr = np.asanyarray(data_points) # Convert to numpy array for faster calculations and less memory usasge
        self.median = np.median(arr)
        self.mad = np.median(np.abs(arr - self.median)) * 1.4826 # A scaling factor to make MAD comparable to STD for normal data distributions
    
    def start(self):
        time_lst = []
        while True:
            if os.getppid() == 1: break
            # Check if there is data
            if self.receiver.poll(1000):
                batch_of_packets = []
                
                # Greedy Read: Grab everything currently in the ZeroMQ buffer
                while True:
                    try:
                        raw = self.receiver.recv(flags=zmq.NOBLOCK)

                        packet = self.func(raw)
                        if packet:
                            print(packet)
                            batch_of_packets.append(packet)
                    except zmq.Again:
                        break # Queue is empty
                
                if self.batch_id == packet["ID"]:
                    print(f"--- [INFO] Batch with ID {packet['ID']} received.")
                    self.batch_id += 1
                else:
                    print(f"--- [INFO] Batch with ID {packet['ID']} received. Expected ID: {self.batch_id}.")
                    continue
                

                all_new_values = {}
                for packet in batch_of_packets:
                    all_new_values.update({p["timestamp"]: p["value"] for p in packet["datapoints"]})

                if self.strategy == None:
                    print(f"--- [INFO] No strategy provided. Sending the batch {packet['ID']} to the virtual sensor.")
                    continue
                else:
                    if self.strategy.name == "SKlearnIsolatedForest":
                        if all_new_values:
                            # Calculate the current median and MAD
                            self.get_median_mad(self.strategy.data_buffer)
                    
                    results = []

                    # If a model loading path was provided when the worker was created, than load the model.
                    if self.load_path:
                        self.strategy.model = self.strategy.load_model(self.load_path)
                        
                    # If there are newly received data points process them and report the results.
                    if all_new_values:
                        results = self.strategy.process_batch(self.mad, self.median, all_new_values)
                        self.report(results)

                    # If the current model with which the ZMQWorker works does not have a set last_save_time of the model, set it.
                    # Elif last snapshot was made more than SELF.SAVE_EVERY seconds ago, save it.
                    if self.strategy.last_save_time is None:
                        self.strategy.last_save_time = time.time()
                    elif time.time() - self.strategy.last_save_time > self.save_every: # Save every X seconds 
                        if self.strategy.model_snapshot >= self.max_snapshots: # Keep only last Y snapshots
                            self.strategy.model_snapshot = 0
                            print(f"--- [DISK] Reached max snapshots. Overwriting from {self.strategy.__str__()}_0.pkl")

                        os.makedirs(MODELS_DIR, exist_ok=True) # Double check it exists
                        self.strategy.save_model(os.path.join(MODELS_DIR, self.strategy.name))
                        self.strategy.last_save_time = time.time()
                        self.strategy.model_snapshot += 1

                    # if results:
                    #     self.calculate_precision(results, batch_of_packets, results[-1].get("status"))

                context = zmq.Context()


    def report(self, results: list[dict]):
        """Prints the results of the anomaly detection in a readable format."""
        if not results:
            return

        anomalies = [r for r in results if r.get("is_anomaly")]
        last_val = results[-1].get("val")
        status = results[-1].get("status")
        if self.strategy.name == "SKlearnIsolatedForest": level = results[-1].get("anomaly_level", -1)
        elif self.strategy.name == "RiverHalfSpaceTrees": level = results[-1].get("score", -1)
        else: level = -1
        
        if status == "WARMUP":
            sys.stdout.write(f"\r--- [WARMUP] Processed {len(results)} points. Latest: {last_val}")
        elif anomalies:
            self.strategy.logger.warning(f"Found {len(anomalies)} anomalies in batch of {len(results)}. Anomaly Level: {level}")
            print(f"\n--- [ANOMALY DETECTED] Found {len(anomalies)} outliers in batch of {len(results)}. Anomaly Level: {level}\\n")
        else:
            self.strategy.logger.info(f"Processed batch of {len(results)} points. Latest: {last_val}")
            sys.stdout.write(f"\r--- [OK] Batch of {len(results)} points synced. Latest: {last_val}")
        # self.strategy.logger.info(f"Processed batch of {results}")
        sys.stdout.flush()

    def calculate_precision(self, results, data_points, status):
        """Calculates precision based on the results and any available ground truth."""
        if status == "WARMUP":
            return
        for r, dp in zip(results, data_points[0].get("datapoints")):
            if r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                print(f"True Positive: Detected {r['val']} as anomaly, which is correct.")
                self.tp += 1
            elif not r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                print(f"False Negative: Missed {r['val']} which is an anomaly.")
                self.fn += 1
        precision = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0
        print(f"Precision: {precision:.2f} (TP: {self.tp}, `FN: {self.fn})")

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
            from .anomaler.Serialization import TelemetryBatch as tb
            batch = tb.TelemetryBatch.GetRootAs(raw, 0)
            
            # FlatBuffers names methods cleanly (e.g., DatapointsLength / Datapoints)
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
            # Uncomment the next line temporarily if you need to debug schema structural anomalies
            print(f"[DEBUG CRASH] Flatbuffer unpack failed: {e}")
            pass

        return None