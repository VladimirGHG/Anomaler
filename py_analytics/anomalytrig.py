import zmq
import json
import time
from datetime import datetime

def inject_anomaly(port: int, value_to_inject: float):
    context = zmq.Context()
    sender = context.socket(zmq.PUB) 
    sender.connect(f"tcp://127.0.0.1:{port}")
    
    time.sleep(0.1) 

    payload = {
        "shouldbeAnomaly": True,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "value": float(value_to_inject)
    }

    message_string = json.dumps(payload)
    sender.send_string(message_string)
    
    print(f"--- [INJECTOR] Sent anomaly value: {value_to_inject}")
    sender.close()