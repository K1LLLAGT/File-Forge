# FileForge 2.0 — Android setup

The Android app lives in [`android2/`](../android2/) (application id
`com.fileforge2.app`) and embeds the FileForge Python engine through
**Chaquopy**. The discovery/suggestion layer added in FileForge 2.0
(`fileforge.discovery`, `fileforge.suggestions`, `fileforge.unified_cli`) is
pure-Python and dependency-free, so it runs inside the Chaquopy interpreter
unchanged.

For the full module layout and a feature walkthrough, see
[`../android2/ANDROID_SETUP.md`](../android2/ANDROID_SETUP.md).

## Prerequisites

- Android Studio (Hedgehog or newer)
- JDK 17
- Android SDK Platform 34 + build-tools
- Python 3.9+ on the build machine (Chaquopy provisions the on-device runtime)

## Wiring the engine into the app

1. Open the `android2/` folder in Android Studio and let Gradle sync.
2. The Python bridge is `android2/app/src/main/python/ffbridge.py`. It already
   exposes the suggestion engine to Kotlin (`ranked_targets`, `suggest_dir`).
   Chaquopy pulls the engine in via the `pip` block in
   `android2/app/build.gradle.kts`:

   ```kotlin
   chaquopy {
       defaultConfig {
           pip {
               install("Pillow")
               // A locally-built wheel of this repo (includes the 2.0 layer)
               // is preferred when present; otherwise falls back to PyPI.
               install("pyfile-convert")
           }
       }
   }
   ```

3. From Kotlin, call the engine through the bridge, e.g.:

   ```python
   # ffbridge.py
   from fileforge.suggestions import scan_directory, suggest

   def suggestions_for(path):
       scan = scan_directory(path, recursive=True)
       return [s.to_dict() for s in suggest(scan)]
   ```

## Re-branding the package

To ship under a different application id (e.g. `com.yourname.fileforge`):

1. Edit `android2/app/build.gradle.kts` → `namespace` and
   `defaultConfig.applicationId`.
2. Rename the Kotlin package folders under
   `android2/app/src/main/java/…` and the `package` line in `MainActivity.kt`.
3. Nothing in `AndroidManifest.xml` hard-codes the id (it uses
   `${applicationId}`), so the FileProvider authority updates automatically.

## Build

```bash
cd android2
./gradlew assembleDebug        # debug APK
./gradlew assembleRelease      # release (signed) APK
```

The APK lands in `android2/app/build/outputs/apk/`. CI also builds it — see
[`.github/workflows/build-android.yml`](../.github/workflows/build-android.yml).
