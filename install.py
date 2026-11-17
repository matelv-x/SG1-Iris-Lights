#!/usr/bin/env python3
"""Surgical installer for the optional SG1 Iris Lights companion add-on."""

import argparse
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil


SOURCE = Path(__file__).resolve().parent
STATE = Path('web/.sg1-iris-lights/manifest.json')
VERSION = (SOURCE / 'VERSION').read_text(encoding='utf-8').strip()
MARKER = 'SG1_IRIS_LIGHTS_BEGIN'


def require_once(text, anchor, name):
    count = text.count(anchor)
    if count != 1:
        raise ValueError('{}: expected one insertion point, found {}'.format(name, count))


def insert(text, anchor, addition, name, before=False):
    require_once(text, anchor, name)
    replacement = addition + anchor if before else anchor + addition
    return text.replace(anchor, replacement, 1)


def insert_one_of(text, anchors, addition, name, before=False):
    """Insert at exactly one supported layout variant without guessing."""
    matches = [(anchor, text.count(anchor)) for anchor in anchors if text.count(anchor)]
    if len(matches) != 1 or matches[0][1] != 1:
        detail = ', '.join('{}={}'.format(index + 1, text.count(anchor))
                           for index, anchor in enumerate(anchors))
        raise ValueError('{}: expected one supported insertion point, found {}'.format(
            name, detail))
    return insert(text, matches[0][0], addition, name, before=before)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_prerequisites(root):
    iris_js = root / 'web/retro/js/iris.js'
    iris_css = root / 'web/retro/css/iris.css'
    if not iris_js.is_file() or not iris_css.is_file():
        raise ValueError('SG1 Iris must be installed before SG1 Iris Lights')
    if 'SG1 IRIS ADDON ASSET' not in iris_js.read_text(encoding='utf-8', errors='replace'):
        raise ValueError('the installed web/retro/js/iris.js is not a supported SG1 Iris asset')
    if not (root / 'web/js').is_dir():
        raise ValueError('SG1 web/js folder is missing')


