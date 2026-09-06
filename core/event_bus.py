import logging
from collections import defaultdict

class EventBus:
    """Synchronous pub/sub. Hardware adapters must marshal callbacks to the UI thread."""
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event, callback):
        self._subscribers[event].append(callback)

    def publish(self, event, **payload):
        for callback in tuple(self._subscribers[event]):
            try:
                callback(**payload)
            except Exception:
                logging.exception('Event subscriber failed: %s', event)
