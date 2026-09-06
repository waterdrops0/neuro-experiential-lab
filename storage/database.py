import sqlite3
from storage.csv_logger import SAMPLE_FIELDS, EVENT_FIELDS

class Database:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('CREATE TABLE session (session_id TEXT PRIMARY KEY, started_at TEXT, ended_at TEXT, status TEXT)')
        numeric = {'elapsed_session_time', 'session_time', 'hr', 'rr', 'rmssd', 'haptic_intensity'}
        for table, fields in [('samples', SAMPLE_FIELDS), ('events', EVENT_FIELDS)]:
            columns = ', '.join(f'{field} {"REAL" if field in numeric else "TEXT"}' for field in fields)
            self.connection.execute(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, {columns})')
        self.connection.commit()

    def write(self, kind, row):
        fields = SAMPLE_FIELDS if kind == 'samples' else EVENT_FIELDS
        self.connection.execute(f'INSERT INTO {kind} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})', [row.get(k) for k in fields])
        self.connection.commit()

    def close(self):
        self.connection.close()
