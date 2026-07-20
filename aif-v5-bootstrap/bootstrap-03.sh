#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/cpp"
cat > "$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp" <<'AIFV5_EOF'
#include <jni.h>
#include <android/log.h>
#include <vector>
#include <mutex>
#include "realsr.h"

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR,"ImageFinisherNCNN",__VA_ARGS__)
struct Engine { RealSR* sr; int scale; };
static std::once_flag gpu_once;

extern "C" JNIEXPORT jlong JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_create(JNIEnv* env,jobject,jstring p,jstring b,jint scale,jint tile,jboolean vulkan,jint threads){
    const char* pp=env->GetStringUTFChars(p,nullptr); const char* bp=env->GetStringUTFChars(b,nullptr);
    try {
        std::call_once(gpu_once,[]{ ncnn::create_gpu_instance(); });
        int gpu=(vulkan && ncnn::get_gpu_count()>0)?0:-1;
        auto* e=new Engine(); e->scale=scale; e->sr=new RealSR(gpu,false,threads); e->sr->scale=scale; e->sr->tilesize=tile>0?tile:256; e->sr->prepadding=10;
        int rc=e->sr->load(std::string(pp),std::string(bp));
        env->ReleaseStringUTFChars(p,pp); env->ReleaseStringUTFChars(b,bp);
        if(rc!=0){ return 0; }
        return reinterpret_cast<jlong>(e);
    } catch(...) { env->ReleaseStringUTFChars(p,pp); env->ReleaseStringUTFChars(b,bp); return 0; }
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_process(JNIEnv* env,jobject,jlong handle,jbyteArray input,jint w,jint h){
    auto* e=reinterpret_cast<Engine*>(handle); if(!e||!e->sr) return nullptr;
    jsize len=env->GetArrayLength(input); if(len!=w*h*4) return nullptr;
    std::vector<unsigned char> bytes(len); env->GetByteArrayRegion(input,0,len,reinterpret_cast<jbyte*>(bytes.data()));
    ncnn::Mat in(w,h,bytes.data(),(size_t)4u,4); ncnn::Mat out; int rc=e->sr->process(in,out); if(rc!=0 || out.empty()) return nullptr;
    const int expected=w*h*e->scale*e->scale*4; if((int)out.total()*out.elemsize<expected){ LOGE("output short"); return nullptr; }
    jbyteArray result=env->NewByteArray(expected); env->SetByteArrayRegion(result,0,expected,reinterpret_cast<const jbyte*>(out.data)); return result;
}
extern "C" JNIEXPORT void JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_destroy(JNIEnv*,jobject,jlong handle){ auto* e=reinterpret_cast<Engine*>(handle); if(e){ delete e->sr; delete e; } }
extern "C" JNIEXPORT jboolean JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_hasVulkan(JNIEnv*,jobject){ std::call_once(gpu_once,[]{ ncnn::create_gpu_instance(); }); return ncnn::get_gpu_count()>0; }

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/java/ru/quantai/imagefinisher/engine/upscale"
cat > "$ROOT/engine/upscale-ncnn/src/main/java/ru/quantai/imagefinisher/engine/upscale/NcnnNative.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.upscale
internal object NcnnNative {
    init { System.loadLibrary("imagefinisher_upscale") }
    external fun create(paramPath:String, binPath:String, scale:Int, tileSize:Int, useVulkan:Boolean, threads:Int):Long
    external fun process(handle:Long, rgba:ByteArray, width:Int, height:Int):ByteArray
    external fun destroy(handle:Long)
    external fun hasVulkan():Boolean
}

AIFV5_EOF
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/java/ru/quantai/imagefinisher/engine/upscale"
cat > "$ROOT/engine/upscale-ncnn/src/main/java/ru/quantai/imagefinisher/engine/upscale/NcnnUpscaleEngine.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.upscale
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.quantai.imagefinisher.core.engine.*
import java.io.File
import java.security.MessageDigest

class NcnnUpscaleEngine(private val context:Context):UpscaleEngine {
    override suspend fun upscale(input:Bitmap, request:UpscaleRequest, progress:ProgressListener):Bitmap = withContext(Dispatchers.Default) {
        require(request.scale==2 || request.scale==4){"Only native 2x and 4x models are supported"}
        val model=if(request.scale==2)Model("esrgan_dropout_x2.param","esrgan_dropout_x2.bin",X2_PARAM_SHA,X2_BIN_SHA) else Model("realesr_general_x4v3.param","realesr_general_x4v3.bin",X4_PARAM_SHA,X4_BIN_SHA)
        val param=install(model.param,model.paramSha); val bin=install(model.bin,model.binSha)
        val source=if(input.config==Bitmap.Config.ARGB_8888)input else input.copy(Bitmap.Config.ARGB_8888,false)?:error("Bitmap conversion failed")
        val ints=IntArray(source.width*source.height);source.getPixels(ints,0,source.width,0,0,source.width,source.height);val bytes=ByteArray(ints.size*4);var o=0
        for(p in ints){bytes[o++]=(p shr 16).toByte();bytes[o++]=(p shr 8).toByte();bytes[o++]=p.toByte();bytes[o++]=(p ushr 24).toByte()}
        progress.onProgress(0,1);val handle=NcnnNative.create(param.absolutePath,bin.absolutePath,request.scale,request.tileSize,request.useVulkan,Runtime.getRuntime().availableProcessors().coerceIn(1,4));check(handle!=0L){"ncnn engine creation failed"}
        try{val out=NcnnNative.process(handle,bytes,source.width,source.height);val ow=source.width*request.scale;val oh=source.height*request.scale;check(out.size==ow*oh*4){"Invalid native output ${out.size}"};val outInts=IntArray(ow*oh);o=0;for(i in outInts.indices){val r=out[o++].toInt() and 255;val g=out[o++].toInt() and 255;val b=out[o++].toInt() and 255;val a=out[o++].toInt() and 255;outInts[i]=(a shl 24)or(r shl 16)or(g shl 8)or b};Bitmap.createBitmap(ow,oh,Bitmap.Config.ARGB_8888).apply{setPixels(outInts,0,ow,0,0,ow,oh);setHasAlpha(source.hasAlpha())}}finally{NcnnNative.destroy(handle);progress.onProgress(1,1)}
    }
    override suspend fun selfTest():EngineHealth=runCatching{check(File(context.applicationInfo.nativeLibraryDir,"libimagefinisher_upscale.so").isFile);val test=Bitmap.createBitmap(32,32,Bitmap.Config.ARGB_8888).apply{for(y in 0 until 32)for(x in 0 until 32)setPixel(x,y,Color.argb(255,x*8,y*8,(x+y)*4))};val x2=upscale(test,UpscaleRequest(2,32,false));val x4=upscale(test,UpscaleRequest(4,32,false));check(x2.width==64&&x2.height==64);check(x4.width==128&&x4.height==128);EngineHealth(EngineStatus.READY,"NcnnUpscaleEngine","Separate x2 and x4 ncnn inference passed",mapOf("vulkan" to NcnnNative.hasVulkan().toString()))}.getOrElse{EngineHealth(EngineStatus.FAILED,"NcnnUpscaleEngine",it.message?:it.javaClass.name)}
    private data class Model(val param:String,val bin:String,val paramSha:String,val binSha:String)
    private fun install(name:String,sha:String):File{val f=File(context.filesDir,"imagefinisher-models/$name");f.parentFile?.mkdirs();if(!f.isFile||digest(f)!=sha){context.assets.open("models/$name").use{i->f.outputStream().use(i::copyTo)};check(digest(f)==sha){"Model checksum mismatch $name"}};return f}
    private fun digest(f:File):String{val md=MessageDigest.getInstance("SHA-256");f.inputStream().use{s->val b=ByteArray(1 shl 20);while(true){val n=s.read(b);if(n<0)break;md.update(b,0,n)}};return md.digest().joinToString(""){"%02x".format(it)}}
    companion object{const val X2_PARAM_SHA="__X2_PARAM_SHA__";const val X2_BIN_SHA="0c96ee6cade6b914ff1ba1d6a635364be968db5f9264313c94199d52c1fc28cd";const val X4_PARAM_SHA="__X4_PARAM_SHA__";const val X4_BIN_SHA="01450f4a79b81c0f1f3eeefc31121167886125c25e41a6d4773e8ec8062528a1"}
}

AIFV5_EOF
mkdir -p "$ROOT/engine/vector-vtracer"
cat > "$ROOT/engine/vector-vtracer/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.engine.vector"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
android { sourceSets["main"].jniLibs.srcDir("src/main/jniLibs") }
dependencies { implementation(project(":core:engine-api")); implementation(libs.kotlinx.coroutines.android); testImplementation(libs.junit4) }

AIFV5_EOF
mkdir -p "$ROOT/engine/vector-vtracer"
cat > "$ROOT/engine/vector-vtracer/consumer-rules.pro" <<'AIFV5_EOF'
-keep class ru.quantai.imagefinisher.engine.vector.VTracerNative { *; }

AIFV5_EOF
mkdir -p "$ROOT/engine/vector-vtracer/src/main"
cat > "$ROOT/engine/vector-vtracer/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
mkdir -p "$ROOT/engine/vector-vtracer/src/main/java/ru/quantai/imagefinisher/engine/vector"
cat > "$ROOT/engine/vector-vtracer/src/main/java/ru/quantai/imagefinisher/engine/vector/VTracerEngine.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.vector
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import ru.quantai.imagefinisher.core.engine.*
import java.io.File

class VTracerEngine(private val context:Context):VectorizationEngine {
    override suspend fun vectorize(input:Bitmap, request:VectorRequest, progress:ProgressListener):VectorResult=withContext(Dispatchers.IO){
        val dir=File(context.cacheDir,"vtracer").apply{mkdirs()}; val png=File(dir,"input-${System.nanoTime()}.png"); val svg=File(dir,"output-${System.nanoTime()}.svg")
        png.outputStream().use{ check(input.compress(Bitmap.CompressFormat.PNG,100,it)) }
        progress.onProgress(0,1); val rc=VTracerNative.vectorize(png.absolutePath,svg.absolutePath,request.preset.ordinal,request.colorPrecision,request.filterSpeckle,request.pathPrecision); check(rc==0){"VTracer failed code=$rc"}
        val text=svg.readText(); val paths=Regex("<path\\s").findAll(text).count(); check(paths>0); check(!text.contains("<image",true)); progress.onProgress(1,1)
        png.delete(); svg.delete(); VectorResult(text,input.width,input.height,paths)
    }
    override suspend fun selfTest():EngineHealth=runCatching{
        val b=Bitmap.createBitmap(32,32,Bitmap.Config.ARGB_8888); b.eraseColor(Color.TRANSPARENT); for(y in 8..23)for(x in 8..23)b.setPixel(x,y,Color.RED)
        val result=vectorize(b,VectorRequest(VectorPreset.LOGO)); check(result.pathCount>0); check(!result.svg.contains("<image",true)); EngineHealth(EngineStatus.READY,"VTracerEngine","Rust VTracer produced editable paths",mapOf("paths" to result.pathCount.toString(),"version" to "0.6.4"))
    }.getOrElse{EngineHealth(EngineStatus.FAILED,"VTracerEngine",it.message?:it.javaClass.name)}
}

AIFV5_EOF
mkdir -p "$ROOT/engine/vector-vtracer/src/main/java/ru/quantai/imagefinisher/engine/vector"
cat > "$ROOT/engine/vector-vtracer/src/main/java/ru/quantai/imagefinisher/engine/vector/VTracerNative.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.engine.vector
internal object VTracerNative { init { System.loadLibrary("imagefinisher_vtracer") }; external fun vectorize(inputPath:String,outputPath:String,preset:Int,colorPrecision:Int,filterSpeckle:Int,pathPrecision:Int):Int }

AIFV5_EOF
mkdir -p "$ROOT/gradle"
cat > "$ROOT/gradle/libs.versions.toml" <<'AIFV5_EOF'
[versions]
agp = "8.13.2"
kotlin = "2.3.21"
coroutines = "1.10.2"
aire = "0.18.1"
onnx = "1.27.0"
junit4 = "4.13.2"
androidxTestExt = "1.3.0"
espresso = "3.7.0"
runner = "1.7.0"
testCore = "1.7.0"

[libraries]
kotlinx-coroutines-android = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-android", version.ref = "coroutines" }
aire = { module = "com.github.awxkee:aire", version.ref = "aire" }
onnx-runtime = { module = "com.microsoft.onnxruntime:onnxruntime-android", version.ref = "onnx" }
junit4 = { module = "junit:junit", version.ref = "junit4" }
androidx-test-ext-junit = { module = "androidx.test.ext:junit", version.ref = "androidxTestExt" }
androidx-test-espresso-core = { module = "androidx.test.espresso:espresso-core", version.ref = "espresso" }
androidx-test-runner = { module = "androidx.test:runner", version.ref = "runner" }
androidx-test-core = { module = "androidx.test:core", version.ref = "testCore" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
android-library = { id = "com.android.library", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }

AIFV5_EOF
mkdir -p "$ROOT/."
cat > "$ROOT/gradle.properties" <<'AIFV5_EOF'
org.gradle.jvmargs=-Xmx4g -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
android.defaults.buildfeatures.buildconfig=true

AIFV5_EOF
mkdir -p "$ROOT/integration/api"
cat > "$ROOT/integration/api/build.gradle.kts" <<'AIFV5_EOF'
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { alias(libs.plugins.android.library); alias(libs.plugins.kotlin.android) }
android {
    namespace = "ru.quantai.imagefinisher.integration"
    compileSdk = 36
    defaultConfig { minSdk = 26; testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"; consumerProguardFiles("consumer-rules.pro") }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }
dependencies { api(project(":core:engine-api")); api(project(":engine:resize-aire")); api(project(":engine:background-onnx")); api(project(":engine:upscale-ncnn")); api(project(":engine:vector-vtracer")); implementation(libs.kotlinx.coroutines.android) }

AIFV5_EOF
mkdir -p "$ROOT/integration/api"
cat > "$ROOT/integration/api/consumer-rules.pro" <<'AIFV5_EOF'

AIFV5_EOF
mkdir -p "$ROOT/integration/api/src/main"
cat > "$ROOT/integration/api/src/main/AndroidManifest.xml" <<'AIFV5_EOF'
<manifest />

AIFV5_EOF
