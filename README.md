# SG1 Iris Lights

Optional physical LED companion for
[SG1 Iris](https://github.com/matelv-x/SG1-Iris) on StargateProject SG1 v4.
It maps the browser Iris state to four red pixels on the existing wormhole LED
strip. No additional LED hardware is required.

The feature is installed **off by default**. The SG1 `config.htm` page controls:

- enable or disable;
- idle flash interval from 1 to 3600 seconds;
- first-pixel calibration offset, with the four calculated LED indices shown.

When the Iris is closed, four red pixels flash while the gate is idle and stay
red over an active wormhole animation. The indicator opens after disconnect.
Lamp Mode has priority and suspends Iris Lights while it owns the strip.

## Requirements

- SG1 v4 in `/home/pi/sg1_v4`;
- Retro;
- SG1 Iris installed first;
- at least four wormhole LEDs.

Stellar Archive is not required to run Iris Lights. Stellar Archive 1.5.31 or
newer is recommended for dependency-aware installation and automatic safe
reapplication after compatible SG1 Iris updates.

## Install

```bash
cd /home/pi
git clone https://github.com/matelv-x/SG1-Iris-Lights.git
cd SG1-Iris-Lights
chmod +x install.sh restore.sh
python3 install.py --target /home/pi/sg1_v4 --dry-run
sudo ./install.sh --target /home/pi/sg1_v4
sudo systemctl restart stargate.service
```

The preferred installation path is Stellar Archive's add-on catalogue. It
checks that SG1 Iris is installed before allowing Iris Lights to install.

## Update

```bash
sudo ./install.sh --target /home/pi/sg1_v4 --update
sudo systemctl restart stargate.service
```

With dependency-aware Stellar Archive, updating SG1 Iris temporarily removes
Iris Lights, updates Iris, then reapplies the same verified Iris Lights package.
If reapplication is incompatible, SG1 Iris remains updated and operational,
while Iris Lights remains safely absent and reports the failure.

## Uninstall

```bash
sudo ./restore.sh --target /home/pi/sg1_v4 --dry-run
sudo ./restore.sh --target /home/pi/sg1_v4
sudo systemctl restart stargate.service
```

Uninstall verifies the installed and backup hashes before changing anything.
It preserves `config/iris-lights.json` so settings survive reinstallations.

## Ownership and compatibility

SG1 Iris Lights owns only blocks marked `SG1_IRIS_LIGHTS_BEGIN` /
`SG1_IRIS_LIGHTS_END` and its three added runtime assets. It refuses to replace
unknown files or overwrite later edits. Its backend changes are recorded in a
checksum manifest below `web/.sg1-iris-lights/` and exact originals are retained
below `web/backups/`.

The original physical indicator reference patch and behavior were contributed
by Jan. This official companion packaging, dependency contract, calibration
setting, update lifecycle and Stellar Archive integration are maintained by
matelv-x.

## Hardware status

The installer and logic can be validated without hardware. Pixel placement,
brightness and interaction with the physical strip must still be accepted on an
unmodified gate before the first public release is marked hardware-verified.
