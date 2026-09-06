import math
import random
from collections import deque
from core.models import PhysiologicalSample, utc_now
from sensors.base import SensorProvider

def calculate_rmssd(rr):
    values = list(rr)
    if len(values) < 2:
        return None
    return math.sqrt(sum((b-a)**2 for a, b in zip(values, values[1:])) / (len(values)-1))

class PhysiologicalSensorSimulator(SensorProvider):
    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.rr_window = deque(maxlen=60)
        self.next_beat = None
        self.origin = None
        self.drift = 0.0

    def connect(self):
        self.status = 'SIMULATED / CONNECTED'
        self.next_beat = None
        self.origin = None
        self.rr_window.clear()

    def disconnect(self):
        self.status = 'DISCONNECTED'

    def poll(self, now):
        if self.status == 'DISCONNECTED':
            return []
        if self.origin is None:
            self.origin = now
            self.next_beat = now
        samples = []
        while self.next_beat <= now:
            t = self.next_beat - self.origin
            self.drift = max(-3, min(3, self.drift + self.random.gauss(0, .08)))
            hr = 74 + 7*math.sin(t/42) + 3*math.sin(2*math.pi*.23*t) + self.drift + self.random.gauss(0, .45)
            hr = max(55, min(100, hr))
            rr = 60000/hr
            self.rr_window.append(rr)
            quality = 'POOR' if 110 < t % 180 < 114 else ('FAIR' if 100 < t % 180 < 120 else 'GOOD')
            samples.append(PhysiologicalSample(utc_now(), self.next_beat, hr, rr, calculate_rmssd(self.rr_window), quality))
            self.next_beat += rr/1000
            if len(samples) >= 10:  # avoid replay storms after machine sleep
                self.next_beat = now + rr/1000
                break
        return samples

SimulatedSensorProvider = PhysiologicalSensorSimulator
