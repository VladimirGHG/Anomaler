import json
import time

import zmq

from .runtime_manager import RuntimeManager
from ..transport.discovery import create_discovery_socket

registry = RuntimeManager()

def start_manager(port: int = 5555):
    context = zmq.Context()
    discovery = create_discovery_socket(context, port)
    print("[MANAGER] Waiting for a package through the discovery socket.")
    
    while True:
        try:
            try:
                msg = discovery.recv_json()
            except zmq.Again:
                continue
            except (zmq.ZMQError, ValueError, json.JSONDecodeError) as recv_err:
                print(f"--- [ERROR] Failed to receive or decode message: {recv_err}")
                discovery.send_json({"status": "error", "message": "Invalid JSON framing"})

            registry.register(discovery, msg)

        except Exception as e:
            print(f"--- [ERROR] Unexpected exception in manager loop: {e}")
            discovery.send_json({"status": "error", "message": "Manager internal loop exception"})
            
            time.sleep(1)