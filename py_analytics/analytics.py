import sys
import multiprocessing
import signal
import zmq
from .models import IsolationForestStrategy, RiverStrategy
from .worker import ZMQWorker
from pathlib import Path
import joblib

active_workers = []

def run_model_worker_process(
        port: int, # A port on which the ZMQWroker is going to wait for data points from the Cpp side.
        Amodel: str = "SKlearnIsolatedForest" # If a basic name is given, initiates a new model. When given a path, loads the model from that path.
    ):
    """Entry point for the multiprocessing.Process"""

    # Check if their is a saved model
    folder = "./py_analytics/models"
    models = get_latest_model(folder)
    
    if Amodel == "RiverHalfSpaceTrees":
        strategy = RiverStrategy()
    elif Amodel == "SKlearnIsolatedForest":
        strategy = IsolationForestStrategy()
    elif ".pkl" in Amodel: # If a specific path to a model is given, load the given model.
        print(Amodel)
        if Amodel in [str(model) for model in models]:
            strategy = joblib.load(Amodel)
            print(f"--- [LOADED] {Amodel}")
        else:
            raise NameError("--- [ERROR] Please provide a valid path to load an Amodel model")
    else:
        raise NameError("--- [ERROR] Please provide a valid Amodel name")

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

def start_manager(port=5555):
    context = zmq.Context()
    discovery = context.socket(zmq.REP)
    discovery.bind(f"tcp://127.0.0.1:{port}")

    print(f"--- [MANAGER] Awaiting C++ registrations ...")

    while True:
        msg = discovery.recv_json()
        
        # Support both JSON object and raw port
        if isinstance(msg, dict):
            stream_port = msg.get('port')
            model_type = msg.get('ml_model')
        else:
            stream_port = msg
            model_type = "RiverHalfSpaceTrees"
    
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
        return ""
        
    # latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(files)
    return files

if __name__ == "__main__":
    start_manager()