def changed_files(root):
    validate_prerequisites(root)
    paths = [
        'classes/StargateMilkyWay/stargate.py',
        'classes/StargateMilkyWay/wormhole_animation_manager.py',
        'classes/StargateMilkyWay/wormhole_manager.py',
        'classes/web_server.py',
        'web/config.htm',
        'web/retro/dial.html',
        'web/retro/dial9.html',
    ]
    old = {}
    for name in paths:
        path = root / name
        if not path.is_file():
            raise ValueError('Missing {}'.format(name))
        old[name] = path.read_text(encoding='utf-8')
    if any(MARKER in text for text in old.values()):
        raise ValueError('SG1 Iris Lights is already or partially installed')
    if any('PHYSICAL_IRIS_INDICATOR_BEGIN' in text for text in old.values()):
        raise ValueError('remove the legacy physical iris indicator patch before installing SG1 Iris Lights')

    new = dict(old)
    name = 'classes/StargateMilkyWay/stargate.py'
    text = new[name]
    text = insert(text, 'from wormhole_manager import WormholeManager\n',
                  '# SG1_IRIS_LIGHTS_BEGIN\nfrom iris_lights import IrisLights\n'
                  '# SG1_IRIS_LIGHTS_END\n', name)
    text = insert(text, '        self.wh_manager.initialize_animation_manager()\n',
                  '        # SG1_IRIS_LIGHTS_BEGIN\n'
                  '        self.iris_lights = IrisLights(self)\n'
                  '        # SG1_IRIS_LIGHTS_END\n', name, before=True)
    text = insert(text, '            self.schedule.run_pending() # Run any scheduled items\n',
                  '            # SG1_IRIS_LIGHTS_BEGIN\n'
                  '            self.iris_lights.tick()\n'
                  '            # SG1_IRIS_LIGHTS_END\n', name, before=True)
    new[name] = text

    name = 'classes/StargateMilkyWay/wormhole_animation_manager.py'
    new[name] = insert(new[name], '        for index, led_state in enumerate(pattern):\n',
                       '        # SG1_IRIS_LIGHTS_BEGIN\n'
                       '        pattern = self.stargate.iris_lights.overlay(pattern)\n'
                       '        # SG1_IRIS_LIGHTS_END\n', name, before=True)

    name = 'classes/StargateMilkyWay/wormhole_manager.py'
    anchor = "        self.log.log(f'Disengaged Wormhole after {timedelta(seconds=int(time() - self.open_time))}')"
    new[name] = insert(new[name], anchor,
                       '        # SG1_IRIS_LIGHTS_BEGIN\n'
                       '        self.stargate.iris_lights.set_closed(False)\n'
                       '        # SG1_IRIS_LIGHTS_END\n', name, before=True)

    name = 'classes/web_server.py'
    text = new[name]
    text = insert(text, '            if request_path == "/get/is_alive":\n',
                  '            # SG1_IRIS_LIGHTS_BEGIN\n'
                  '            if request_path == "/get/iris_lights":\n'
                  '                data = self.stargate.iris_lights.status()\n'
                  '            else:\n'
                  '                data = None\n'
                  '            # SG1_IRIS_LIGHTS_END\n\n', name, before=True)
    text = text.replace(
        '            else:\n                data = None\n'
        '            # SG1_IRIS_LIGHTS_END\n\n'
        '            if request_path == "/get/is_alive":\n',
        '            # SG1_IRIS_LIGHTS_END\n\n'
        '            elif request_path == "/get/is_alive":\n', 1)
    text = insert_one_of(text, (
                  '            ##### DO ACTION HANDLERS BELOW ####\n',
                  '                                                                                    # STELLAR_ARCHIVE_MAINTENANCE_POST_BEGIN\n',
                  ),
                  '            # SG1_IRIS_LIGHTS_BEGIN\n'
                  '            if self.path == "/update/iris_lights":\n'
                  '                try:\n'
                  '                    state = self.stargate.iris_lights.set_closed(data.get("closed"))\n'
                  '                    self.send_json_response({"success": True, **state})\n'
                  '                except ValueError as error:\n'
                  '                    self.send_json_response({"success": False, "message": str(error)})\n'
                  '                return\n'
                  '            if self.path == "/update/iris_lights_preferences":\n'
                  '                try:\n'
                  '                    state = self.stargate.iris_lights.set_preferences(\n'
                  '                        data.get("enabled"), data.get("flash_interval_seconds"),\n'
                  '                        data.get("offset"))\n'
                  '                    self.send_json_response({"success": True, **state})\n'
                  '                except ValueError as error:\n'
                  '                    self.send_json_response({"success": False, "message": str(error)})\n'
                  '                return\n'
                  '            # SG1_IRIS_LIGHTS_END\n\n', name, before=True)
    new[name] = text

    name = 'web/config.htm'
    panel = '''
      <!-- SG1_IRIS_LIGHTS_BEGIN -->
      <section class="card mt-4 mb-4" aria-labelledby="iris-lights-heading">
        <div class="card-body">
          <h2 class="h5" id="iris-lights-heading">SG1 Iris Lights</h2>
          <p>Use four red pixels of the wormhole LED strip to show a closed iris.
             Iris Lights pauses while Lamp Mode controls the strip.</p>
          <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="iris-lights-enabled">
            <label class="form-check-label" for="iris-lights-enabled">
              Enable four red iris LEDs
            </label>
          </div>
          <label class="form-label" for="iris-lights-interval">
            Idle flash interval (seconds)
          </label>
          <input class="form-control" type="number" id="iris-lights-interval"
                 min="1" max="3600" step="1">
          <label class="form-label mt-3" for="iris-lights-offset">
            First LED position (calibration offset)
          </label>
          <input class="form-control" type="number" id="iris-lights-offset"
                 min="0" step="1">
          <p id="iris-lights-positions" class="form-text"></p>
          <p class="form-text">During an active wormhole, the four pixels remain red.</p>
          <button class="btn btn-primary" type="button" id="iris-lights-save">
            Save Iris Lights settings
          </button>
          <span id="iris-lights-message" role="status" class="ms-2"></span>
        </div>
      </section>
      <!-- SG1_IRIS_LIGHTS_END -->
'''
    text = insert(new[name], '    </main><!-- /.container -->', panel, name, before=True)
    text = insert(text, '  </body>',
                  '    <!-- SG1_IRIS_LIGHTS_BEGIN -->\n'
                  '    <script src="/js/iris-lights-settings.js"></script>\n'
                  '    <!-- SG1_IRIS_LIGHTS_END -->\n', name, before=True)
    new[name] = text

    for name in ('web/retro/dial.html', 'web/retro/dial9.html'):
        new[name] = insert(new[name], '    <!-- SG1 IRIS ADDON JS END -->',
                           '\n    <!-- SG1_IRIS_LIGHTS_BEGIN -->\n'
                           '    <script type="module" src="js/iris-lights.js"></script>\n'
                           '    <!-- SG1_IRIS_LIGHTS_END -->', name)

    for name, content in new.items():
        if name.endswith('.py'):
            ast.parse(content, filename=name)
    return old, new


