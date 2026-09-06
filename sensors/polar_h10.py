from sensors.base import SensorProvider

class PolarH10Provider(SensorProvider):
    """Future BLE adapter: decode HR/RR notifications in a worker, queue beats for poll.
    Convert RR units to ms, preserve device timestamps and report stale/disconnected.
    No synthetic data may be emitted by this adapter.
    """
    def connect(self):
        raise NotImplementedError('Polar H10 hardware adapter is not installed')
    def poll(self, now):
        return []
    def disconnect(self):
        self.status = 'DISCONNECTED'
