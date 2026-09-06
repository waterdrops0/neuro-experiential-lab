import json
import logging
import time
import uuid
from core.models import utc_now
from storage.csv_logger import CSVLogger
from storage.database import Database

class SessionManager:
    def __init__(self, bus, directory, clock=time.monotonic):
        self.bus, self.directory, self.clock = bus, directory, clock
        self.status = 'IDLE'
        self.session_id = None
        self.total = 0.0
        self.started = None
        self.marker_count = 0
        self.last_event = '—'
        self.error = ''
        self.csv = self.db = None

    @property
    def elapsed(self):
        return self.total + (max(0, self.clock()-self.started) if self.status == 'RUNNING' else 0)

    def start(self, configuration=None):
        if self.status in ('RUNNING', 'PAUSED'):
            return
        self.session_id = uuid.uuid4().hex
        folder = self.directory / self.session_id
        folder.mkdir(parents=True)
        try:
            self.csv = CSVLogger(folder)
            self.db = Database(folder / 'session.sqlite3')
            (folder / 'configuration.json').write_text(json.dumps(configuration or {}, indent=2), encoding='utf-8')
            self.db.connection.execute('INSERT INTO session VALUES (?, ?, NULL, ?)', (self.session_id, utc_now(), 'RUNNING'))
            self.db.connection.commit()
        except Exception:
            self.close_storage()
            raise
        self.total, self.marker_count, self.error = 0.0, 0, ''
        self.started = self.clock()
        self.status = 'RUNNING'
        self.marker('SESSION_STARTED')
        self.bus.publish('session_started', session_id=self.session_id)

    def _write(self, kind, row):
        errors = []
        for writer in (self.db, self.csv):
            try:
                writer.write(kind, row)
            except Exception as exc:
                logging.exception('Session storage failure')
                errors.append(str(exc))
        if errors:
            self.error = 'LOGGING ERROR: ' + '; '.join(errors)
            self.bus.publish('storage_error', message=self.error)

    def marker(self, event_type, previous_state='', new_state='', operator_note=''):
        if self.status not in ('RUNNING', 'PAUSED'):
            return
        row = dict(timestamp=utc_now(), session_time=self.elapsed, event_type=event_type, previous_state=previous_state, new_state=new_state, operator_note=operator_note)
        self._write('events', row)
        self.marker_count += 1
        self.last_event = f'{event_type} {new_state} {operator_note}'.strip()
        self.bus.publish('marker_added', marker=row)

    def pause(self):
        if self.status == 'RUNNING':
            self.total = self.elapsed
            self.status = 'PAUSED'
            self.marker('SESSION_PAUSED')
        elif self.status == 'PAUSED':
            self.started = self.clock()
            self.status = 'RUNNING'
            self.marker('SESSION_RESUMED')

    def record(self, sample, state, audio, haptic):
        if self.status != 'RUNNING':
            return
        self._write('samples', dict(timestamp=sample.timestamp, elapsed_session_time=max(0, self.elapsed - max(0, self.clock()-sample.monotonic_time)), hr=sample.hr, rr=sample.rr, rmssd=sample.rmssd, signal_quality=sample.signal_quality, current_state=state, audio_profile=audio.profile, haptic_profile=haptic.profile, haptic_intensity=haptic.intensity))

    def end(self):
        if self.status not in ('RUNNING', 'PAUSED'):
            return
        self.marker('SESSION_ENDED')
        self.total = self.elapsed
        self.status = 'ENDED'
        try:
            self.db.connection.execute('UPDATE session SET ended_at=?, status=?', (utc_now(), 'ENDED'))
            self.db.connection.commit()
        finally:
            self.close_storage()
        self.bus.publish('session_ended', session_id=self.session_id)

    def close_storage(self):
        for writer in (self.csv, self.db):
            if writer:
                writer.close()
        self.csv = self.db = None
