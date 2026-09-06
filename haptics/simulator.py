import math
from haptics.base import HapticOutput

class SimulatedHapticOutput(HapticOutput):
    def __init__(self):
        self.config = {}
        self.profile = 'OFF'
        self.intensity = 0.0
        self.amplitude = 0.0
        self.status = 'OFF'
        self.transition = None

    def apply_profile(self, config, now):
        self.update(now)
        old_out = self.config.get('fade_out', 0) if self.intensity else 0
        self.config = dict(config)
        self.profile = config['profile']
        self.transition = (now, self.intensity, old_out, config['fade_in'])
        self.status = 'ACTIVE'
        self.update(now)

    def update(self, now):
        if self.transition is None:
            return
        start, initial, out_time, in_time = self.transition
        elapsed = max(0, now-start)
        if elapsed < out_time:
            self.intensity = initial * (1-elapsed/out_time)
        else:
            self.intensity = self.config['intensity'] * (min(1, (elapsed-out_time)/in_time) if in_time else 1)
        pattern = self.config.get('pattern', 'steady')
        envelope = 1 if pattern == 'steady' else (.5 + .5*math.sin(2*math.pi*elapsed*(1 if pattern == 'pulse' else .2)))
        self.amplitude = self.intensity * envelope

    def stop(self):
        self.transition = None
        self.intensity = self.amplitude = 0.0
        self.profile = self.status = 'OFF'
