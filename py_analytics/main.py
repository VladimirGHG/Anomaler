import sys
import multiprocessing
import signal
import json
import time

import zmq
import joblib
from pathlib import Path

from .models.river_strategy import RiverStrategy
from .models.sklearn_strategies.isolationforest_strategy import IsolationForestStrategy
from .worker import ZMQWorker

active_workers = []

def run_model_worker_process(
        port: int, # A port on which the ZMQWroker is going to wait for data points from the Cpp side.
        Amodel: str = "SKlearnIsolatedForest", # If a basic name is given, initiates a new model. When given a path, loads the model from that path.
        serialization: str = "json"
    ):
    """Entry point for the multiprocessing.Process"""

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # Check if their is a saved model
    folder = "./py_analytics/models"
    if Amodel == "RiverHalfSpaceTrees":
        strategy = RiverStrategy()
    elif Amodel == "SKlearnIsolatedForest":
        strategy = IsolationForestStrategy()
    elif ".pkl" in Amodel: # If a specific path to a model is given, load the given model.
        models = get_saved_models(folder_path=folder)
        if Amodel in [str(model) for model in models]:
            strategy = joblib.load(Amodel)['model_state']
            strategy.logger.info(f"--- [LOADED] {joblib.load(Amodel)['metadata']}")
        else:
            raise NameError("--- [ERROR] Please provide a valid path to load an Amodel model")
    else:
        raise NameError("--- [ERROR] Please provide a valid Amodel name")

    worker = ZMQWorker(port, strategy, serialization)
    worker.start()

def shutdown_handler(sig: int, frame):
    print(f"--- [SYSTEM] Termination signal received. Cleaning up {len(active_workers)} workers...\n")
    for p in active_workers:
        try:
            if p.is_alive():
                p.terminate()
                p.join(timeout=2)

                if p.is_alive():
                    print(f"--- [WARNING] Worker {p.pid} did not terminate gracefully. Forcing kill.")
                    p.kill()
                    p.join(timeout=1)

        except Exception as e:
            print(f"--- [ERROR] Exception while terminating worker {p.pid}: {e}")
            continue

    print("--- [SYSTEM] All processes cleared. Exit.")
    sys.exit(0)

def start_manager(port: int = 5555):
    context = zmq.Context()

    try:
        discovery = context.socket(zmq.REP)
        discovery.setsockopt(zmq.LINGER, 0)
        discovery.setsockopt(zmq.RCVTIMEO, 1000)
        discovery.bind(f"tcp://127.0.0.1:{port}")
    except zmq.ZMQError as e:
        print(f"--- [ERROR] Failed to bind discovery socket on port {port}: {e}")
        context.destroy()
        sys.exit(1)

    print(f"--- [MANAGER] Awaiting C++ registrations ...")

    while True:
        try:
            try:
                msg = discovery.recv_json()
            except zmq.Again:
                continue
            except (zmq.ZMQError, ValueError, json.JSONDecodeError) as recv_err:
                print(f"--- [ERROR] Failed to receive or decode message: {recv_err}")
                try:
                    discovery.send_json({"status": "error", "message": "Invalid JSON framing"})
                except zmq.ZMQError:
                    pass
                continue

            try:
                # Support both JSON object and raw port
                if isinstance(msg, dict):
                    stream_port = msg.get('port')
                    model_type = msg.get('ml_model')
                    serialization = msg.get('serialization', 'json')
                else:
                    stream_port = msg
                    model_type = "RiverHalfSpaceTrees"
                    serialization = "json"

                if not stream_port or not isinstance(stream_port, int) or not (1024 <= stream_port <= 65535):
                    raise ValueError(f"Invalid or out-of-bounds network port specified: {stream_port}")
                
                if not isinstance(model_type, str) or not model_type.strip():
                    raise ValueError("Model type must be a non-empty string definition.")
            
            except (ValueError, TypeError) as validation_err:
                print(f"--- [ERROR] Validation error: {validation_err}")
                discovery.send_json({"status": "error", "message": f"Validation failed: {validation_err}"})
                continue

            try:
                p = multiprocessing.Process(
                    target=run_model_worker_process, 
                    args=(stream_port, model_type, serialization), 
                    daemon=True
                )
                p.start()
                active_workers.append(p)
            except Exception as proc_err:
                print(f"--- [ERROR] Failed to start worker process: {proc_err}")
                discovery.send_json({"status": "error", "message": f"Failed to start worker: {proc_err}"})
                continue

            try:
                discovery.send_json({"status": "worker_spawned", "port": stream_port})
                print(f"--- [MANAGER] Started {model_type} worker for port {stream_port}")
            except zmq.ZMQError as send_err:
                print(f"--- [ERROR] Failed to send confirmation message: {send_err}")
                continue

        except Exception as e:
            print(f"--- [ERROR] Unexpected exception in manager loop: {e}")
            try:
                discovery.send_json({"status": "error", "message": "Manager internal loop exception"})
            except zmq.ZMQError:
                pass
            
            time.sleep(1)

def get_saved_models(folder_path: str, extension: str = "*.pkl", get_latest=True):
    path = Path(folder_path)
    folder_models = list(path.glob("*"))
    if not folder_models:
        return ""
    

    saves = []
    print(folder_models)
    for folder_model in folder_models:
        saves.extend(list(folder_model.glob(extension)))

    return saves

if __name__ == "__main__":
    start_manager()