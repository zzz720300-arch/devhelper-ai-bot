#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/engine/background-onnx/src/main/java/ru/quantai/imagefinisher/engine/background"
cat > "$ROOT/engine/background-onnx/src/main/java/ru/quantai/imagefinisher/engine/background/BiRefNetBackgroundEngine.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.background

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import com.awxkee.aire.Aire
import com.awxkee.aire.ResizeFunction
import com.awxkee.aire.ScaleColorSpace
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.quantai.imagefinisher.core.engine.*
import java.nio.FloatBuffer
import kotlin.math.exp
import kotlin.math.min

class BiRefNetBackgroundEngine(private val context: Context) : BackgroundRemovalEngine, AutoCloseable {
    private val env by lazy { OrtEnvironment.getEnvironment() }
    private var qualitySession: OrtSession? = null
    private var fastSession: OrtSession? = null

    override suspend fun removeBackground(input: Bitmap, request: BackgroundRequest, progress: ProgressListener): Bitmap = withContext(Dispatchers.Default) {
        val spec = when (request.quality) {
            BackgroundQuality.QUALITY -> ModelSpec("birefnet_lite.onnx", QUALITY_SHA256, 1024, floatArrayOf(.485f,.456f,.406f), floatArrayOf(.229f,.224f,.225f), OutputMode.SIGMOID)
            BackgroundQuality.FAST -> ModelSpec("u2netp.onnx", FAST_SHA256, 320, floatArrayOf(.485f,.456f,.406f), floatArrayOf(.229f,.224f,.225f), OutputMode.MIN_MAX)
        }
        progress.onProgress(0,3)
        val source = input.copy(Bitmap.Config.ARGB_8888, false) ?: error("Bitmap conversion failed")
        val prepared = letterbox(source, spec.size)
        progress.onProgress(1,3)
        val mask = inferMask(session(request.quality, spec), prepared.bitmap, spec)
        progress.onProgress(2,3)
        val cropped = Bitmap.createBitmap(mask, prepared.offsetX, prepared.offsetY, prepared.contentWidth, prepared.contentHeight)
        val scaled = Aire.scale(cropped, source.width, source.height, ResizeFunction.Bilinear, ScaleColorSpace.SRGB)
        progress.onProgress(3,3)
        applyMask(source, scaled)
    }

