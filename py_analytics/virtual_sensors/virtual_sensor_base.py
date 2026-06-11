from abc import ABC

class VirtualSensor(ABC):
    def __init__(self, name):
        self.name = name

    def on(self):
        pass

    def off(self):
        pass