import traceback

import zmq

from .runtime_manager import RuntimeManager
from ..transport.discovery import create_discovery_socket

def start_manager(port: int = 5555):
    context = zmq.Context()
    discovery = create_discovery_socket(context, port)

    runtime_manager = RuntimeManager(discovery)

    print("[MANAGER] Waiting for messages.")

    try:
        runtime_manager.run()
    except KeyboardInterrupt:
        print("[MANAGER] Keyboard interrupt received.")

    except Exception as e:
        print(f"[MANAGER] FATAL EXCEPTION: {e}")
        traceback.print_exc()

    finally:
        print("[MANAGER] Entering cleanup...")
        runtime_manager.shutdown_handler()