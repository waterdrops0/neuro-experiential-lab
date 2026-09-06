"""Desktop entry point. Run from any directory: python /path/to/app.py."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-audio', action='store_true', help='Explicitly disable physical audio')
    parser.add_argument('--smoke-test', action='store_true', help='Run a short offscreen-compatible session and exit')
    parser.add_argument('--session-dir', type=Path)
    args = parser.parse_args()
    (ROOT / 'data').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(ROOT/'data/application.log', maxBytes=2_000_000, backupCount=3), logging.StreamHandler()], format='%(asctime)s %(levelname)s %(message)s')
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QTimer
    from core.models import load_states
    from core.event_bus import EventBus
    from core.control_engine import ControlEngine
    from core.session_manager import SessionManager
    from sensors.simulator import SimulatedSensorProvider
    from audio.audio_engine import AudioEngine
    from haptics.simulator import SimulatedHapticOutput
    from ui.main_window import MainWindow
    app = QApplication(sys.argv[:1])
    try:
        settings = json.loads((ROOT/'config/settings.json').read_text())
        if not 2 <= settings['ui_refresh_hz'] <= 5 or settings['chart_window_seconds'] <= 0 or settings['sensor_timeout_seconds'] <= 0:
            raise ValueError('Invalid refresh, chart window or sensor timeout')
        states = load_states(ROOT/'config/states.json')
        bus = EventBus()
        session = SessionManager(bus, args.session_dir or ROOT/settings['session_directory'])
        audio = AudioEngine(ROOT, enabled=settings['audio_enabled'] and not args.no_audio)
        engine = ControlEngine(bus, states, audio, SimulatedHapticOutput(), session)
        window = MainWindow(bus, engine, SimulatedSensorProvider(), settings)
    except Exception as exc:
        logging.exception('Startup failed')
        if not args.smoke_test:
            QMessageBox.critical(None, 'Startup error', str(exc))
        return 1
    window.show()
    if args.smoke_test:
        QTimer.singleShot(100, window.start_session)
        QTimer.singleShot(800, lambda: window.change_state('RESOURCE'))
        QTimer.singleShot(1500, window.add_marker)
        QTimer.singleShot(1800, engine.stop_outputs)
        QTimer.singleShot(2800, window.close)
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
