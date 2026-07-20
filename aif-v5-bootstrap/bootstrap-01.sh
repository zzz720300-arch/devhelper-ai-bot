#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/app"
cat > "$ROOT/app/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.application); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.app"; compileSdk = 36
    defaultConfig { applicationId = "ru.quantai.imagefinisher.enginegate"; minSdk = 26; targetSdk = 36; versionCode = 5; versionName = "0.5.0-engine-gate"; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner" }
    buildTypes { release { isMinifyEnabled = false } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    packaging.resources.excludes += setOf("META-INF/LICENSE*", "META-INF/NOTICE*", "META-INF/DEPENDENCIES")
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
dependencies {
    implementation(project(":integration:api")); implementation(libs.kotlinx.coroutines.android)
    androidTestImplementation(libs.androidx.test.ext.junit); androidTestImplementation(libs.androidx.test.espresso.core); androidTestImplementation(libs.androidx.test.runner); androidTestImplementation(libs.androidx.test.core); androidTestImplementation(libs.kotlinx.coroutines.android)
}

AIFV5_EOF
mkdir -p "$ROOT/app"
cat > "$ROOT/app/proguard-rules.pro" <<'AIFV5_EOF'
# Keep only rules required by app-specific reflection/serialization libraries.
# Retrofit includes its own consumer rules. Never silence all warnings globally.
-keepattributes Signature,InnerClasses,EnclosingMethod

AIFV5_EOF
mkdir -p "$ROOT/app/src/androidTest/java/ru/quantai/imagefinisher/app"
cat > "$ROOT/app/src/androidTest/java/ru/quantai/imagefinisher/app/EngineGateInstrumentedTest.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.app
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import ru.quantai.imagefinisher.core.engine.EngineStatus
import ru.quantai.imagefinisher.integration.ImageFinisherEngines
@RunWith(AndroidJUnit4::class)
class EngineGateInstrumentedTest {
 @Test fun allFourEnginesExecuteInsideAndroid() = runBlocking {
   val context=ApplicationProvider.getApplicationContext<android.content.Context>(); val e=ImageFinisherEngines(context)
   val results=listOf(e.resize.selfTest(),e.background.selfTest(),e.upscale.selfTest(),e.vector.selfTest())
   results.forEach{assertEquals("${it.engine}: ${it.message}",EngineStatus.READY,it.status)}
 }
}

AIFV5_EOF
mkdir -p "$ROOT/app/src/main"
cat > "$ROOT/app/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:theme="@style/Theme.ImageFinisher" android:label="AI Image Finisher Engine Gate"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>
AIFV5_EOF
mkdir -p "$ROOT/app/src/main/java/ru/quantai/imagefinisher/app"
cat > "$ROOT/app/src/main/java/ru/quantai/imagefinisher/app/MainActivity.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.app
import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.TextView
class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContentView(TextView(this).apply { text = "AI Image Finisher — Engine Gate V5\n\nАвтоматические тесты запускаются через Android instrumentation."; setTextColor(Color.WHITE); setBackgroundColor(Color.rgb(10,14,25)); textSize=20f; gravity=Gravity.CENTER; setPadding(32,32,32,32) }) }
}

AIFV5_EOF
mkdir -p "$ROOT/app/src/main/res/values"
cat > "$ROOT/app/src/main/res/values/styles.xml" <<'AIFV5_EOF'
<resources><style name="Theme.ImageFinisher" parent="android:style/Theme.Material.NoActionBar"><item name="android:fontFamily">sans</item><item name="android:windowLightStatusBar">false</item><item name="android:colorAccent">#77A7FF</item></style></resources>
AIFV5_EOF
mkdir -p "$ROOT/."
cat > "$ROOT/build.gradle.kts" <<'AIFV5_EOF'
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
}

AIFV5_EOF
mkdir -p "$ROOT/core/engine-api"
cat > "$ROOT/core/engine-api/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.core.engine"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
dependencies { implementation(libs.kotlinx.coroutines.android); testImplementation(libs.junit4) }

AIFV5_EOF
mkdir -p "$ROOT/core/engine-api"
cat > "$ROOT/core/engine-api/consumer-rules.pro" <<'AIFV5_EOF'

AIFV5_EOF
mkdir -p "$ROOT/core/engine-api/src/main"
cat > "$ROOT/core/engine-api/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
mkdir -p "$ROOT/core/engine-api/src/main/java/ru/quantai/imagefinisher/core/engine"
cat > "$ROOT/core/engine-api/src/main/java/ru/quantai/imagefinisher/core/engine/EngineContracts.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.core.engine

import android.graphics.Bitmap

fun interface ProgressListener { fun onProgress(done: Int, total: Int) }

enum class EngineStatus { READY, MISSING_ASSET, FAILED }

data class EngineAsset(val id: String, val fileName: String, val sha256: String, val sizeBytes: Long)
data class EngineHealth(val status: EngineStatus, val engine: String, val message: String, val details: Map<String,String> = emptyMap())

data class ResizeRequest(val width: Int, val height: Int, val algorithm: ResizeAlgorithm = ResizeAlgorithm.LANCZOS3)
enum class ResizeAlgorithm { LANCZOS3, BICUBIC, MITCHELL, CATMULL_ROM, BILINEAR, NEAREST }
interface ResizeEngine { suspend fun resize(input: Bitmap, request: ResizeRequest, progress: ProgressListener = ProgressListener { _, _ -> }): Bitmap; suspend fun selfTest(): EngineHealth }

data class BackgroundRequest(val quality: BackgroundQuality = BackgroundQuality.QUALITY)
enum class BackgroundQuality { QUALITY, FAST }
interface BackgroundRemovalEngine { suspend fun removeBackground(input: Bitmap, request: BackgroundRequest = BackgroundRequest(), progress: ProgressListener = ProgressListener { _, _ -> }): Bitmap; suspend fun selfTest(): EngineHealth }

data class UpscaleRequest(val scale: Int, val tileSize: Int = 256, val useVulkan: Boolean = true)
interface UpscaleEngine { suspend fun upscale(input: Bitmap, request: UpscaleRequest, progress: ProgressListener = ProgressListener { _, _ -> }): Bitmap; suspend fun selfTest(): EngineHealth }

data class VectorRequest(val preset: VectorPreset = VectorPreset.ILLUSTRATION, val colorPrecision: Int = 6, val filterSpeckle: Int = 4, val pathPrecision: Int = 2)
enum class VectorPreset { LOGO, ILLUSTRATION, POSTER, PHOTO }
data class VectorResult(val svg: String, val width: Int, val height: Int, val pathCount: Int)
interface VectorizationEngine { suspend fun vectorize(input: Bitmap, request: VectorRequest = VectorRequest(), progress: ProgressListener = ProgressListener { _, _ -> }): VectorResult; suspend fun selfTest(): EngineHealth }

AIFV5_EOF
mkdir -p "$ROOT/engine/background-onnx"
cat > "$ROOT/engine/background-onnx/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.engine.background"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    androidResources { noCompress += listOf("onnx","ort","bin","param") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
dependencies { implementation(project(":core:engine-api")); implementation(libs.onnx.runtime); implementation(libs.aire); implementation(libs.kotlinx.coroutines.android); testImplementation(libs.junit4) }

AIFV5_EOF
mkdir -p "$ROOT/engine/background-onnx"
cat > "$ROOT/engine/background-onnx/consumer-rules.pro" <<'AIFV5_EOF'
-keep class ai.onnxruntime.** { *; }

AIFV5_EOF
mkdir -p "$ROOT/engine/background-onnx/src/main"
cat > "$ROOT/engine/background-onnx/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
