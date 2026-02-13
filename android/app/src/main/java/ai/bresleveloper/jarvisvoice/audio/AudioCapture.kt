package ai.bresleveloper.jarvisvoice.audio

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.NoiseSuppressor
import android.util.Log
import androidx.core.app.ActivityCompat
import android.content.Context
import java.nio.ByteBuffer
import java.nio.ByteOrder

class AudioCapture(private val context: Context) {
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL = AudioFormat.CHANNEL_IN_MONO
        const val ENCODING = AudioFormat.ENCODING_PCM_16BIT
        private const val TAG = "AudioCapture"
    }

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordThread: Thread? = null
    private var echoCanceler: AcousticEchoCanceler? = null
    private var noiseSuppressor: NoiseSuppressor? = null

    var onAudioData: ((ByteArray) -> Unit)? = null

    /** Set to true when bot is speaking to suppress mic data (Fix 3) */
    var muteWhileSpeaking = false

    fun start(): Boolean {
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            return false
        }

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL, ENCODING)
            .coerceAtLeast(4096)

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            SAMPLE_RATE,
            CHANNEL,
            ENCODING,
            bufferSize
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            audioRecord?.release()
            audioRecord = null
            return false
        }

        // Fix 2: Enable AcousticEchoCanceler
        val sessionId = audioRecord!!.audioSessionId
        if (AcousticEchoCanceler.isAvailable()) {
            echoCanceler = AcousticEchoCanceler.create(sessionId)?.also {
                it.enabled = true
                Log.i(TAG, "AcousticEchoCanceler enabled")
            }
        } else {
            Log.w(TAG, "AcousticEchoCanceler not available on this device")
        }

        // Bonus: enable noise suppressor too
        if (NoiseSuppressor.isAvailable()) {
            noiseSuppressor = NoiseSuppressor.create(sessionId)?.also {
                it.enabled = true
                Log.i(TAG, "NoiseSuppressor enabled")
            }
        }

        isRecording = true
        audioRecord?.startRecording()

        recordThread = Thread {
            val buffer = ShortArray(bufferSize / 2)
            while (isRecording) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: -1
                if (read > 0) {
                    // Fix 3: Skip sending audio while bot is speaking
                    if (muteWhileSpeaking) continue

                    val byteBuffer = ByteBuffer.allocate(read * 2)
                    byteBuffer.order(ByteOrder.LITTLE_ENDIAN)
                    for (i in 0 until read) {
                        byteBuffer.putShort(buffer[i])
                    }
                    onAudioData?.invoke(byteBuffer.array())
                }
            }
        }.apply {
            name = "AudioCapture"
            start()
        }

        return true
    }

    fun stop() {
        isRecording = false
        recordThread?.join(1000)
        recordThread = null
        echoCanceler?.release()
        echoCanceler = null
        noiseSuppressor?.release()
        noiseSuppressor = null
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
    }
}
