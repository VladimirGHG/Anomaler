import os
import zmq
from .models import AnomalyModel
from sklearn.utils import shuffle
import sys
import json


class ZMQWorker:
    """Worker process that receives data batches via ZeroMQ, processes them with the given anomaly detection strategy, and reports results."""
    def __init__(self, port, strategy: AnomalyModel):
        self.port = port
        self.strategy = strategy
        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.PULL)
        self.receiver.connect(f"tcp://127.0.0.1:{self.port}")

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
                if all_new_values:
                    results = self.strategy.process_batch(all_new_values)
                    self.report(results)

    def report(self, results):
        if not results:
            return

        anomalies = [r for r in results if r.get("is_anomaly")]
        last_val = results[-1].get("val")
        status = results[-1].get("status")

        if status == "WARMUP":
            sys.stdout.write(f"\r[WARMUP] Processed {len(results)} points. Latest: {last_val}")
        elif anomalies:
            print(f"\n[!] ANOMALY DETECTED! Found {len(anomalies)} outliers in batch of {len(results)}.")
        else:
            sys.stdout.write(f"\r[OK] Batch of {len(results)} points synced. Latest: {last_val}")
        
        sys.stdout.flush()
