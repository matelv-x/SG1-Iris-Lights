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


class IrisLightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        (Path(self.temp.name) / 'config').mkdir()
        self.gate = Gate(self.temp.name)
        self.lights = IrisLights(self.gate)

    def tearDown(self):
        self.temp.cleanup()

    def test_opt_in_overlay_and_lamp_priority(self):
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


if __name__ == '__main__':
    unittest.main()
