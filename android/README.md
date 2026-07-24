# FileForge Android

A small Compose app that runs the **real FileForge engine on-device** via
[Chaquopy](https://chaquo.com/chaquopy/) (embedded CPython). It installs the
published `pyfile-convert` package at build time, so the app and the CLI share
exactly the same conversion code. FileForge is free — no license, no upsells.

## What it does

**Pick a file → choose an output format → convert → share.** The Kotlin UI is
deliberately thin; all conversion logic lives in Python (`ffbridge.py`, which
calls `fileforge`), so new formats added to the engine appear in the app with
no Kotlin changes.

```
MainActivity.kt ──callAttr──> ffbridge.py ──> fileforge.core.registry
   (Compose UI)                (bridge)          (shared engine)
```

## Project layout

```
android/
├── settings.gradle.kts
├── build.gradle.kts                 # plugin versions (AGP, Kotlin, Chaquopy)
├── gradle.properties
└── app/
    ├── build.gradle.kts             # Chaquopy pip { install("pyfile-convert") }
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/k1lllagt/fileforge/MainActivity.kt
        ├── python/ffbridge.py       # Kotlin <-> engine bridge
        └── res/…                    # strings, theme, FileProvider paths
```

## Build

**Requirements:** Android Studio (Hedgehog+), JDK 17, Android SDK 34.

Chaquopy also needs a desktop Python **3.8–3.12** available for the build
(it uses it to resolve/download the requirements). Point it at yours if it
isn't auto-detected, e.g. in `app/build.gradle.kts`:

```kotlin
// android { defaultConfig { python { buildPython("/usr/bin/python3.12") } } }
```

Then:

```bash
# Open the android/ folder in Android Studio and let it sync + generate the
# Gradle wrapper, OR from a machine with Gradle installed:
cd android
gradle wrapper            # one-time: creates ./gradlew and the wrapper jar
./gradlew assembleDebug   # builds app/build/outputs/apk/debug/app-debug.apk
```

Install on a device:

```bash
./gradlew installDebug
# or: adb install app/build/outputs/apk/debug/app-debug.apk
```

## Notes

- **First build is slow** — Chaquopy downloads CPython + the requirements for
  each ABI. Subsequent builds are cached.
- **ABIs:** `arm64-v8a` (modern phones), `armeabi-v7a` (older), `x86_64`
  (emulator). Trim the list in `build.gradle.kts` to shrink the APK.
- **Images:** Pillow is installed for image conversions. Drop it from the
  `pip { }` block if you only need text/data/PDF routes.
- **No signing config** is included — `assembleDebug` produces a debug-signed
  APK. Add a `signingConfig` for Play Store release builds.
