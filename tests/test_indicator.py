from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from iris_lights import IrisLights  # noqa: E402


class Pixels:
    def __init__(self, count):
        self.colors = [(0, 0, 0)] * count
        self.shows = 0

    def __setitem__(self, index, color):
        self.colors[index] = color

    def show(self):
        self.shows += 1


class WarningClip:
    def __init__(self):
        self.plays = 0

    def play(self):
        self.plays += 1


class Audio:
    def __init__(self):
        self.cfg = {'audio_enable': True}
        self.clip = WarningClip()
        self.loaded = []

    def init_wav_file(self, path):
        self.loaded.append(path)
        return self.clip


class Gate:
    def __init__(self, path, count=122):
        self.base_path = path
        self.wormhole_active = False
        self.lamp_mode = False
        self.address_buffer_outgoing = []
        self.address_buffer_incoming = []
        self.locked_chevrons_outgoing = 0
        self.locked_chevrons_incoming = 0
        self.wh_manager = type('WH', (), {'pixels': Pixels(count), 'tot_leds': count})()
        self.app = type('App', (), {'audio': Audio()})()


class IrisLightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        (Path(self.temp.name) / 'config').mkdir()
        self.gate = Gate(self.temp.name)
        self.lights = IrisLights(self.gate)

    def tearDown(self):
        self.temp.cleanup()

    def test_closed_iris_blocks_wormhole_and_lamp_has_priority(self):
        self.assertFalse(self.lights.status()['enabled'])
        self.assertEqual(self.lights.indices, (0, 30, 61, 91))
        self.lights.set_closed(True)
        self.gate.wormhole_active = True
        blue = [(0, 0, 70)] * 122
        self.assertEqual(self.lights.overlay(blue), blue)
        state = self.lights.set_preferences(True, 3, 4)
        self.assertEqual(state['indices'], (4, 34, 65, 95))
        result = self.lights.overlay(blue)
        self.assertEqual([i for i, rgb in enumerate(result) if rgb == (180, 0, 0)],
                         [4, 34, 65, 95])
        self.assertTrue(all(rgb == (0, 0, 0) for i, rgb in enumerate(result)
                            if i not in (4, 34, 65, 95)))
        self.gate.lamp_mode = True
        self.assertEqual(self.lights.overlay(blue), blue)

    def test_idle_flash_and_persistence(self):
        self.lights.set_closed(True)
        self.lights.set_preferences(True, 5, 9)
        due = self.lights.next_flash
        self.lights.tick(due)
        self.assertEqual(self.gate.wh_manager.pixels.colors[9], (180, 0, 0))
        self.lights.tick(due + 0.2)
        self.assertEqual(self.gate.wh_manager.pixels.colors[9], (0, 0, 0))
        state = IrisLights(self.gate).status()
        self.assertTrue(state['enabled'])
        self.assertEqual(state['flash_interval_seconds'], 5)
        self.assertEqual(state['offset'], 9)

    def test_invalid_offset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'offset'):
            self.lights.set_preferences(True, 3, 122)

    def test_lamp_mode_suspends_idle_flash_without_writing_strip(self):
        self.lights.set_closed(True)
        self.lights.set_preferences(True, 3, 0)
        due = self.lights.next_flash
        self.gate.lamp_mode = True
        self.lights.tick(due)
        self.assertEqual(self.gate.wh_manager.pixels.shows, 0)
        self.assertEqual(self.gate.wh_manager.pixels.colors[0], (0, 0, 0))
        self.assertGreater(self.lights.next_flash, due)

    def test_offset_change_clears_previous_idle_pixels(self):
        self.lights.set_closed(True)
        self.lights.set_preferences(True, 3, 0)
        due = self.lights.next_flash
        self.lights.tick(due)
        self.assertEqual(self.gate.wh_manager.pixels.colors[0], (180, 0, 0))
        self.lights.set_preferences(True, 3, 5)
        self.lights.tick(due + 0.01)
        self.assertEqual(self.gate.wh_manager.pixels.colors[0], (0, 0, 0))

    def test_too_few_pixels_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'at least four'):
            IrisLights(Gate(self.temp.name, count=3))

    def test_headless_incoming_closes_and_disconnect_opens(self):
        self.lights.set_preferences(True, 3, 0, True, 0)
        self.gate.address_buffer_incoming = [14]
        self.lights.tick(100.0)
        self.assertTrue(self.lights.status()['closed'])
        self.assertEqual(self.gate.wh_manager.pixels.colors[0], (180, 0, 0))
        self.gate.address_buffer_incoming = []
        self.lights.tick(101.0)
        self.assertFalse(self.lights.status()['closed'])

    def test_incoming_warning_plays_once_after_red_indicators_appear(self):
        self.lights.set_preferences(True, 3, 0, True, 0)
        self.gate.address_buffer_incoming = [14]
        self.lights.tick(100.0)
        self.assertEqual(self.gate.wh_manager.pixels.colors[0], (180, 0, 0))
        self.assertEqual(self.gate.app.audio.loaded,
                         ['/audio_clips/unsceduald offworld activation.wav'])
        self.assertEqual(self.gate.app.audio.clip.plays, 1)
        self.lights.tick(101.0)
        self.assertEqual(self.gate.app.audio.clip.plays, 1)

    def test_warning_is_silent_when_four_led_indicator_is_disabled(self):
        self.gate.address_buffer_incoming = [14]
        self.lights.tick(100.0)
        self.assertEqual(self.gate.app.audio.clip.plays, 0)

    def test_direct_kawoosh_is_replaced_by_four_red_pixels(self):
        self.lights.set_preferences(True, 3, 4, True, 0)
        self.lights.set_closed(True)
        self.gate.wh_manager.pixels.colors = [(10, 20, 30)] * 122
        self.assertTrue(self.lights.replace_kawoosh())
        expected = {4, 34, 65, 95}
        self.assertEqual({index for index, color in enumerate(
            self.gate.wh_manager.pixels.colors) if color == (180, 0, 0)}, expected)
        self.assertTrue(all(color == (0, 0, 0) for index, color in enumerate(
            self.gate.wh_manager.pixels.colors) if index not in expected))

    def test_manual_open_during_incoming_is_not_immediately_reclosed(self):
        self.lights.set_preferences(True, 3, 0, True, 0)
        self.gate.wormhole_active = 'incoming'
        self.lights.tick(100.0)
        self.lights.set_closed(False)
        self.lights.tick(101.0)
        self.assertFalse(self.lights.status()['closed'])

    def test_optional_auto_open_timer(self):
        self.lights.set_preferences(True, 3, 0, False, 5)
        self.lights.set_closed(True)
        due = self.lights.closed_since
        self.lights.tick(due + 4.9)
        self.assertTrue(self.lights.status()['closed'])
        self.lights.tick(due + 5.0)
        self.assertFalse(self.lights.status()['closed'])

    def test_new_preferences_persist(self):
        self.lights.set_preferences(True, 4, 2, False, 45)
        state = IrisLights(self.gate).status()
        self.assertFalse(state['auto_incoming'])
        self.assertEqual(state['auto_open_seconds'], 45)

    def test_invalid_auto_open_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'auto_open_seconds'):
            self.lights.set_preferences(True, 3, 0, True, 3601)


if __name__ == '__main__':
    unittest.main()
