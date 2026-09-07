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


@pytest.fixture
def dashboard(app, tmp_path):
    bus = EventBus()
    session = SessionManager(bus, tmp_path)
    audio = AudioEngine(ROOT)
    engine = ControlEngine(bus, load_states(ROOT/'config/states.json'), audio,
                           SimulatedHapticOutput(), session)
    window = MainWindow(bus, engine, SimulatedSensorProvider(seed=1),
                        json.loads((ROOT/'config/settings.json').read_text()))
    window.timer.stop()
    window.show()
    QTest.qWait(30)
    yield window
    window.close()


def assert_controls_in_view(window):
    from PySide6.QtCore import QPoint, QRect
    controls = [window.start_button, window.pause_button, window.marker_button,
                window.stop_button, window.end_button, *window.states.buttons.values()]
    rects = []
    for button in controls:
        assert button.isVisible()
        rect = QRect(button.mapTo(window, QPoint()), button.size())
        assert window.rect().contains(rect), (button.text(), rect, window.rect())
        assert all(not rect.intersects(other) for other in rects)
        rects.append(rect)
        assert button.width() >= button.minimumSizeHint().width()
    assert window.stop_button.isEnabled()
    assert window.pause_button.isEnabled()
    assert window.marker_button.isEnabled()
    assert window.end_button.isEnabled()
    assert not window.start_button.isEnabled()


@pytest.mark.parametrize('size', [(1380, 880), (1920, 1080), (540, 500), (800, 600), (1000, 600), (1100, 720)])
def test_responsive_dashboard_controls(dashboard, size):
    window = dashboard
    window.resize(*size)
    window.start_session()
    QTest.qWait(30)
    assert window.width() == size[0]
    assert window.height() == size[1]
    for state in window.engine.states:
        window.change_state(state)
        QTest.qWait(20)
        assert_controls_in_view(window)
    for mode in (window.showMaximized, window.showNormal, window.showFullScreen,
                 window.showNormal):
        mode()
        QTest.qWait(30)
        assert_controls_in_view(window)
        button_height = window.pause_button.height()
        controls_top = window.states.y()
        minimum_size = window.minimumSizeHint()
        QTest.mouseClick(window.pause_button, Qt.LeftButton)
        QTest.qWait(30)
        assert window.session.status == 'PAUSED'
        assert window.pause_button.text() == 'RESUME'
        assert_controls_in_view(window)
        assert window.pause_button.height() == button_height
        assert window.states.y() == controls_top
        assert window.minimumSizeHint() == minimum_size
        QTest.mouseClick(window.pause_button, Qt.LeftButton)
        QTest.qWait(30)
        assert window.session.status == 'RUNNING'
        assert window.pause_button.text() == 'PAUSE'
        assert_controls_in_view(window)
        assert window.pause_button.height() == button_height
        assert window.states.y() == controls_top


def test_metric_values_fit_and_scroll_only_when_needed(dashboard):
    window = dashboard
    window.resize(1920, 1080)
    QTest.qWait(30)
    assert not window.dashboard_scroll.verticalScrollBar().isVisible()
    assert not window.dashboard_scroll.horizontalScrollBar().isVisible()
    for size in [(1380, 880), (1000, 600), (1920, 1080)]:
        window.resize(*size)
        for value in ('68 BPM', '884 ms', '46 ms', 'GOOD', 'DISCONNECTED'):
            for card in window.metrics.values():
                card.set_value(value)
            QTest.qWait(20)
            for card in window.metrics.values():
                label = card.value
                assert card.rect().contains(label.geometry())
                assert label.contentsRect().width() >= label.fontMetrics().horizontalAdvance(value)
                assert label.contentsRect().height() >= label.fontMetrics().height()
                for child in card.findChildren(type(window.top)):
                    assert card.rect().contains(child.geometry())
                    assert child.height() >= child.minimumSizeHint().height()
    window.resize(1000, 400)
    QTest.qWait(30)
    assert window.dashboard_scroll.verticalScrollBar().isVisible()
    window.start_session()
    assert_controls_in_view(window)
