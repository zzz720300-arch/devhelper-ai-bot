#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
mkdir -p "$ROOT/app/src/androidTest/java/ru/quantai/imagefinisher/app"
cat > "$ROOT/app/src/androidTest/java/ru/quantai/imagefinisher/app/EngineGateInstrumentedTest.kt" <<'AIFV5_EOF'
package ru.quantai.imagefinisher.app

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import ru.quantai.imagefinisher.core.engine.EngineHealth
import ru.quantai.imagefinisher.core.engine.EngineStatus
import ru.quantai.imagefinisher.integration.ImageFinisherEngines

@RunWith(AndroidJUnit4::class)
class EngineGateInstrumentedTest {
    private val context: Context
        get() = ApplicationProvider.getApplicationContext()

    private fun assertReady(health: EngineHealth) {
        assertEquals(
            "${health.engine}: ${health.message}; details=${health.details}",
            EngineStatus.READY,
            health.status
        )
    }

    @Test
    fun resizeEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).resize.selfTest())
    }

    @Test
    fun backgroundEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).background.selfTest())
    }

    @Test
    fun upscaleX2AndX4ExecuteInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).upscale.selfTest())
    }

    @Test
    fun vectorEngineExecutesInsideAndroid() = runBlocking {
        assertReady(ImageFinisherEngines(context).vector.selfTest())
    }
}
AIFV5_EOF
