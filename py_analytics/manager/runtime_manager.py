import multiprocessing
import sys

import zmq

from ..config.group_config import GroupConfig
from ..config.worker_context import WorkerContext
from ..workers.process import run_model_worker_process

class RuntimeManager:
    def __init__(self):
        self.active_workers = []
        self._contexts: dict[str, WorkerContext] = {}

    def register(self, discovery_socket, msg):
        action = msg.get('action')

        if action == "register_stream":
            self._register_stream(discovery_socket, msg)
        elif action == "register_group":
            self._register_group(discovery_socket, msg)
        else:
            raise NameError(f"No '{action}' action found!")

    def _register_group(self, discovery_socket, msg):
        try:
            if isinstance(msg, dict):
                group_id = msg.get('group_id')
                config = GroupConfig.from_dict(msg)

                context = WorkerContext(group_id=group_id, group_config=config)
                self._contexts[group_id] = context
                
            try:
                discovery_socket.send_json({"status": "group_registered", "id": group_id})
                print(f"--- [MANAGER] Registered group {group_id}")
            except zmq.ZMQError as send_err:
                print(f"--- [ERROR] Failed to send group registration message: {send_err}")
                return 1

        except (ValueError, TypeError) as validation_err:
            print(f"--- [ERROR] Validation error: {validation_err}")
            discovery_socket.send_json({"status": "error", "message": f"Validation failed: {validation_err}"})

    def _register_stream(self, discovery_socket, msg):
        try:
            if isinstance(msg, dict):
                stream_port = msg.get('port')
                strategy = msg.get('ml_model')

                group_id = msg.get('group_id', None)
                serialization = msg.get('serialization', 'json')

            if not stream_port or not isinstance(stream_port, int) or not (1024 <= stream_port <= 65535):
                raise ValueError(f"Invalid or out-of-bounds network port specified: {stream_port}")
            
            if not isinstance(strategy, (str, type(None))) or (isinstance(strategy, str) and not strategy.strip()):
                raise ValueError("Strategy must be a non-empty string definition or None.")

        except (ValueError, TypeError) as validation_err:
            print(f"--- [ERROR] Validation error: {validation_err}")
            discovery_socket.send_json({"status": "error", "message": f"Validation failed: {validation_err}"})

        try:
            p = multiprocessing.Process(
                target=run_model_worker_process, 
                args=(self._contexts[group_id], stream_port, strategy, serialization), 
                daemon=True)

            p.start()

            self.active_workers.append(p)
            
        except Exception as proc_err:
            print(f"--- [ERROR] Failed to start worker process: {proc_err}")
            discovery_socket.send_json({"status": "error", "message": f"Failed to start worker: {proc_err}"})

        try:
            discovery_socket.send_json({"status": "worker_spawned", "port": stream_port})
            print(f"--- [MANAGER] Started {strategy} worker for port {stream_port}")
        except zmq.ZMQError as send_err:
            print(f"--- [ERROR] Failed to send confirmation message: {send_err}")

    def shutdown_handler(self, sig: int, frame):
        print(f"--- [SYSTEM] Termination signal received. Cleaning up {len(self._active_workers)} workers...\n")
        for p in self.active_workers:
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