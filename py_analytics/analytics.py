import sys
import multiprocessing
import signal
import zmq
from .models import IsolationForestStrategy, RiverStrategy
from .worker import ZMQWorker

active_workers = []

def run_model_worker_process(port, model_type):
    """Entry point for the multiprocessing.Process"""
    if model_type == "River":
        strategy = RiverStrategy()
    else:
        strategy = IsolationForestStrategy()
        
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

def start_manager(port=5555, default_model="IsolationForest"):
    context = zmq.Context()
    discovery = context.socket(zmq.REP)
    discovery.bind(f"tcp://127.0.0.1:{port}")

    print(f"--- [MANAGER] Awaiting C++ registrations (Mode: {default_model})...")

    while True:
        msg = discovery.recv_json()
        
        # Support both JSON object and raw port
        if isinstance(msg, dict):
            stream_port = msg.get('port')
            model_type = msg.get('model_type', default_model)
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

if __name__ == "__main__":
    start_manager()