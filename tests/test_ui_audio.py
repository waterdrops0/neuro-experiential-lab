import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import json
import time
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from audio.audio_engine import AudioEngine
from core.models import load_states
from core.event_bus import EventBus
from core.session_manager import SessionManager
from core.control_engine import ControlEngine
from sensors.simulator import SimulatedSensorProvider
from haptics.simulator import SimulatedHapticOutput
from ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

def test_audio_crossfade_and_stop():
    audio = AudioEngine(ROOT)
    assert audio.mixer is not None
    states = load_states(ROOT/'config/states.json')
    audio.apply_profile('SAFE', states['SAFE']['audio'], 0)
    audio.update(3)
    assert audio.voices[0]['channel'].get_volume() == pytest.approx(.25, abs=.01)
    audio.apply_profile('RESOURCE', states['RESOURCE']['audio'], 3)
    assert len(audio.voices) == 2
    audio.update(6)
    assert len(audio.voices) == 1
    audio.fade_out(1, 6)
    audio.update(7)
    assert not audio.voices
    audio.play('SAFE', states['SAFE']['audio'], 8)
    audio.stop()
    audio.update(10)
    assert not audio.voices and not audio.mixer.get_busy()
    audio.apply_profile('SAFE', dict(states['SAFE']['audio'], file='missing.wav'), 11)
    assert audio.status == 'ERROR'
    audio.close()

def test_dashboard_lifecycle_shortcuts_disconnect(app, tmp_path):
    bus = EventBus()
    session = SessionManager(bus, tmp_path)
    audio = AudioEngine(ROOT)
    engine = ControlEngine(bus, load_states(ROOT/'config/states.json'), audio, SimulatedHapticOutput(), session)
    sensor = SimulatedSensorProvider(seed=1)
    settings = json.loads((ROOT/'config/settings.json').read_text())
    window = MainWindow(bus, engine, sensor, settings)
    window.show()
    window.activateWindow()
    QTest.qWait(50)
    QTest.mouseClick(window.start_button, Qt.LeftButton)
    assert session.status == 'RUNNING'
    window.note.clearFocus()
    window.start_button.setFocus()
    QTest.keyClick(window, Qt.Key_3)
    assert engine.current_state == 'PERSPECTIVE'
    window.note.setFocus()
    QTest.keyClicks(window.note, 'SUDS 6')
    assert engine.current_state == 'PERSPECTIVE'
    QTest.mouseClick(window.marker_button, Qt.LeftButton)
    assert 'SUDS 6' in session.last_event
    QTest.keyClick(window, Qt.Key_Escape)
    assert engine.outputs_stopped and not audio.mixer.get_busy()
    window.pause_session()
    assert session.status == 'PAUSED'
    window.pause_session()
    assert session.status == 'RUNNING' and engine.outputs_stopped
    sensor.disconnect()
    window.tick()
    assert 'DISCONNECTED' in window.top.text()
    sensor.connect()
    window.tick()
    assert not window.disconnected
    window.close()
    assert session.status == 'ENDED'
