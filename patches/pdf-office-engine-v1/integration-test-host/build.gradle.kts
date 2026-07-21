plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    buildToolsVersion = "36.0.0"
    namespace = "ru.pdfoffice.integration"
    compileSdk = 36
    defaultConfig {
        applicationId = "ru.pdfoffice.integration"
        minSdk = 26
        targetSdk = 36
        versionCode = 10000
        versionName = "1.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(project(":pdf-contract"))
    implementation(project(":pdf-engine-pdfbox"))
    implementation("androidx.core:core-ktx:1.15.0")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
}