    private fun session(quality: BackgroundQuality, spec: ModelSpec): OrtSession {
        (if (quality == BackgroundQuality.QUALITY) qualitySession else fastSession)?.let { return it }
        val file = ModelFileInstaller.install(context, spec.fileName, spec.sha256)
        val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceIn(1,4)); setInterOpNumThreads(1); setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT) }
        return env.createSession(file.absolutePath, options).also { if (quality == BackgroundQuality.QUALITY) qualitySession = it else fastSession = it }
    }

    private fun inferMask(session: OrtSession, bitmap: Bitmap, spec: ModelSpec): Bitmap {
        val n = spec.size * spec.size
        val pixels = IntArray(n); bitmap.getPixels(pixels,0,spec.size,0,0,spec.size,spec.size)
        val data = FloatArray(3*n); var r=0; var g=n; var b=2*n
        for (px in pixels) { val rr=Color.red(px)/255f; val gg=Color.green(px)/255f; val bb=Color.blue(px)/255f; data[r++]=(rr-spec.mean[0])/spec.std[0]; data[g++]=(gg-spec.mean[1])/spec.std[1]; data[b++]=(bb-spec.mean[2])/spec.std[2] }
        OnnxTensor.createTensor(env, FloatBuffer.wrap(data), longArrayOf(1,3,spec.size.toLong(),spec.size.toLong())).use { tensor ->
            session.run(mapOf(session.inputNames.first() to tensor)).use { result ->
                val raw = flatten(result[0].value, n)
                val values = when (spec.outputMode) {
                    OutputMode.SIGMOID -> FloatArray(n) { i -> (1.0 / (1.0 + exp(-raw[i].toDouble()))).toFloat() }
                    OutputMode.MIN_MAX -> { val lo=raw.minOrNull()?:0f; val hi=raw.maxOrNull()?:1f; val d=(hi-lo).coerceAtLeast(1e-6f); FloatArray(n){i->(raw[i]-lo)/d} }
                }
                val out = IntArray(n) { i -> Color.argb((values[i].coerceIn(0f,1f)*255f).toInt(),255,255,255) }
                return Bitmap.createBitmap(spec.size,spec.size,Bitmap.Config.ARGB_8888).apply { setPixels(out,0,spec.size,0,0,spec.size,spec.size); setHasAlpha(true) }
            }
        }
    }

    private fun flatten(value: Any, expected: Int): FloatArray { val out=FloatArray(expected); var i=0; fun walk(v:Any?){ when(v){ is FloatArray -> v.forEach{if(i<expected)out[i++]=it}; is Array<*> -> v.forEach(::walk); is FloatBuffer -> {val c=v.duplicate();while(c.hasRemaining()&&i<expected)out[i++]=c.get()}; else -> error("Unsupported ONNX output ${v?.javaClass}") } }; walk(value); check(i>=expected){"ONNX output too short $i/$expected"}; return out }
    private data class Prepared(val bitmap:Bitmap,val offsetX:Int,val offsetY:Int,val contentWidth:Int,val contentHeight:Int)
    private fun letterbox(source:Bitmap,size:Int):Prepared { val scale=min(size/source.width.toFloat(),size/source.height.toFloat()); val w=(source.width*scale).toInt().coerceAtLeast(1); val h=(source.height*scale).toInt().coerceAtLeast(1); val scaled=Aire.scale(source,w,h,ResizeFunction.Bilinear,ScaleColorSpace.SRGB); val x=(size-w)/2; val y=(size-h)/2; val canvasBitmap=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888); Canvas(canvasBitmap).apply{drawColor(Color.BLACK);drawBitmap(scaled,x.toFloat(),y.toFloat(),Paint(Paint.FILTER_BITMAP_FLAG))}; return Prepared(canvasBitmap,x,y,w,h) }
    private fun applyMask(source:Bitmap,mask:Bitmap):Bitmap { val src=IntArray(source.width*source.height); val m=IntArray(src.size); source.getPixels(src,0,source.width,0,0,source.width,source.height); mask.getPixels(m,0,source.width,0,0,source.width,source.height); for(i in src.indices){val a=Color.alpha(m[i]);val p=src[i];src[i]=Color.argb(a,Color.red(p),Color.green(p),Color.blue(p))}; return Bitmap.createBitmap(source.width,source.height,Bitmap.Config.ARGB_8888).apply{setPixels(src,0,source.width,0,0,source.width,source.height);setHasAlpha(true)} }
    override suspend fun selfTest():EngineHealth = runCatching { val test=context.assets.open("selftest/subject.png").use{android.graphics.BitmapFactory.decodeStream(it)}; val result=removeBackground(test,BackgroundRequest(BackgroundQuality.QUALITY)); val pixels=IntArray(result.width*result.height); result.getPixels(pixels,0,result.width,0,0,result.width,result.height); val transparent=pixels.count{Color.alpha(it)<32}; val opaque=pixels.count{Color.alpha(it)>223}; check(transparent>pixels.size/30){"No background pixels"};check(opaque>pixels.size/30){"No foreground pixels"};EngineHealth(EngineStatus.READY,"BiRefNetBackgroundEngine","BiRefNet Lite Android inference passed",mapOf("transparent" to transparent.toString(),"opaque" to opaque.toString())) }.getOrElse{EngineHealth(if(it is java.io.FileNotFoundException)EngineStatus.MISSING_ASSET else EngineStatus.FAILED,"BiRefNetBackgroundEngine",it.message?:it.javaClass.name)}
    override fun close(){qualitySession?.close();fastSession?.close();qualitySession=null;fastSession=null}
    private data class ModelSpec(val fileName:String,val sha256:String,val size:Int,val mean:FloatArray,val std:FloatArray,val outputMode:OutputMode)
    private enum class OutputMode{SIGMOID,MIN_MAX}
    companion object { const val QUALITY_SHA256="5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333"; const val FAST_SHA256="16fb536473a41b2e101bd3a6ff788f599b95e32ecbe20624c552b3d8ba91a11a" }
}

AIFV5_EOF
mkdir -p "$ROOT/engine/background-onnx/src/main/java/ru/quantai/imagefinisher/engine/background"
cat > "$ROOT/engine/background-onnx/src/main/java/ru/quantai/imagefinisher/engine/background/ModelFileInstaller.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.background

import android.content.Context
import java.io.File
import java.security.MessageDigest

