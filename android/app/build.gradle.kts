plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.k1lllagt.fileforge"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.k1lllagt.fileforge"
        minSdk = 24
        targetSdk = 34
        versionCode = 2
        versionName = "0.1.1"

        // Chaquopy needs explicit ABIs. arm64 covers modern phones; the others
        // keep older devices and emulators working.
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }

        // Chaquopy: embed CPython and the FileForge engine straight from PyPI.
        python {
            pip {
                install("pyfile-convert")   // the published FileForge CLI/engine
                install("Pillow")           // image conversions on-device
            }
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
