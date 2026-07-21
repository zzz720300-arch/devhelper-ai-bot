import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val keystoreFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties().apply {
    if (keystoreFile.exists()) keystoreFile.inputStream().use(::load)
}

android {
    buildToolsVersion = "36.0.0"
    namespace = "ru.pdfoffice.demo"
    compileSdk = 36
    defaultConfig {
        applicationId = "ru.pdfoffice.demo"
        minSdk = 26
        targetSdk = 36
        versionCode = 10000
        versionName = "1.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    signingConfigs {
        if (keystoreFile.exists()) create("release") {
            storeFile = rootProject.file(requireNotNull(keystoreProperties.getProperty("storeFile")))
            storePassword = requireNotNull(keystoreProperties.getProperty("storePassword"))
            keyAlias = requireNotNull(keystoreProperties.getProperty("keyAlias"))
            keyPassword = requireNotNull(keystoreProperties.getProperty("keyPassword"))
        }
    }
    buildTypes {
        debug { applicationIdSuffix = ".debug"; versionNameSuffix = "-debug" }
        release {
            isDebuggable = false
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.findByName("release")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    lint { abortOnError = true; checkReleaseBuilds = true }
}

dependencies {
    implementation(project(":pdf-contract"))
    implementation(project(":pdf-engine-pdfbox"))
    implementation(project(":pdf-render"))
    implementation("androidx.core:core-ktx:1.15.0")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
}
