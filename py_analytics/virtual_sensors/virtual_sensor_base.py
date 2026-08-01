import datetime

import numpy as np
import math

class VirtualSensor:
    def __init__(self, name, sensor, sampling_rate: int, connected_sensors: dict[str, float], initial_connected_sensors_weights: list[float] = []):
        self.name = name
        self.sensor = sensor
        self.connected_sensors = connected_sensors
        self.connected_sensors_weights = initial_connected_sensors_weights
        self.sampling_rate = sampling_rate

    def correlation(self, batches: list[dict], from_time: str, to_time: str):
        for connected_sensor, sampling_rate_ in self.connected_sensors.items():
            if sampling_rate_ > self.sampling_rate:
                print(f"--- [INFO] Connected sensor {connected_sensor} has a higher sampling rate ({sampling_rate_}) than the virtual sensor {self.name} ({self.sampling_rate}). NOT RECOMMENDED! May lead to data loss or misalignment.")
                common = math.gcd(sampling_rate_, self.sampling_rate)
                print(f"--- [INFO] Common sampling rate: {common}")

                for batch in batches:
                    for datapoint in batch["datapoints"]:
                        base_from, frac_from = from_time.rsplit('.', 1)
                        base_to, frac_to = to_time.rsplit('.', 1)
                        frac_from = frac_from.zfill(3)[:3]
                        frac_to = frac_to.zfill(3)[:3]

                        from_time = datetime.strptime(f"{base_from}.{frac_from}", "%Y-%m-%d %H:%M:%S.%f")
                        to_time = datetime.strptime(f"{base_to}.{frac_to}", "%Y-%m-%d %H:%M:%S.%f")

                        if from_time in datapoint["timestamp"] and to_time in datapoint["timestamp"]:
                            print(f"--- [INFO] Processing batch {batch} for connected sensor {connected_sensor}.")
                        else:
                            print(f"--- [INFO] Skipping batch {batch} for connected sensor {connected_sensor}.")

                
                # TO BE IMPLEMENTED: Logic to handle the correlation between the virtual sensor and its connected sensors based on the common sampling rate.

    def select_timeframe(self, from_time: str, to_time: str):
        pass

    def train(self):
        pass