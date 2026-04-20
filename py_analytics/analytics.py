import sys
import multiprocessing
import signal
import zmq
from .models import IsolationForestStrategy, RiverStrategy
from .worker import ZMQWorker
from pathlib import Path
import joblib

active_workers = []

def run_model_worker_process(port, model_type):
    """Entry point for the multiprocessing.Process"""

    # Check if their is a saved model
    folder = "./py_analytics/models"
    models = get_latest_model(folder)

    if model_type == "River":
        strategy = RiverStrategy()
        prefix = "RiverHalfSpaceTrees"
    else:
        strategy = IsolationForestStrategy()
        prefix = "SKlearnIsolatedForest"

    if models:
        model_to_load = None
        for model in models:
            if prefix in str(model):
                model_to_load = model

        if model_to_load:
            strategy.model = joblib.load(model_to_load)
            print(f"[LOADED] {model_to_load}")
            
    worker = ZMQWorker(port, strategy)
    worker.start()

def shutdown_handler(sig, frame):
    print(f"\n--- [SYSTEM] Termination signal received. Cleaning up {len(active_workers)} workers...")
    for p in active_workers:
        if p.is_alive():
            p.terminate()
            p.join(timeout=2)
    print("--- [SYSTEM] All processes cleared. Exit.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

def start_manager(port=5555, default_model="River"):
    context = zmq.Context()
    discovery = context.socket(zmq.REP)
    discovery.bind(f"tcp://127.0.0.1:{port}")

    print(f"--- [MANAGER] Awaiting C++ registrations (Mode: {default_model})...")

    while True:
        msg = discovery.recv_json()
        
        # Support both JSON object and raw port
        if isinstance(msg, dict):
            stream_port = msg.get('port')
            model_type = "River"
        else:
            stream_port = msg
            model_type = default_model
    
        p = multiprocessing.Process(
            target=run_model_worker_process, 
            args=(stream_port, model_type), 
            daemon=True
        )
        p.start()
        active_workers.append(p)
        
        discovery.send_json({"status": "worker_spawned", "port": stream_port})
        print(f"--- [MANAGER] Started {model_type} worker for port {stream_port}")

def get_latest_model(folder_path: str, extension: str = "*.pkl"):
    path = Path(folder_path)
    files = list(path.glob(extension))
    
    if not files:
        return None
        
    # latest_file = max(files, key=lambda f: f.stat().st_mtime)
    return files

if __name__ == "__main__":
    start_manager()