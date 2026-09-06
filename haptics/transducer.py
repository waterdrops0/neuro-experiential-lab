from haptics.base import HapticOutput

class AudioTransducerHapticOutput(HapticOutput):
    """Future dedicated audio-device output. Implement bounded waveform generation,
    device selection, watchdog and immediate mute independently of programme audio.
    """
    def apply_profile(self, config, now):
        raise NotImplementedError('Transducer hardware output is not installed')
    def update(self, now):
        pass
    def stop(self):
        pass
