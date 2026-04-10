import zmq
import json
import pandas as pd
from sklearn.ensemble import IsolationForest
import multiprocessing
import signal
import sys
import time

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

    print(f"--- [WORKER] Monitoring Port {port} with {model_type}")

    while True:
        message = receiver.recv_string()
        packet = json.loads(message)
        
        # C++ might send a single point or a small batch
        # We append new values to our rolling buffer
        new_values = [p['value'] for p in packet['datapoints']]
        data_buffer.extend(new_values)

        # Keep only the most recent points
        if len(data_buffer) > 200:
            data_buffer = data_buffer[-200:]

        if len(data_buffer) >= buffer_limit:
            # Prepare data for Scikit-Learn
            X = [[v] for v in data_buffer]
            
            # Re-fit and predict
            model.fit(X)
            predictions = model.predict(X)
            
            # Check the most recent point (the latest one received)
            latest_score = predictions[-1]
            if latest_score == -1:
                print(f"[!] ANOMALY on Port {port}: Value {new_values[-1]} is an outlier!")
            else:
                print(f"[OK] Port {port}: Received {new_values[-1]}")

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