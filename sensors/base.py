from abc import ABC, abstractmethod

class SensorProvider(ABC):
    status = 'DISCONNECTED'

    @abstractmethod
    def connect(self): ...

    @abstractmethod
    def poll(self, now: float) -> list:
        """Return new beat-level PhysiologicalSample objects; never block the UI."""

    @abstractmethod
    def disconnect(self): ...