internal object ModelFileInstaller {
    fun install(context: Context, assetName: String, expectedSha256: String): File {
        val out = File(context.filesDir, "imagefinisher-models/$assetName")
        out.parentFile?.mkdirs()
        if (!out.isFile || sha256(out) != expectedSha256) {
            context.assets.open("models/$assetName").use { input -> out.outputStream().use(input::copyTo) }
            check(sha256(out) == expectedSha256) { "Model checksum mismatch: $assetName" }
        }
        return out
    }
    fun sha256(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { stream ->
            val buffer = ByteArray(1024 * 1024)
            while (true) { val n=stream.read(buffer); if(n<0) break; md.update(buffer,0,n) }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
}

AIFV5_EOF
mkdir -p "$ROOT/engine/resize-aire"
cat > "$ROOT/engine/resize-aire/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.engine.resize"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
dependencies { implementation(project(":core:engine-api")); implementation(libs.aire); implementation(libs.kotlinx.coroutines.android); testImplementation(libs.junit4) }

AIFV5_EOF
mkdir -p "$ROOT/engine/resize-aire"
cat > "$ROOT/engine/resize-aire/consumer-rules.pro" <<'AIFV5_EOF'

AIFV5_EOF
mkdir -p "$ROOT/engine/resize-aire/src/main"
cat > "$ROOT/engine/resize-aire/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
mkdir -p "$ROOT/engine/resize-aire/src/main/java/ru/quantai/imagefinisher/engine/resize"
cat > "$ROOT/engine/resize-aire/src/main/java/ru/quantai/imagefinisher/engine/resize/AireResizeEngine.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.resize

import android.graphics.Bitmap
import android.graphics.Color
import com.awxkee.aire.Aire
import com.awxkee.aire.ResizeFunction
import com.awxkee.aire.ScaleColorSpace
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.quantai.imagefinisher.core.engine.*

class AireResizeEngine : ResizeEngine {
    override suspend fun resize(input: Bitmap, request: ResizeRequest, progress: ProgressListener): Bitmap = withContext(Dispatchers.Default) {
        require(request.width > 0 && request.height > 0) { "Target size must be positive" }
        progress.onProgress(0, 1)
        val source = if (input.config == Bitmap.Config.ARGB_8888) input else input.copy(Bitmap.Config.ARGB_8888, false) ?: error("Bitmap conversion failed")
        val result = Aire.scale(
            bitmap = source,
            dstWidth = request.width,
            dstHeight = request.height,
            scaleMode = request.algorithm.toAire(),
            colorSpace = ScaleColorSpace.SRGB
        ).apply { setHasAlpha(input.hasAlpha()) }
        progress.onProgress(1, 1)
        result
    }

    override suspend fun selfTest(): EngineHealth = runCatching {
        val source = Bitmap.createBitmap(4, 4, Bitmap.Config.ARGB_8888).apply {
            setHasAlpha(true)
            eraseColor(Color.TRANSPARENT)
            setPixel(1, 1, Color.argb(255, 255, 0, 0))
        }
        val output = resize(source, ResizeRequest(8, 8, ResizeAlgorithm.LANCZOS3))
        check(output.width == 8 && output.height == 8)
        check(output.hasAlpha())
        EngineHealth(EngineStatus.READY, "AireResizeEngine", "Lanczos3 native resize passed", mapOf("version" to "0.18.1"))
    }.getOrElse { EngineHealth(EngineStatus.FAILED, "AireResizeEngine", it.message ?: it.javaClass.name) }

    private fun ResizeAlgorithm.toAire() = when (this) {
        ResizeAlgorithm.LANCZOS3 -> ResizeFunction.Lanczos3
        ResizeAlgorithm.BICUBIC -> ResizeFunction.Bicubic
        ResizeAlgorithm.MITCHELL -> ResizeFunction.MitchellNetravalli
        ResizeAlgorithm.CATMULL_ROM -> ResizeFunction.CatmullRom
        ResizeAlgorithm.BILINEAR -> ResizeFunction.Bilinear
        ResizeAlgorithm.NEAREST -> ResizeFunction.Nearest
    }
}

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn"
cat > "$ROOT/engine/upscale-ncnn/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.engine.upscale"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    androidResources { noCompress += listOf("onnx","ort","bin","param") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
android { sourceSets["main"].jniLibs.srcDir("src/main/jniLibs") }
dependencies { implementation(project(":core:engine-api")); implementation(libs.kotlinx.coroutines.android); testImplementation(libs.junit4) }

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn"
cat > "$ROOT/engine/upscale-ncnn/consumer-rules.pro" <<'AIFV5_EOF'
-keep class ru.quantai.imagefinisher.engine.upscale.NcnnNative { *; }

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn/src/main"
cat > "$ROOT/engine/upscale-ncnn/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/cpp"
cat > "$ROOT/engine/upscale-ncnn/src/main/cpp/CMakeLists.txt" <<'AIFV5_EOF'
cmake_minimum_required(VERSION 3.22.1)
project(imagefinisher_upscale)
if(NOT DEFINED REALSR_SRC_DIR)
  message(FATAL_ERROR "REALSR_SRC_DIR is required")
endif()
find_package(ncnn REQUIRED)
add_library(imagefinisher_upscale SHARED realsr_jni.cpp ${REALSR_SRC_DIR}/realsr.cpp)
target_include_directories(imagefinisher_upscale PRIVATE ${REALSR_SRC_DIR})
target_compile_features(imagefinisher_upscale PRIVATE cxx_std_17)
target_link_libraries(imagefinisher_upscale ncnn log android)

AIFV5_EOF
