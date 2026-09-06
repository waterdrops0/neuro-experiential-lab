import csv

SAMPLE_FIELDS = ['timestamp', 'elapsed_session_time', 'hr', 'rr', 'rmssd', 'signal_quality', 'current_state', 'audio_profile', 'haptic_profile', 'haptic_intensity']
EVENT_FIELDS = ['timestamp', 'session_time', 'event_type', 'previous_state', 'new_state', 'operator_note']

class CSVLogger:
    def __init__(self, folder):
        self.files = {}
        self.writers = {}
        try:
            for kind, fields in [('samples', SAMPLE_FIELDS), ('events', EVENT_FIELDS)]:
                handle = (folder / f'{kind}.csv').open('w', newline='', encoding='utf-8')
                self.files[kind] = handle
                self.writers[kind] = csv.DictWriter(handle, fieldnames=fields)
                self.writers[kind].writeheader()
                handle.flush()
        except Exception:
            self.close()
            raise

    def write(self, kind, row):
        self.writers[kind].writerow(row)
        self.files[kind].flush()

    def close(self):
        for handle in self.files.values():
            handle.close()
