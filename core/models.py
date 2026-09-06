from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

STATES = ('SAFE', 'RESOURCE', 'PERSPECTIVE', 'INTEGRATION', 'RETURN')

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

@dataclass(frozen=True)
class PhysiologicalSample:
    timestamp: str
    monotonic_time: float
    hr: float
    rr: float
    rmssd: float | None
    signal_quality: str
    beat: bool = True

    def to_dict(self):
        return asdict(self)

def load_states(path: Path):
    states = json.loads(path.read_text(encoding='utf-8'))
    if set(states) != set(STATES):
        raise ValueError('states.json must contain exactly the five supported states')
    for name, state in states.items():
        for section, bounded in [('audio', 'volume'), ('haptic', 'intensity')]:
            config = state[section]
            for key in (bounded, 'fade_in', 'fade_out'):
                value = config[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f'{name}.{section}.{key}: invalid number')
            if config[bounded] > 1:
                raise ValueError(f'{name}.{section}.{bounded} must be 0..1')
        if not isinstance(state['audio']['loop'], bool):
            raise ValueError('loop must be boolean')
        if not isinstance(state['audio']['file'], str):
            raise ValueError('audio file must be a string')
        h = state['haptic']
        if h['pattern'] not in ('steady', 'pulse', 'wave') or not h['profile']:
            raise ValueError('Invalid haptic pattern/profile')
        if not isinstance(h['frequency'], (int, float)) or not math.isfinite(h['frequency']) or h['frequency'] <= 0:
            raise ValueError('Invalid haptic frequency')
    return states
