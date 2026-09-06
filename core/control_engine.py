import logging
import time

class ControlEngine:
    def __init__(self, bus, states, audio, haptic, session, clock=time.monotonic):
        self.bus, self.states, self.audio, self.haptic, self.session, self.clock = bus, states, audio, haptic, session, clock
        self.current_state = 'SAFE'
        self.outputs_stopped = True

    def change_state(self, name):
        if name not in self.states:
            raise ValueError(f'Unknown state: {name}')
        previous = self.current_state
        self.current_state = name
        self.outputs_stopped = False
        now = self.clock()
        for output, config, event in [(self.audio, self.states[name]['audio'], 'audio_profile_changed'), (self.haptic, self.states[name]['haptic'], 'haptic_profile_changed')]:
            try:
                if output is self.audio:
                    output.apply_profile(name, config, now)
                else:
                    output.apply_profile(config, now)
                self.bus.publish(event, profile=output.profile)
            except Exception:
                logging.exception('Output transition failed')
                try:
                    output.stop()
                except Exception:
                    logging.exception('Output stop failed')
                self.session.marker('OUTPUT_ERROR', operator_note=event)
        self.session.marker('STATE_CHANGED', previous, name)
        self.bus.publish('state_changed', previous_state=previous, new_state=name)

    def stop_outputs(self, reason='EMERGENCY_STOP'):
        self.outputs_stopped = True
        for output in (self.audio, self.haptic):
            try:
                output.stop()
            except Exception:
                logging.exception('Emergency stop failed')
        self.outputs_stopped = True
        self.session.marker(reason, new_state=self.current_state)
        self.bus.publish('outputs_stopped')
