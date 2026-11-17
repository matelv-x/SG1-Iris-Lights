"""Physical SG1 Iris state and indication on the wormhole LED strip."""

import json
import os
from pathlib import Path
from threading import Lock
from time import monotonic


class IrisLights:
    DEFAULT_FLASH_INTERVAL = 3
    DEFAULT_AUTO_OPEN_SECONDS = 0
    FLASH_DURATION = 0.18
    RED = (180, 0, 0)
    INCOMING_WARNING = '/audio_clips/unsceduald offworld activation.wav'

    def __init__(self, stargate):
        self.stargate = stargate
        self.pixels = stargate.wh_manager.pixels
        self.count = stargate.wh_manager.tot_leds
        if not isinstance(self.count, int) or self.count < 4:
            raise ValueError('SG1 Iris Lights requires at least four wormhole LEDs')
        self.path = Path(stargate.base_path) / 'config' / 'iris-lights.json'
        self.lock = Lock()
        self.closed = False
        self.enabled = False
        self.flash_interval = self.DEFAULT_FLASH_INTERVAL
        self.auto_incoming = True
        self.auto_open_seconds = self.DEFAULT_AUTO_OPEN_SECONDS
        self.offset = 0
        self.closed_since = None
        self.incoming_seen = False
        self.manual_open_during_incoming = False
        self.steady_visible = False
        self.pulse_until = 0.0
        self.clear_pending = False
        self.clear_indices = ()
        self.incoming_warning_clip = None
        self.next_flash = monotonic() + self.flash_interval
        self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.closed = data.get('closed') is True
            self.enabled = data.get('enabled', False) is True
            interval = data.get('flash_interval_seconds', self.DEFAULT_FLASH_INTERVAL)
            if type(interval) is int and 1 <= interval <= 3600:
                self.flash_interval = interval
            self.auto_incoming = data.get('auto_incoming', True) is True
            auto_open = data.get('auto_open_seconds', self.DEFAULT_AUTO_OPEN_SECONDS)
            if type(auto_open) is int and 0 <= auto_open <= 3600:
                self.auto_open_seconds = auto_open
            offset = data.get('offset', 0)
            if type(offset) is int:
                self.offset = offset % self.count
        except (OSError, ValueError, TypeError):
            pass
        if self.closed:
            self.closed_since = monotonic()
        self.next_flash = monotonic() + self.flash_interval

    @property
    def indices(self):
        return tuple((self.offset + (index * self.count) // 4) % self.count
                     for index in range(4))

    def status_unlocked(self):
        return {
            'closed': self.closed,
            'indices': self.indices,
            'led_count': self.count,
            'offset': self.offset,
            'enabled': self.enabled,
            'auto_incoming': self.auto_incoming,
            'auto_open_seconds': self.auto_open_seconds,
            'flash_interval_seconds': self.flash_interval,
        }

    def status(self):
        with self.lock:
            return self.status_unlocked()

    def set_closed(self, closed, manual=True):
        if type(closed) is not bool:
            raise ValueError('closed must be a boolean')
        with self.lock:
            incoming = self._incoming_activity()
            if manual and incoming:
                self.manual_open_during_incoming = not closed
            elif closed:
                self.manual_open_during_incoming = False
            if self.closed == closed:
                return self.status_unlocked()
            self.closed = closed
            self.closed_since = monotonic() if closed else None
            self.next_flash = monotonic() + self.flash_interval
            self.pulse_until = 0.0
            if not closed:
                self.clear_pending = True
                self.clear_indices = self.indices
                self.steady_visible = False
            self._save()
            return self.status_unlocked()

    def set_preferences(self, enabled, interval, offset, auto_incoming=True,
                        auto_open_seconds=0):
        if type(enabled) is not bool:
            raise ValueError('enabled must be a boolean')
        if type(interval) is not int or not 1 <= interval <= 3600:
            raise ValueError('flash_interval_seconds must be 1 to 3600')
        if type(offset) is not int or not 0 <= offset < self.count:
            raise ValueError('offset must be a valid wormhole LED index')
        if type(auto_incoming) is not bool:
            raise ValueError('auto_incoming must be a boolean')
        if type(auto_open_seconds) is not int or not 0 <= auto_open_seconds <= 3600:
            raise ValueError('auto_open_seconds must be 0 to 3600')
        with self.lock:
            old_indices = self.indices
            self.enabled = enabled
            self.flash_interval = interval
            self.offset = offset
            self.auto_incoming = auto_incoming
            self.auto_open_seconds = auto_open_seconds
            self.next_flash = monotonic() + interval
            self.pulse_until = 0.0
            if not enabled or old_indices != self.indices:
                self.clear_pending = True
                self.clear_indices = old_indices
            self._save()
            return self.status_unlocked()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps({
            'closed': self.closed,
            'offset': self.offset,
            'enabled': self.enabled,
            'auto_incoming': self.auto_incoming,
            'auto_open_seconds': self.auto_open_seconds,
            'flash_interval_seconds': self.flash_interval,
        }) + '\n', encoding='utf-8')
        os.replace(temporary, self.path)

    def overlay(self, pattern):
        """Hide an active wormhole behind a closed Iris and show four red points."""
        with self.lock:
            closed = self.closed and self.enabled
            indices = self.indices
        if (not closed or getattr(self.stargate, 'lamp_mode', False)
                or not self.stargate.wormhole_active):
            return pattern
        result = [(0, 0, 0)] * len(pattern)
        for index in indices:
            result[index] = self.RED
        return result

    def show_closed(self):
        """Replace the shared strip with the four closed-Iris indicators."""
        with self.lock:
            active = self.closed and self.enabled
            indices = self.indices
        if not active or getattr(self.stargate, 'lamp_mode', False):
            return False
        for index in range(self.count):
            self.pixels[index] = (0, 0, 0)
        for index in indices:
            self.pixels[index] = self.RED
        self.pixels.show()
        self.steady_visible = True
        return True

    def replace_kawoosh(self):
        """Block direct-write kawoosh frames while the physical Iris is closed."""
        return self.show_closed()

    def _play_incoming_warning(self):
        """Play the existing SG1 warning once for this incoming connection."""
        audio = getattr(getattr(self.stargate, 'app', None), 'audio', None)
        if audio is None:
            return
        try:
            if not audio.cfg.get('audio_enable'):
                return
            if self.incoming_warning_clip is None:
                self.incoming_warning_clip = audio.init_wav_file(self.INCOMING_WARNING)
            self.incoming_warning_clip.play()
        except Exception as error:  # Audio backends expose implementation-specific errors.
            log = getattr(self.stargate, 'log', None)
            if log is not None:
                log.log('SG1 Iris Lights warning audio failed: {}'.format(error))

    def _incoming_activity(self):
        gate = self.stargate
        return (str(gate.wormhole_active).lower() == 'incoming'
                or bool(gate.address_buffer_incoming)
                or bool(gate.locked_chevrons_incoming))

    def _idle(self):
        gate = self.stargate
        return (not gate.wormhole_active
                and not getattr(gate, 'lamp_mode', False)
                and not gate.address_buffer_outgoing
                and not gate.address_buffer_incoming
                and not gate.locked_chevrons_outgoing
                and not gate.locked_chevrons_incoming)

    def tick(self, now=None):
        """Run from the SG1 main loop, which owns the NeoPixel output."""
        if now is None:
            now = monotonic()
        if getattr(self.stargate, 'lamp_mode', False):
            self.pulse_until = 0.0
            self.next_flash = now + self.flash_interval
            return
        with self.lock:
            closed = self.closed and self.enabled
            indices = self.indices
            clear_pending = self.clear_pending
            clear_indices = self.clear_indices
            self.clear_pending = False
            self.clear_indices = ()
            auto_incoming = self.auto_incoming
            auto_open_seconds = self.auto_open_seconds
            closed_since = self.closed_since
        incoming = self._incoming_activity()
        warning_due = False
        if incoming and not self.incoming_seen:
            self.incoming_seen = True
            if self.enabled and auto_incoming and not self.manual_open_during_incoming:
                self.set_closed(True, manual=False)
                closed = True
                closed_since = self.closed_since
            warning_due = closed and self.enabled
        elif not incoming and self.incoming_seen:
            self.incoming_seen = False
            self.manual_open_during_incoming = False
            if closed and auto_incoming:
                self.set_closed(False, manual=False)
                closed = False
                clear_pending = True
                clear_indices = indices
        if warning_due and self.show_closed():
            self._play_incoming_warning()
        if (closed and auto_open_seconds and closed_since is not None
                and now - closed_since >= auto_open_seconds):
            self.set_closed(False)
            closed = False
            clear_pending = True
            clear_indices = indices
        idle = self._idle()
        if clear_pending and idle:
            for index in clear_indices:
                self.pixels[index] = (0, 0, 0)
            self.pixels.show()
        if closed and not idle and not self.stargate.wormhole_active:
            if not self.steady_visible:
                self.show_closed()
            return
        self.steady_visible = False
        if self.pulse_until:
            if now >= self.pulse_until or not idle or not closed:
                self.pulse_until = 0.0
                if not self.stargate.wormhole_active:
                    for index in indices:
                        self.pixels[index] = (0, 0, 0)
                    self.pixels.show()
            return
        if closed and idle and now >= self.next_flash:
            for index in indices:
                self.pixels[index] = self.RED
            self.pixels.show()
            self.pulse_until = now + self.FLASH_DURATION
            self.next_flash = now + self.flash_interval
