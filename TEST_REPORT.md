# SG1 Iris Lights 1.1.0 validation

Date: 2026-11-16 (America/Chicago)

## Tested source revisions

- StargateProject SG1 v4: `7307664670a2f60c158b583a0abc5b922fb549ff`
- polklabs Stargate Retro: `8531100befa71c72e9e27fb1104445a5bc0b96c8`
- matelv-x SG1 Iris: `b105ae45c5b14ff624963d85252c443fb09006b5`
- Stellar Archive base: `336ddf86e78126cbee67a2571cb7ece191ff339b`

## Passed checks

- Fifteen hardware-free Iris Lights unit and installer tests, including both the
  clean SG1 v4 and Stellar Archive-managed `web_server.py` layouts.
- Headless incoming auto-close, manual incoming override, optional auto-open,
  preference persistence, Lamp Mode priority, and closed-Iris wormhole masking.
- Install dry-run, install, Python compilation, checksum-verified uninstall
  dry-run, and uninstall on a newly assembled SG1 v4 + Retro + SG1 Iris tree.
- SG1 Iris update followed by successful Iris Lights reapplication and another
  verified uninstall dry-run.
- A first controlled start on gate 200 exposed an initialization-order fault;
  checksum rollback restored the gate, and the installer now creates Iris
  Lights before the animation manager's initial strip-clear callback.
- Stellar Archive dependency, manifest, dirty-package rejection, browser,
  installer, original-only, and navigation tests.

## Physical validation completed for 1.0.0

- Installed on gate 200 with its 122-pixel wormhole strip. The owner confirmed
  the four red positions were physically visible. A real Seed Ship 115 to gate
  200 incoming connection established successfully and the 1.0.0 overlay was
  exercised over the active wormhole.

## Pending physical validation for 1.1.0

- Confirm automatic headless close on a new real incoming connection.
- Confirm that a closed Iris suppresses the physical kawoosh and wormhole strip
  while leaving only the four red pixels visible.
- Confirm automatic open and normal strip restoration after disconnect.
