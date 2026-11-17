# Changelog

## 1.2.0

- Blocks the direct-write kawoosh animation before its first frame when the
  physical Iris indicator is active, so only the four red pixels remain.
- Plays the existing `Unscheduled Offworld Activation` SoundFX clip once when
  the first four-red-pixel indication appears for an incoming connection.
- Keeps the warning headless and server-side, and respects the SG1 audio-enable
  setting and Lamp Mode priority.
- Updates and uninstalls now remove only owned marker blocks from shared files
  that Stellar Archive or another compatible add-on changed later.

## 1.1.0

- Added headless automatic Iris close for incoming connections.
- Added physical Iris ON/OFF and an optional automatic-open timer to config.
- A closed Iris now blocks kawoosh and wormhole strip illumination, leaving
  only the four red Iris pixels visible.
- Manual opening during an incoming connection is respected until disconnect.

## 1.0.0

- Packages Jan's optional four-pixel physical iris indicator as the separate
  official SG1 Iris Lights companion add-on.
- Keeps the feature disabled by default and adds an idle flash interval plus
  first-pixel calibration on the SG1 configuration page.
- Gives Lamp Mode priority over the shared wormhole strip.
- Adds a surgical checksum-verified installer and uninstaller which preserve
  user preferences.
- Declares the SG1 Iris dependency and safe dependency-reapply contract used by
  Stellar Archive 1.5.31 and newer.
