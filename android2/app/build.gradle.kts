plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    // Re-branded FileForge 2.0 package id.
    namespace = "com.fileforge2.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.fileforge2.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "2.0.0"

        // Chaquopy needs explicit ABIs. arm64 covers modern phones; the others
        // keep older devices and emulators working.
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

// Chaquopy: embed CPython + the FileForge engine (incl. the 2.0
// discovery/suggestion layer, which is pure-Python). In the Kotlin DSL this is
// a top-level `chaquopy { }` extension, NOT a `python { }` block inside
// android.defaultConfig (that is the Groovy form and does not compile in .kts).
//
// The published PyPI `pyfile-convert` does not yet ship the 2.0 suggestion
// layer that `ffbridge.ranked_targets` / `suggest_dir` rely on, so we prefer a
// locally-built wheel of *this* repo when one is present (CI builds it into
// `app/wheels/` via `pip wheel .`), and fall back to PyPI otherwise.
val fileForgeWheel = fileTree("wheels") { include("*.whl") }.files.firstOrNull()
chaquopy {
    defaultConfig {
        pip {
            install("Pillow")   // image conversions on-device
            if (fileForgeWheel != null) {
                install(fileForgeWheel.absolutePath)   // local engine + 2.0 layer
            } else {
                install("pyfile-convert")              // fallback (may lack 2.0 layer)
            }
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation(platform("androidx.compose:compose-bom:2024.02.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
