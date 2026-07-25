# FileForge 2.0 — Android (re-branded)

A re-branded Android build of FileForge under a **new application id**,
`com.fileforge2.app`, built on the same shared Python engine as the CLI and
desktop app via **Chaquopy**. It adds a suggestion-driven target picker and a
persisted conversion-history screen on top of the FileForge 2.0 layer.

> This lives alongside the original `android/` project (id
> `com.k1lllagt.fileforge`) so both can be installed side-by-side. If you only
> want one, delete `android/`.

## What changed vs. `android/`

| Aspect | `android/` | `android2/` (this project) |
|--------|-----------|----------------------------|
| Application id / namespace | `com.k1lllagt.fileforge` | **`com.fileforge2.app`** |
| Kotlin package | `com.k1lllagt.fileforge` | **`com.fileforge2.app`** |
| App label | "FileForge" | **"FileForge 2.0"** |
| versionName / versionCode | 0.1.1 / 2 | **2.0.0 / 1** |
| Target list | alphabetical (`targets_for`) | **ranked** (`ranked_targets`, engine-supported first; generic shown but disabled) |
| History | — | **persisted** (`filesDir/history.json`), own tab |
| Bridge | `targets_for/can_convert/convert` | adds **`ranked_targets`**, **`suggest_dir`** (FileForge 2.0 suggestion layer) |

## Project layout

```
android2/
  settings.gradle.kts            # rootProject.name = "FileForge2"
  build.gradle.kts               # plugin versions
  gradle.properties
  gradle/wrapper/gradle-wrapper.properties
  app/
    build.gradle.kts             # applicationId = com.fileforge2.app + Chaquopy pip
    proguard-rules.pro
    src/main/
      AndroidManifest.xml
      java/com/fileforge2/app/MainActivity.kt   # Compose UI: Convert + History tabs
      python/ffbridge.py                        # Kotlin <-> engine bridge (2.0 layer)
      res/values/strings.xml                    # app_name = "FileForge 2.0"
      res/values/themes.xml                     # Theme.FileForge2
      res/xml/file_paths.xml                    # FileProvider paths
```

## Prerequisites

- Android Studio (Hedgehog or newer), JDK 17
- Android SDK Platform 34 + build-tools
- Python 3.9+ on the build machine (Chaquopy provisions the on-device runtime)

## Features

- **File selection** — system file picker (`GetContent`), copied into the app cache.
- **Source/target format selection** — the source extension is inferred from the
  picked file; the target dropdown is populated from `ffbridge.ranked_targets`,
  which puts engine-supported formats first and disables generic (not-yet-
  supported) suggestions.
- **Conversion history** — every conversion (success or failure) is appended to
  `filesDir/history.json` and shown on the **History** tab, with a Clear action.
- **Engine integration** — all conversions run through the shared
  `fileforge.core.registry`; the target ranking uses `fileforge.suggestions`.

## Build & run

```bash
cd android2
./gradlew assembleDebug        # debug APK
./gradlew assembleRelease      # release (signed) APK
```

APK output: `android2/app/build/outputs/apk/`.

The first build downloads CPython + the pip requirements
(`pyfile-convert`, `Pillow`) declared in `app/build.gradle.kts` under the
Chaquopy `python { pip { ... } }` block.

## Changing the id again

To ship under yet another id (e.g. `com.acme.fileforge`):

1. `app/build.gradle.kts` → `namespace` and `defaultConfig.applicationId`.
2. Rename the folders under `app/src/main/java/…` and the `package` line at the
   top of `MainActivity.kt`.
3. Nothing in `AndroidManifest.xml` hard-codes the id (it uses
   `${applicationId}`), so the FileProvider authority updates automatically.
