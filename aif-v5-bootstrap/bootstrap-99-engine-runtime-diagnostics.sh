#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
FILE="$ROOT/app/src/androidTest/java/ru/quantai/imagefinisher/app/EngineGateInstrumentedTest.kt"
mkdir -p "$(dirname "$FILE")"
cat > "$FILE" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.app

import android.content.Context
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.fail
import org.junit.FixMethodOrder
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.MethodSorters
import ru.quantai.imagefinisher.core.engine.EngineHealth
import ru.quantai.imagefinisher.core.engine.EngineStatus
import ru.quantai.imagefinisher.integration.ImageFinisherEngines

@RunWith(AndroidJUnit4::class)
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
class EngineGateInstrumentedTest {
    private val context: Context
        get() = ApplicationProvider.getApplicationContext()

    private fun assertReady(health: EngineHealth) {
        val evidence = "${health.engine}: status=${health.status}; message=${health.message}; details=${health.details}"
        Log.e("AIF_ENGINE_GATE", evidence)
        if (health.status != EngineStatus.READY) fail(evidence)
    }

    @Test
    fun a_resizeEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).resize.selfTest())
    }

    @Test
    fun b_backgroundEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).background.selfTest())
    }

    @Test
    fun c_upscaleX2AndX4ExecuteInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).upscale.selfTest())
    }

    @Test
    fun d_vectorEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).vector.selfTest())
    }
}
AIFV5_EOF

grep -q 'a_resizeEngineExecutesInsideAndroid' "$FILE"
grep -q 'b_backgroundEngineExecutesInsideAndroid' "$FILE"
grep -q 'c_upscaleX2AndX4ExecuteInsideAndroid' "$FILE"
grep -q 'd_vectorEngineExecutesInsideAndroid' "$FILE"
grep -q 'AIF_ENGINE_GATE' "$FILE"
