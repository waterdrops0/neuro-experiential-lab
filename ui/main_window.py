import logging
import time
from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QSpinBox, QListWidget, QProgressBar, QMessageBox, QApplication)
from ui.dashboard import MetricCard, STYLE
from ui.charts import LiveCharts
from ui.state_controls import StateControls

class MainWindow(QMainWindow):
    def __init__(self, bus, engine, sensor, settings):
        super().__init__()
        self.bus, self.engine, self.sensor, self.settings = bus, engine, sensor, settings
        self.session = engine.session
        self.latest = None
        self.last_received = time.monotonic()
        self.disconnected = False
        self.setWindowTitle('Neuro Experiential Control Lab — MVP v0.1')
        self.resize(1380, 880)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        title = QLabel('NEURO EXPERIENTIAL CONTROL LAB  /  MVP v0.1')
        title.setObjectName('title')
        layout.addWidget(title)
        layout.addWidget(QLabel('DEMO · Simulated physiology & haptics · Experimental output only'))
        self.top = QLabel()
        self.top.setWordWrap(True)
        layout.addWidget(self.top)
        self.error_label = QLabel('')
        self.error_label.setStyleSheet('color: #ff9c9c')
        layout.addWidget(self.error_label)
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        left = QVBoxLayout()
        body.addLayout(left, 1)
        self.metrics = {}
        for name, unit in [('Heart Rate', 'BPM'), ('RR interval', 'ms'), ('HRV RMSSD', 'ms · last 60 beats'), ('Signal Quality', '')]:
            card = MetricCard(name, unit)
            self.metrics[name] = card
            left.addWidget(card)
        self.suds = QSpinBox()
        self.suds.setRange(0, 10)
        left.addWidget(QLabel('SUDS / self-report · 0–10'))
        left.addWidget(self.suds)
        self.suds_button = QPushButton('SAVE SUDS')
        self.suds_button.clicked.connect(lambda: self.session.marker('SUDS', operator_note=str(self.suds.value())))
        left.addWidget(self.suds_button)
        self.charts = LiveCharts(settings['chart_window_seconds'])
        body.addWidget(self.charts, 4)
        right = QVBoxLayout()
        body.addLayout(right, 2)
        self.state_card = MetricCard('CURRENT STATE')
        right.addWidget(self.state_card)
        self.outputs = QLabel()
        self.outputs.setWordWrap(True)
        right.addWidget(self.outputs)
        self.amplitude = QProgressBar()
        self.amplitude.setFormat('Simulated amplitude: %p%')
        right.addWidget(self.amplitude)
        self.count = QLabel('Events: 0')
        right.addWidget(self.count)
        right.addWidget(QLabel('Recent markers'))
        self.markers = QListWidget()
        right.addWidget(self.markers, 1)
        self.states = StateControls(self.change_state, self)
        layout.addWidget(self.states)
        self.note = QLineEdit()
        self.note.setPlaceholderText('Optional operator note · state shortcuts are suspended while typing here')
        self.note.setMaxLength(500)
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        layout.addLayout(bottom)
        self.start_button = self.button(bottom, 'START SESSION', self.start_session)
        self.pause_button = self.button(bottom, 'PAUSE', self.pause_session)
        self.marker_button = self.button(bottom, 'ADD MARKER', self.add_marker)
        self.stop_button = self.button(bottom, 'STOP OUTPUTS · ESC', self.engine.stop_outputs)
        self.stop_button.setObjectName('stop')
        self.end_button = self.button(bottom, 'END SESSION', self.end_session)
        self.escape = QShortcut(QKeySequence('Escape'), self)
        self.escape.activated.connect(self.engine.stop_outputs)
        bus.subscribe('marker_added', self.marker_added)
        bus.subscribe('physiological_data_updated', self.receive_sample)
        bus.subscribe('storage_error', self.storage_error)
        QApplication.instance().focusChanged.connect(self.focus_changed)
        try:
            sensor.connect()
        except Exception:
            logging.exception('Sensor connection failed')
            sensor.disconnect()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(round(1000/settings['ui_refresh_hz']))
        self.tick()

    def button(self, layout, text, callback):
        button = QPushButton(text)
        button.setMinimumHeight(50)
        button.clicked.connect(lambda checked=False: self.safe_call(callback))
        layout.addWidget(button)
        return button

    def safe_call(self, callback):
        try:
            callback()
        except Exception as exc:
            logging.exception('Operator action failed')
            self.error_label.setText(str(exc))
            QMessageBox.warning(self, 'Operation failed', str(exc))

    def focus_changed(self, old, new):
        editing = isinstance(new, (QLineEdit, QSpinBox))
        for shortcut in self.states.shortcuts:
            shortcut.setEnabled(not editing)

    def storage_error(self, message):
        self.error_label.setText(message)
        self.engine.stop_outputs('STORAGE_FAILURE_STOP') if not self.engine.outputs_stopped else None

    def change_state(self, name):
        self.safe_call(lambda: self.engine.change_state(name))
        self.states.set_active(self.engine.current_state)
        self.refresh()

    def start_session(self):
        self.error_label.clear()
        self.markers.clear()
        self.session.start({'states': self.engine.states, 'settings': self.settings})
        self.engine.change_state('SAFE')
        self.refresh()

    def pause_session(self):
        if self.session.status == 'RUNNING':
            self.engine.stop_outputs('PAUSE_OUTPUTS_STOP')
        self.session.pause()
        # Resume recording leaves outputs stopped until an explicit state selection.
        self.refresh()

    def end_session(self):
        self.engine.stop_outputs('END_OUTPUTS_STOP')
        self.session.end()
        self.refresh()

    def add_marker(self):
        self.session.marker('OPERATOR_MARKER', operator_note=self.note.text().strip())
        self.note.clear()

    def marker_added(self, marker):
        self.markers.insertItem(0, f"{marker['session_time']:7.1f}s  {marker['event_type']}\n{marker['new_state']} {marker['operator_note']}")
        while self.markers.count() > 100:
            self.markers.takeItem(self.markers.count()-1)

    def receive_sample(self, sample):
        self.latest = sample
        self.last_received = time.monotonic()
        self.charts.add(sample)
        self.session.record(sample, self.engine.current_state, self.engine.audio, self.engine.haptic)

    def tick(self):
        now = time.monotonic()
        try:
            self.engine.audio.update(now)
            self.engine.haptic.update(now)
        except Exception:
            logging.exception('Output update failed')
            self.engine.stop_outputs('OUTPUT_ERROR')
        try:
            for sample in self.sensor.poll(now):
                self.bus.publish('physiological_data_updated', sample=sample)
        except Exception:
            logging.exception('Sensor polling failed')
            self.sensor.disconnect()
        disconnected = self.sensor.status == 'DISCONNECTED' or now-self.last_received > self.settings['sensor_timeout_seconds']
        if disconnected != self.disconnected:
            self.disconnected = disconnected
            self.session.marker('SENSOR_DISCONNECTED' if disconnected else 'SENSOR_RECONNECTED')
        self.charts.refresh(now)
        self.refresh()

    def refresh(self):
        s, e = self.session, self.engine
        seconds = int(s.elapsed)
        sensor_status = 'DISCONNECTED' if self.disconnected else self.sensor.status
        self.top.setText(f'Session: {s.session_id or "—"}  |  {s.status}  |  {seconds//60:02d}:{seconds%60:02d}  |  Sensor: {sensor_status}  |  Audio: {e.audio.status}  |  Haptic: SIMULATED / {e.haptic.status}  |  Controller: KEYBOARD')
        sample = self.latest
        values = [f'{sample.hr:.1f}', f'{sample.rr:.1f}', f'{sample.rmssd:.1f}' if sample.rmssd is not None else '—', sample.signal_quality] if sample and not self.disconnected else ['—', '—', '—', 'DISCONNECTED']
        for card, value in zip(self.metrics.values(), values):
            card.set_value(value)
        self.state_card.set_value(e.current_state)
        self.states.set_active(e.current_state)
        h = e.haptic
        self.outputs.setText(f'Outputs: {"STOPPED" if e.outputs_stopped else "ENABLED"}\n\nAudio: {e.audio.profile}\nStatus: {e.audio.status}\n\nHaptic: {h.profile}\nIntensity: {h.intensity*100:.1f}%\nPattern: {h.config.get("pattern", "—")}\nFrequency: {h.config.get("frequency", "—")} Hz (simulated)\nStatus: {h.status}')
        self.amplitude.setValue(round(h.amplitude*100))
        self.count.setText(f'Events: {s.marker_count}\nLast: {s.last_event}')
        self.count.setWordWrap(True)
        active = s.status in ('RUNNING', 'PAUSED')
        self.start_button.setEnabled(not active)
        for button in (self.pause_button, self.end_button, self.marker_button, self.suds_button):
            button.setEnabled(active)
        self.pause_button.setText('RESUME' if s.status == 'PAUSED' else 'PAUSE')

    def closeEvent(self, event):
        self.timer.stop()
        try:
            self.end_session()
        except Exception:
            logging.exception('Session close failed')
        finally:
            self.sensor.disconnect()
            self.engine.audio.close()
        event.accept()
