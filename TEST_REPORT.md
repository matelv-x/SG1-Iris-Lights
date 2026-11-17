# SG1 Iris Lights 1.0.0 validation

Date: 2026-11-16 (America/Chicago)

## Tested source revisions

- StargateProject SG1 v4: `7307664670a2f60c158b583a0abc5b922fb549ff`
- polklabs Stargate Retro: `8531100befa71c72e9e27fb1104445a5bc0b96c8`
- matelv-x SG1 Iris: `b105ae45c5b14ff624963d85252c443fb09006b5`
- Stellar Archive base: `336ddf86e78126cbee67a2571cb7ece191ff339b`

## Passed checks

- Ten hardware-free Iris Lights unit and installer tests, including both the
  clean SG1 v4 and Stellar Archive-managed `web_server.py` layouts.
- Install dry-run, install, Python compilation, checksum-verified uninstall
  dry-run, and uninstall on a newly assembled SG1 v4 + Retro + SG1 Iris tree.
- SG1 Iris update followed by successful Iris Lights reapplication and another
  verified uninstall dry-run.
- A first controlled start on gate 200 exposed an initialization-order fault;
  checksum rollback restored the gate, and the installer now creates Iris
  Lights before the animation manager's initial strip-clear callback.
- Stellar Archive dependency, manifest, dirty-package rejection, browser,
  installer, original-only, and navigation tests.

## Not yet verified

- No files were deployed to or executed on an unmodified physical Stargate.
- The four LED positions, brightness, and appearance over every physical
  wormhole animation still require acceptance on a 122-pixel gate.
- Until that acceptance is complete, version 1.0.0 is software-validated but
  not hardware-verified.
