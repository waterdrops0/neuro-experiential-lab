import logging
import math
import os
from array import array
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

class AudioEngine:
    """Two-channel, nonblocking fades; optional in-memory demo tones."""
    def __init__(self, root: Path, enabled=True):
        self.root = root
        self.status = 'OFF'
        self.profile = 'OFF'
        self.config = {}
        self.voices = []
        self.cache = {}
        self.mixer = None
        if not enabled:
            self.status = 'DISABLED'
            return
        try:
            import pygame.mixer as mixer
            mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
            mixer.set_num_channels(16)
            self.mixer = mixer
        except Exception:
            self.status = 'ERROR / NO DEVICE'
            logging.exception('Audio initialization failed')

    def load(self, name, config):
        key = config['file'] or f'demo:{name}'
        if key not in self.cache:
            if config['file']:
                self.cache[key] = self.mixer.Sound(str(self.root / config['file']))
            else:
                frequency = {'SAFE': 220, 'RESOURCE': 264, 'PERSPECTIVE': 330, 'INTEGRATION': 275, 'RETURN': 198}[name]
                samples = array('h', (int(2400*math.sin(2*math.pi*frequency*i/44100)) for i in range(88200)))
                self.cache[key] = self.mixer.Sound(buffer=samples)
        return self.cache[key]

    def apply_profile(self, name, config, now):
        if self.mixer is None:
            return
        try:
            sound = self.load(name, config)
            self.update(now)
            for voice in self.voices:
                voice.update(start=now, initial=voice['channel'].get_volume(), target=0, duration=self.config.get('fade_out', 0))
            channel = self.mixer.find_channel()
            if channel is None:
                oldest = self.voices.pop(0)
                oldest['channel'].stop()
                channel = oldest['channel']
            channel.set_volume(0)
            channel.play(sound, loops=-1 if config['loop'] else 0)
            self.voices.append(dict(channel=channel, start=now, initial=0, target=config['volume'], duration=config['fade_in']))
            self.config = dict(config)
            self.profile = config['file'] or f'DEMO tone / {name}'
            self.status = 'ACTIVE'
            self.update(now)
        except Exception:
            self.stop()
            self.status = 'ERROR'
            logging.exception('Audio profile failed: %s', name)

    def update(self, now):
        for voice in self.voices[:]:
            fraction = min(1, max(0, (now-voice['start'])/voice['duration'])) if voice['duration'] else 1
            voice['channel'].set_volume(voice['initial'] + fraction*(voice['target']-voice['initial']))
            if not voice['channel'].get_busy() or (fraction == 1 and voice['target'] == 0):
                voice['channel'].stop()
                self.voices.remove(voice)
        if self.mixer and not self.voices and self.status == 'ACTIVE':
            self.status = self.profile = 'OFF'

    def play(self, name, config, now):
        """Play or loop a profile with its configured fade-in."""
        self.apply_profile(name, config, now)

    def fade_out(self, seconds, now):
        """Schedule a nonblocking fade to silence; stop() remains immediate."""
        self.update(now)
        for voice in self.voices:
            voice.update(start=now, initial=voice['channel'].get_volume(), target=0,
                         duration=max(0, seconds))
        self.update(now)

    def set_volume(self, volume):
        volume = max(0, min(1, volume))
        if self.voices:
            self.voices[-1]['target'] = volume
        self.config['volume'] = volume

    def stop(self):
        if self.mixer:
            self.mixer.stop()
        self.voices.clear()
        self.profile = 'OFF'
        if self.mixer:
            self.status = 'OFF'

    def close(self):
        self.stop()
        if self.mixer:
            self.mixer.quit()
