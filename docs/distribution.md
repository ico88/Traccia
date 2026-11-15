# Distribution inventory

Traccia's own code is **GPL-3.0-or-later**, as confirmed by the project owner. [Full license](../LICENSE). Models are downloaded separately; they are not included in the installer.

The Mac package carries an inventory of the exact Python build environment and the license/notice files supplied by installed distributions in `third-party-notices/`. The inventory deliberately includes build/test dependencies as an upper bound; it is not a claim that every installed package is bundled. Native notices are in `runtimes/licenses/`.

| Component | Distribution treatment |
|---|---|
| Traccia | GPL-3.0-or-later; tagged application source on GitHub |
| Mutagen 1.48.1 | GPL-2.0-or-later; exact source archive and license included with release sources |
| PyInstaller 6.22.3 / bootloader | GPL with bootloader exception; source and notices included |
| FFmpeg 9.0 | Audio-only custom build, LGPL-2.1-or-later, without `--enable-gpl` or `--enable-nonfree`; exact source archive and build commands supplied |
| LAME 3.100 | Static audio codec in FFmpeg, upstream LGPL terms; exact source archive and license supplied |
| Python 3.11.9 | PSF license text included |
| whisper.cpp / llama.cpp | Pinned commits and MIT notices retained by runtime setup |
| sherpa-onnx / remaining Python libraries | Their upstream notices and metadata are retained; see package inventory |

`build_ffmpeg.py` verifies source SHA-256, compiles the required audio formats/filters and retains exact source archives plus configuration commands. The full video binary supplied by the imageio-ffmpeg wheel is excluded from Mac builds through a dedicated PyInstaller hook. The application invokes FFmpeg as a separate executable; explicit runtime overrides remain possible.

The release provides `Traccia-0.10-Corresponding-Sources.zip` next to the DMG, containing FFmpeg/LAME/Mutagen/PyInstaller source archives, notices and build instructions. Source archives are unmodified; configuration is recorded in `build-commands.json`. Rebuilding requires the documented compiler/toolchain, Python dependencies and pinned native runtime sources.

Builds are ad hoc signed for development. Developer ID signing, notarization, automatic updates and verification on a clean second Mac remain pending. No quarantine/security bypass is part of the installation instructions.

License provenance comes from the actual bundled FFmpeg `-L` / `-buildconf`, distribution metadata and included upstream texts. This inventory is reproducible packaging documentation, not a claim of formal legal certification.
