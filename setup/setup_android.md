# FileForge 2.0 — Android setup

The Android app lives in [`android/`](../android/) and embeds the FileForge
Python engine through **Chaquopy**. The discovery/suggestion layer added in
FileForge 2.0 (`fileforge.discovery`, `fileforge.suggestions`,
`fileforge.unified_cli`) is pure-Python and dependency-free, so it runs inside
the Chaquopy interpreter unchanged.

## Prerequisites

- Android Studio (Hedgehog or newer)
- JDK 17
- Android SDK Platform 34 + build-tools
- Python 3.9+ on the build machine (Chaquopy provisions the on-device runtime)

## Wiring the engine into the app

1. Open the `android/` folder in Android Studio and let Gradle sync.
2. The Python bridge is `android/app/src/main/python/ffbridge.py`. To expose the
   new suggestion engine to Kotlin, add the FileForge package to Chaquopy's
   `pip` block in `android/app/build.gradle.kts`:

   ```kotlin
   chaquopy {
       defaultConfig {
           pip {
               // Point at the repo's src/ layout, or the published wheel.
               install("pyfile-convert")   // once published
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

To ship under a new application id (e.g. `com.yourname.fileforge2`):

1. Edit `android/app/build.gradle.kts` → `defaultConfig.applicationId`.
2. Update `namespace` to match.
3. Rename the Kotlin package folders under
   `android/app/src/main/java/…` and the `package` line in `MainActivity.kt`.
4. Update `android/app/src/main/AndroidManifest.xml` if it hard-codes the id.

See [`../android/README.md`](../android/README.md) for the full module layout.

## Build

```bash
cd android
./gradlew assembleDebug        # debug APK
./gradlew assembleRelease      # release (signed) APK
```

The APK lands in `android/app/build/outputs/apk/`.
