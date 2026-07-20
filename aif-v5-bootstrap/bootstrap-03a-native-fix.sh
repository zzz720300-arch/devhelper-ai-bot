#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/engine/upscale-ncnn/src/main/cpp"
cat > "$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp" <<'AIFV5_EOF'
#include <jni.h>
#include <android/log.h>
#include <vector>
#include <mutex>
#include <new>
#include "realsr.h"

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR,"ImageFinisherNCNN",__VA_ARGS__)
struct Engine { RealSR* sr; int scale; };
static std::once_flag gpu_once;

extern "C" JNIEXPORT jlong JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_create(
    JNIEnv* env, jobject, jstring p, jstring b, jint scale, jint tile, jboolean vulkan, jint threads
) {
    const char* pp = env->GetStringUTFChars(p, nullptr);
    const char* bp = env->GetStringUTFChars(b, nullptr);
    if (!pp || !bp) {
        if (pp) env->ReleaseStringUTFChars(p, pp);
        if (bp) env->ReleaseStringUTFChars(b, bp);
        return 0;
    }

    std::call_once(gpu_once, [] { ncnn::create_gpu_instance(); });
    const int gpu = (vulkan && ncnn::get_gpu_count() > 0) ? 0 : -1;

    Engine* engine = new(std::nothrow) Engine{nullptr, static_cast<int>(scale)};
    if (!engine) {
        env->ReleaseStringUTFChars(p, pp);
        env->ReleaseStringUTFChars(b, bp);
        return 0;
    }

    engine->sr = new(std::nothrow) RealSR(gpu, false, static_cast<int>(threads));
    if (!engine->sr) {
        delete engine;
        env->ReleaseStringUTFChars(p, pp);
        env->ReleaseStringUTFChars(b, bp);
        return 0;
    }

    engine->sr->scale = static_cast<int>(scale);
    engine->sr->tilesize = tile > 0 ? static_cast<int>(tile) : 256;
    engine->sr->prepadding = 10;
    const int rc = engine->sr->load(std::string(pp), std::string(bp));

    env->ReleaseStringUTFChars(p, pp);
    env->ReleaseStringUTFChars(b, bp);

    if (rc != 0) {
        delete engine->sr;
        delete engine;
        return 0;
    }
    return reinterpret_cast<jlong>(engine);
}

extern "C" JNIEXPORT jbyteArray JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_process(
    JNIEnv* env, jobject, jlong handle, jbyteArray input, jint width, jint height
) {
    Engine* engine = reinterpret_cast<Engine*>(handle);
    if (!engine || !engine->sr || !input || width <= 0 || height <= 0) return nullptr;

    const jsize length = env->GetArrayLength(input);
    if (length != width * height * 4) return nullptr;

    std::vector<unsigned char> bytes(static_cast<size_t>(length));
    env->GetByteArrayRegion(input, 0, length, reinterpret_cast<jbyte*>(bytes.data()));
    if (env->ExceptionCheck()) return nullptr;

    ncnn::Mat in(width, height, bytes.data(), static_cast<size_t>(4u), 4);
    ncnn::Mat out;
    const int rc = engine->sr->process(in, out);
    if (rc != 0 || out.empty()) return nullptr;

    const int expected = width * height * engine->scale * engine->scale * 4;
    const size_t available = out.total() * out.elemsize;
    if (available < static_cast<size_t>(expected)) {
        LOGE("Output buffer too short: %zu < %d", available, expected);
        return nullptr;
    }

    jbyteArray result = env->NewByteArray(expected);
    if (!result) return nullptr;
    env->SetByteArrayRegion(result, 0, expected, reinterpret_cast<const jbyte*>(out.data));
    if (env->ExceptionCheck()) return nullptr;
    return result;
}

extern "C" JNIEXPORT void JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_destroy(
    JNIEnv*, jobject, jlong handle
) {
    Engine* engine = reinterpret_cast<Engine*>(handle);
    if (engine) {
        delete engine->sr;
        delete engine;
    }
}

extern "C" JNIEXPORT jboolean JNICALL Java_ru_quantai_imagefinisher_engine_upscale_NcnnNative_hasVulkan(
    JNIEnv*, jobject
) {
    std::call_once(gpu_once, [] { ncnn::create_gpu_instance(); });
    return ncnn::get_gpu_count() > 0 ? JNI_TRUE : JNI_FALSE;
}
AIFV5_EOF

grep -q 'new(std::nothrow)' "$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp"
! grep -q 'try {' "$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp"
