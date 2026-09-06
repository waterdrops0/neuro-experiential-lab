import csv
import json
import sqlite3
from pathlib import Path
import pytest
from core.event_bus import EventBus
from core.models import load_states
from core.session_manager import SessionManager
from core.control_engine import ControlEngine
from sensors.simulator import SimulatedSensorProvider, calculate_rmssd
from haptics.simulator import SimulatedHapticOutput

ROOT = Path(__file__).resolve().parents[1]

class FakeAudio:
    profile = 'OFF'
    def apply_profile(self, name, config, now):
        self.profile = name
    def stop(self):
        self.profile = 'OFF'

@pytest.fixture
def system(tmp_path):
    now = [100.0]
    clock = lambda: now[0]
    bus = EventBus()
    session = SessionManager(bus, tmp_path, clock)
    engine = ControlEngine(bus, load_states(ROOT/'config/states.json'), FakeAudio(), SimulatedHapticOutput(), session, clock)
    return engine, session, now, tmp_path

def test_rmssd():
    assert calculate_rmssd([]) is None
    assert calculate_rmssd([800]) is None
    assert calculate_rmssd([800, 810, 800]) == 10
    assert calculate_rmssd([800, 800, 800]) == 0

def test_simulator():
    sensor = SimulatedSensorProvider(seed=42)
    sensor.connect()
    samples = []
    for i in range(2400):
        samples.extend(sensor.poll(i*.25))
    assert 500 < len(samples) < 1000
    assert all(55 <= p.hr <= 100 and abs(p.rr*p.hr-60000) < 1e-8 for p in samples)
    assert {p.signal_quality for p in samples} == {'GOOD', 'FAIR', 'POOR'}
    assert len({round(p.hr, 1) for p in samples}) > 50
    assert all(p.rmssd is None or 0 <= p.rmssd < 100 for p in samples)
    sensor.disconnect()
    assert sensor.poll(700) == []

def test_session_transitions_logging_stop(system):
    engine, session, now, folder = system
    session.start(engine.states)
    sid = session.session_id
    engine.change_state('RESOURCE')
    now[0] += 3
    engine.haptic.update(now[0])
    assert engine.haptic.intensity == .3
    sensor = SimulatedSensorProvider(seed=1)
    sensor.connect()
    sample = sensor.poll(now[0])[0]
    session.record(sample, engine.current_state, engine.audio, engine.haptic)
    engine.stop_outputs()
    assert engine.audio.profile == engine.haptic.profile == 'OFF'
    assert engine.haptic.intensity == 0
    now[0] += 1
    engine.haptic.update(now[0])
    assert engine.haptic.intensity == 0
    session.record(sample, engine.current_state, engine.audio, engine.haptic)
    session.marker('SUDS', operator_note='6')
    session.pause()
    elapsed = session.elapsed
    now[0] += 10
    assert session.elapsed == elapsed
    session.record(sample, engine.current_state, engine.audio, engine.haptic)
    session.pause()
    now[0] += 2
    session.end()
    assert session.elapsed == elapsed + 2
    rows = list(csv.DictReader((folder/sid/'samples.csv').open()))
    assert len(rows) == 2
    assert rows[1]['audio_profile'] == 'OFF'
    db = sqlite3.connect(folder/sid/'session.sqlite3')
    assert db.execute('SELECT COUNT(*) FROM samples').fetchone()[0] == 2
    assert db.execute("SELECT operator_note FROM events WHERE event_type='SUDS'").fetchone()[0] == '6'
    assert db.execute('SELECT status FROM session').fetchone()[0] == 'ENDED'
    events = list(csv.DictReader((folder/sid/'events.csv').open()))
    assert len(events) == db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    db.close()
    session.start()
    assert session.session_id != sid
    session.end()

def test_all_states_and_invalid(system):
    engine, session, now, _ = system
    session.start()
    for state in engine.states:
        engine.change_state(state)
        assert engine.current_state == state
        assert engine.audio.profile == state
    with pytest.raises(ValueError):
        engine.change_state('UNKNOWN')
    session.end()

def test_haptic_fade():
    h = SimulatedHapticOutput()
    c = dict(profile='a', intensity=.4, frequency=35, pattern='steady', fade_in=2, fade_out=1)
    h.apply_profile(c, 0)
    h.update(1)
    assert h.intensity == pytest.approx(.2)
    h.update(2)
    h.apply_profile(dict(c, intensity=.2), 2)
    h.update(2.5)
    assert h.intensity == pytest.approx(.2)
    h.update(3)
    assert h.intensity == 0
    h.update(5)
    assert h.intensity == .2

def test_invalid_config(tmp_path):
    config = load_states(ROOT/'config/states.json')
    config['SAFE']['audio']['volume'] = 2
    p = tmp_path/'states.json'
    p.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_states(p)

def test_storage_failure_is_reported(system):
    engine, session, _, _ = system
    session.start()
    session.csv.files['events'].close()
    session.marker('TEST')
    assert 'LOGGING ERROR' in session.error
    session.end()

def test_stop_attempts_both_outputs(system):
    engine, _, _, _ = system
    engine.haptic.intensity = .5
    def fail():
        raise RuntimeError('device failed')
    engine.audio.stop = fail
    engine.stop_outputs()
    assert engine.haptic.intensity == 0
    assert engine.outputs_stopped
