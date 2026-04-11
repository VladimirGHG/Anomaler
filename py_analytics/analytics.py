import sys
import os
import multiprocessing
import signal
import zmq
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.utils import shuffle  


def run_model_worker(port, model_type="IsolationForest"):
    """
    This is the spawned 'Worker'. 
    Every time a new C++ stream starts, a new instance of this runs.
    """
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    # Use bind so the worker is the stable endpoint
    receiver.bind(f"tcp://127.0.0.1:{port}")
    
    model = IsolationForest(contamination=0.1, random_state=42)
    data_buffer = []
    buffer_limit = 50 # How many points to collect before training/predicting
    max_buffer_size = 200 # Keep a rolling window of the most recent points for training
    train_every_n_points = 20 # Re-train the model every N new points to adapt to changes
    points_since_last_train = 0

    print(f"--- [WORKER] Monitoring Port {port} with {model_type}")

    while True:
        if os.getppid() == 1:  # Check if parent process has exited (in case of orphaned workers)
            print("--- [MANAGER] Parent process has exited. Shutting down manager.")
            break

        try:
            if receiver.poll(1000):  # Wait for a message with a timeout to allow graceful shutdown checks
                message = receiver.recv_string()
                packet = json.loads(message)
                
                # We append new values to our rolling buffer
                new_values = [p['value'] for p in packet['datapoints']]
                data_buffer.extend(new_values)
                points_since_last_train += len(new_values)

                # Keep only the most recent points
                if len(data_buffer) > max_buffer_size:
                    data_buffer = data_buffer[-max_buffer_size:]

                if len(data_buffer) >= buffer_limit and hasattr(model, 'estimators_'):
                    X_latest = [[v] for v in new_values]
                    predictions = model.predict(X_latest)
                    
                    for val, pred in zip(new_values, predictions):
                        if pred == -1:
                            print(f"\n[!] ANOMALY Port {port}: Value {val:.2f} is an outlier!")
                        else:
                            sys.stdout.write(f"\r[OK] Port {port}: Last value {val:.2f}")
                            sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r[WARMUP] Port {port}: Filling buffer and initializing model ({len(data_buffer)}/{buffer_limit})")
                    sys.stdout.flush()

                if len(data_buffer) >= buffer_limit and points_since_last_train >= train_every_n_points:
                    X = np.array([[v] for v in data_buffer])
                    X = shuffle(X, random_state=42) # Shuffle to avoid any time-based patterns
                    X = np.asarray(X)
                    
                    # Re-fit the model with the updated buffer
                    model.fit(X)
                    points_since_last_train = 0

        except Exception as e:
            print(f"\n[ERROR] Worker on Port {port} encountered an error: {e}")
            break

active_workers = []

def shutdown_handler(sig, frame):
    """Gracefully terminates all child processes on Ctrl+C."""
    print(f"\n--- [SYSTEM] Termination signal received. Cleaning up {len(active_workers)} workers...")
    
    for p in active_workers:
        if p.is_alive():
            print(f"--- Stopping Worker: {p.name} (PID: {p.pid})")
            p.terminate() # Sends SIGTERM
            p.join(timeout=2) # Wait a moment for it to release the ZMQ port
            
    print("--- [SYSTEM] All processes cleared. Exit.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

def start_manager(port=5555):
    """
    The 'Discovery' service. 
    Listens for C++ to automatically register ports of new streams.
    """
    context = zmq.Context()
    # Use REP (Request-Reply) for the handshake we discussed
    discovery = context.socket(zmq.REP)
    discovery.bind(f"tcp://127.0.0.1:{port}")

    print("--- [MANAGER] Awaiting C++ registrations...")

    while True:
        # Wait for registration JSON
        msg = discovery.recv_json()

        if isinstance(msg, dict):
            port = msg.get('port')
        else:
            port = msg 
            print(f"[Warning] Received raw port {port} instead of JSON object.")
        
        if port is None:
            print("[Error] No port provided in message.")
            discovery.send_json({"status": "error", "message": "Missing port"})
            continue

        # Spawn the worker process
        p = multiprocessing.Process(target=run_model_worker, args=(port,), daemon=True)
        p.start()

        # Keep track of active workers to ensure we can clean them up on shutdown
        active_workers.append(p)
        
        # Return acknowledgment to C++
        discovery.send_json({"status": "worker_spawned", "port": port})
        print(f"--- [MANAGER] Started dedicated model for port {port}")

if __name__ == "__main__":
    # For now, you can choose to run the manager 
    # OR just call start_analytics_engine() for a single test.
    start_manager()