import os
import zmq
from .models import AnomalyModel
from sklearn.utils import shuffle
import numpy as np
import joblib
import sys
import time
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

class ZMQWorker:
    """Worker process that receives data batches via ZeroMQ, processes them with the given anomaly detection strategy, and reports results."""
    def __init__(self, port, strategy: AnomalyModel, load_path: str = "", save_every: int = 15, max_snapshots: int = 10):
        self.port = port
        self.strategy = strategy
        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.connect(f"tcp://127.0.0.1:{self.port}")
        self.median = 0
        self.mad = 1 # MAD / Median Absolute Deviation
        self.tp = 0 # True Positives
        self.fn = 0 # False Negatives
        self.load_path = load_path
        self.save_every = save_every
        self.max_snapshots = max_snapshots

    def get_median_mad(self, data_points: list[int]):
        arr = np.asanyarray(data_points) # Convert to numpy array for faster calculations and less memory usasge
        self.median = np.median(arr)
        self.mad = np.median(np.abs(arr - self.median)) * 1.4826 # A scaling factor to make MAD comparable to STD for normal data distributions
    
    def start(self):
        while True:
            if os.getppid() == 1: break

            # Check if there is data
            if self.receiver.poll(1000):
                batch_of_packets = []
                
                # Greedy Read: Grab everything currently in the ZeroMQ buffer
                while True:
                    try:
                        msg = self.receiver.recv_string(flags=zmq.NOBLOCK)
                        batch_of_packets.append(json.loads(msg))
                    except zmq.Again:
                        break # Queue is empty
                
                # Flatten all data points from all packets received
                all_new_values = []
                for packet in batch_of_packets:
                    all_new_values.extend([p["value"] for p in packet["datapoints"]])

                if self.strategy.name == "SKlearnIsolatedForest":
                    if all_new_values:
                        # Calculate the current median and MAD
                        self.get_median_mad(self.strategy.data_buffer)
                
                # Process everything in one go
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
            print(f"\n--- [ANOMALY DETECTED] Found {len(anomalies)} outliers in batch of {len(results)}. Anomaly Level: {level}\\n")
        else:
            sys.stdout.write(f"\r--- [OK] Batch of {len(results)} points synced. Latest: {last_val}")
        
        sys.stdout.flush()

    def calculate_precision(self, results, data_points, status):
        """Calculates precision based on the results and any available ground truth."""
        if status == "WARMUP":
            return
        for r, dp in zip(results, data_points[0].get("datapoints")):
            # print(r, dp)
            if r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                print(f"True Positive: Detected {r['val']} as anomaly, which is correct.")
                self.tp += 1
            elif not r.get("is_anomaly") and dp.get("shouldbeAnomaly"):
                print(f"False Negative: Missed {r['val']} which is an anomaly.")
                self.fn += 1
        precision = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0
        print(f"Precision: {precision:.2f} (TP: {self.tp}, `FN: {self.fn})")