import os
import zmq
from .models import AnomalyModel
from sklearn.utils import shuffle
import sys
import time
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

class ZMQWorker:
    """Worker process that receives data batches via ZeroMQ, processes them with the given anomaly detection strategy, and reports results."""
    def __init__(self, port, strategy: AnomalyModel):
        self.port = port
        self.strategy = strategy
        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.connect(f"tcp://127.0.0.1:{self.port}")
        self.tp = 0 # True Positives
        self.fn = 0 # False Negatives

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

                # Process everything in one go
                results = []
                if all_new_values:
                    results = self.strategy.process_batch(all_new_values)
                    # self.report(results)

                if self.strategy.last_save_time is None:
                    self.strategy.last_save_time = time.time()
                elif time.time() - self.strategy.last_save_time > 20: # Save every 5 minutes (will not be hardcoded in future)
                    if self.strategy.model_snapshot >= 5: # Keep only last 5 snapshots (will not be hardcoded in future)
                        self.strategy.model_snapshot = 0
                        print("[DISK] Reached max snapshots. Overwriting from model_0.pkl")

                    os.makedirs(MODELS_DIR, exist_ok=True) # Double check it exists
                    self.strategy.save_model(os.path.join(MODELS_DIR, f"model_{self.strategy.model_snapshot}.pkl"))
                    self.strategy.last_save_time = time.time()
                    self.strategy.model_snapshot += 1

                # if results:
                #     self.calculate_precision(results, batch_of_packets, results[-1].get("status"))

    def report(self, results):
        if not results:
            return

        anomalies = [r for r in results if r.get("is_anomaly")]
        last_val = results[-1].get("val")
        status = results[-1].get("status")
        levels = results[-1].get("anomaly_level", -1)
        
        if status == "WARMUP":
            sys.stdout.write(f"\r[WARMUP] Processed {len(results)} points. Latest: {last_val}")
        elif anomalies:
            print(f"\n[!] ANOMALY DETECTED! Found {len(anomalies)} outliers in batch of {len(results)}. Anomaly Level: {levels}\\n")
        else:
            sys.stdout.write(f"\r[OK] Batch of {len(results)} points synced. Latest: {last_val}")
        
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

    def save_model(self, path: str):
        self.strategy.save_model(path)