import datetime

import zmq
import numpy as np
import math

from ..workers.worker import ZMQWorker

class VirtualSensor:
    def __init__(self, name, group_config: dict, group_workers: list[ZMQWorker], initial_connected_sensors_weights: list[float] = []):
        self.name = name
        self.group_config = group_config
        self.group_workers = group_workers
        self.connected_sensors_weights = initial_connected_sensors_weights
    
    def correlation(self, batches: list[dict], from_time: str, to_time: str):
        for connected_sensor, sampling_rate_ in self.connected_sensors.items():
            if sampling_rate_ > self.sampling_rate:
                print(f"--- [INFO] Connected sensor {connected_sensor} has a higher sampling rate ({sampling_rate_}) than the virtual sensor {self.name} ({self.sampling_rate}). NOT RECOMMENDED! May lead to data loss or misalignment.")
                common = math.gcd(sampling_rate_, self.sampling_rate)
                print(f"--- [INFO] Common sampling rate: {common}")
                
                # TO BE IMPLEMENTED: Logic to handle the correlation between the virtual sensor and its connected sensors based on the common sampling rate.

    def select_timeframe(self, from_time: str, to_time: str):
        pass

    def train(self):
        pass