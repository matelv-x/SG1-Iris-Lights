"""Optional physical LED indication of the browser SG1 Iris state."""

import json
import os
from pathlib import Path
from threading import Lock
from time import monotonic


class IrisLights:
    DEFAULT_FLASH_INTERVAL = 3
    FLASH_DURATION = 0.18
    RED = (180, 0, 0)

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
        self.offset = 0
        self.pulse_until = 0.0
        self.clear_pending = False
        self.clear_indices = ()
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
            offset = data.get('offset', 0)
            if type(offset) is int:
                self.offset = offset % self.count
        except (OSError, ValueError, TypeError):
            pass
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
            'flash_interval_seconds': self.flash_interval,
        }

    def status(self):
        with self.lock:
            return self.status_unlocked()

    def set_closed(self, closed):
        if type(closed) is not bool:
            raise ValueError('closed must be a boolean')
        with self.lock:
            if self.closed == closed:
                return self.status_unlocked()
            self.closed = closed
            self.next_flash = monotonic() + self.flash_interval
            self._save()
            return self.status_unlocked()

    def set_preferences(self, enabled, interval, offset):
        if type(enabled) is not bool:
            raise ValueError('enabled must be a boolean')
        if type(interval) is not int or not 1 <= interval <= 3600:
            raise ValueError('flash_interval_seconds must be 1 to 3600')
        if type(offset) is not int or not 0 <= offset < self.count:
            raise ValueError('offset must be a valid wormhole LED index')
        with self.lock:
            old_indices = self.indices
            self.enabled = enabled
            self.flash_interval = interval
            self.offset = offset
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
            'flash_interval_seconds': self.flash_interval,
        }) + '\n', encoding='utf-8')
        os.replace(temporary, self.path)

    def overlay(self, pattern):
        """Composite four red points over an active, nonempty wormhole frame."""
        with self.lock:
            closed = self.closed and self.enabled
            indices = self.indices
        if (not closed or getattr(self.stargate, 'lamp_mode', False)
                or not self.stargate.wormhole_active
                or not any(any(rgb) for rgb in pattern)):
            return pattern
        result = list(pattern)
        for index in indices:
            result[index] = self.RED
        return result

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
        idle = self._idle()
        if clear_pending and idle:
            for index in clear_indices:
                self.pixels[index] = (0, 0, 0)
            self.pixels.show()
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
