import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('iris_lights_installer', ROOT / 'install.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


FILES = {
    'classes/StargateMilkyWay/stargate.py': '''from wormhole_manager import WormholeManager

class Stargate:
    def setup(self):
        self.wh_manager.initialize_animation_manager()

    def loop(self):
        while True:
            self.schedule.run_pending() # Run any scheduled items
''',
    'classes/StargateMilkyWay/wormhole_animation_manager.py': '''from time import sleep

class Animation:
    def animate_kawoosh(self):
        self.pixels.fill((1, 2, 3))
        self.pixels.show()

    def apply(self, pattern):
        for index, led_state in enumerate(pattern):
            self.pixels[index] = led_state
''',
    'classes/StargateMilkyWay/wormhole_manager.py': '''class Wormhole:
    def close(self):
        self.log.log(f'Disengaged Wormhole after {timedelta(seconds=int(time() - self.open_time))}')
''',
    'classes/web_server.py': '''class Handler:
    def get(self, request_path):
        try:
            if request_path == "/get/is_alive":
                data = {"is_alive": True}
            return data
        except Exception:
            return None

    def post(self, data):
        try:
            ##### DO ACTION HANDLERS BELOW ####
            return data
        except Exception:
            return None
''',
    'web/config.htm': '''<html><body><main>
    </main><!-- /.container -->
  </body></html>
''',
    'web/retro/dial.html': '''<html><body>
    <!-- SG1 IRIS ADDON JS END -->
</body></html>
''',
    'web/retro/dial9.html': '''<html><body>
    <!-- SG1 IRIS ADDON JS END -->
</body></html>
''',
    'web/retro/js/iris.js': '/* SG1 IRIS ADDON ASSET */\n',
    'web/retro/css/iris.css': '/* SG1 IRIS ADDON ASSET */\n',
}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name) / 'sg1_v4'
        for relative, content in FILES.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        (self.root / 'web/js').mkdir(exist_ok=True)
        self.original = {name: (self.root / name).read_bytes() for name in FILES}

    def tearDown(self):
        self.temp.cleanup()

    def test_install_update_and_surgical_uninstall(self):
        INSTALLER.install(self.root)
        self.assertTrue((self.root / INSTALLER.STATE).is_file())
        self.assertIn('SG1_IRIS_LIGHTS_BEGIN',
                      (self.root / 'classes/web_server.py').read_text(encoding='utf-8'))
        stargate = (self.root / 'classes/StargateMilkyWay/stargate.py').read_text(encoding='utf-8')
        self.assertLess(stargate.index('self.iris_lights = IrisLights(self)'),
                        stargate.index('self.wh_manager.initialize_animation_manager()'))
        self.assertTrue((self.root / 'classes/StargateMilkyWay/iris_lights.py').is_file())
        animation = (self.root / 'classes/StargateMilkyWay/wormhole_animation_manager.py').read_text(encoding='utf-8')
        self.assertIn('if self.stargate.iris_lights.replace_kawoosh():', animation)
        settings = self.root / 'config/iris-lights.json'
        settings.parent.mkdir(parents=True)
        settings.write_text('{"enabled": true, "offset": 7}\n', encoding='utf-8')

        INSTALLER.install(self.root, update=True)
        self.assertTrue(settings.is_file())
        INSTALLER.uninstall(self.root, dry_run=True)
        INSTALLER.uninstall(self.root)

        for name, content in self.original.items():
            self.assertEqual((self.root / name).read_bytes(), content, name)
        self.assertTrue(settings.is_file())
        self.assertFalse((self.root / 'classes/StargateMilkyWay/iris_lights.py').exists())

    def test_requires_sg1_iris(self):
        (self.root / 'web/retro/js/iris.js').unlink()
        with self.assertRaisesRegex(ValueError, 'SG1 Iris must be installed'):
            INSTALLER.install(self.root)

    def test_refuses_to_uninstall_over_later_changes(self):
        INSTALLER.install(self.root)
        path = self.root / 'web/retro/dial.html'
        path.write_text(path.read_text(encoding='utf-8') + '<!-- later change -->\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'later changes'):
            INSTALLER.uninstall(self.root)

    def test_stellar_archive_post_anchor_is_supported(self):
        path = self.root / 'classes/web_server.py'
        text = path.read_text(encoding='utf-8').replace(
            '            ##### DO ACTION HANDLERS BELOW ####\n',
            '                                                                                    # STELLAR_ARCHIVE_MAINTENANCE_POST_BEGIN\n'
            '            if self.path == "/do/stellar_archive_update":\n'
            '                return\n'
            '            # STELLAR_ARCHIVE_MAINTENANCE_POST_END\n',
        )
        path.write_text(text, encoding='utf-8')
        original = path.read_bytes()

        INSTALLER.install(self.root)
        self.assertIn('SG1_IRIS_LIGHTS_BEGIN', path.read_text(encoding='utf-8'))
        INSTALLER.uninstall(self.root)
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