def additions():
    return {
        'classes/StargateMilkyWay/iris_lights.py': SOURCE / 'src/iris_lights.py',
        'web/retro/js/iris-lights.js': SOURCE / 'src/iris-lights.js',
        'web/js/iris-lights-settings.js': SOURCE / 'src/iris-lights-settings.js',
    }


def install(root, dry_run=False, update=False):
    state_file = root / STATE
    if state_file.exists():
        if not update:
            raise ValueError('SG1 Iris Lights is already installed; use --update')
        uninstall(root, dry_run=dry_run)
        if dry_run:
            print('Update dry run complete; the installed version can be removed safely.')
            return
    old, new = changed_files(root)
    added = additions()
    for name in added:
        if (root / name).exists():
            raise ValueError('Refusing to replace existing {}'.format(name))
    print('Will edit:', *new, sep='\n  ')
    print('Will add:', *added, sep='\n  ')
    if dry_run:
        print('Dry run complete; no files changed.')
        return

    backup_base = root / 'web/backups' / ('sg1-iris-lights-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup = backup_base
    suffix = 1
    while backup.exists():
        backup = Path(str(backup_base) + '-{}'.format(suffix))
        suffix += 1
    manifest = {'schema': 1, 'version': VERSION, 'backup': str(backup), 'modified': {}, 'added': {}}
    for name in old:
        destination = backup / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, destination)
        manifest['modified'][name] = {
            'before': digest((root / name).read_bytes()),
            'after': digest(new[name].encode('utf-8')),
        }
    for name, source in added.items():
        manifest['added'][name] = digest(source.read_bytes())
    try:
        for name, content in new.items():
            path = root / name
            temporary = path.with_suffix(path.suffix + '.sg1-iris-lights-tmp')
            temporary.write_text(content, encoding='utf-8')
            os.replace(temporary, path)
        for name, source in added.items():
            shutil.copy2(source, root / name)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    except Exception:
        for name in old:
            shutil.copy2(backup / name, root / name)
        for name in added:
            (root / name).unlink(missing_ok=True)
        raise
    print('Installed SG1 Iris Lights {}. Backup: {}'.format(VERSION, backup))


def uninstall(root, dry_run=False):
    state_file = root / STATE
    if not state_file.is_file():
        raise ValueError('SG1 Iris Lights is not installed by this installer')
    manifest = json.loads(state_file.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported SG1 Iris Lights install state')
    backup = Path(manifest['backup'])
    for name, hashes in manifest['modified'].items():
        if digest((root / name).read_bytes()) != hashes['after']:
            raise ValueError('Refusing to overwrite later changes in {}'.format(name))
        if digest((backup / name).read_bytes()) != hashes['before']:
            raise ValueError('Backup checksum mismatch in {}'.format(name))
    for name, expected in manifest['added'].items():
        if digest((root / name).read_bytes()) != expected:
            raise ValueError('Refusing to remove later changes in {}'.format(name))
    if dry_run:
        print('Uninstall dry run complete; no files changed.')
        return
    for name in manifest['modified']:
        shutil.copy2(backup / name, root / name)
    for name in manifest['added']:
        (root / name).unlink()
    state_file.unlink()
    print('Removed SG1 Iris Lights. Preferences remain in config/iris-lights.json.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path('/home/pi/sg1_v4'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    root = args.target.resolve()
    try:
        if args.uninstall:
            uninstall(root, args.dry_run)
        else:
            install(root, args.dry_run, args.update)
    except (OSError, ValueError, SyntaxError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, 'ERROR: {}\n'.format(error))


if __name__ == '__main__':
    main()
