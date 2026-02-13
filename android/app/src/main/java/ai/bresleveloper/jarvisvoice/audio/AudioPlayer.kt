package ai.bresleveloper.jarvisvoice.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

class AudioPlayer {
    companion object {
        const val SAMPLE_RATE = 16000
    }

    private var audioTrack: AudioTrack? = null
    private val audioQueue = ConcurrentLinkedQueue<ByteArray>()
    private val isPlaying = AtomicBoolean(false)
    private var playThread: Thread? = null

    // Track total frames written vs played for accurate "done" detection
    private val totalFramesWritten = AtomicLong(0)

    /**
     * True if audio is queued OR AudioTrack is still playing buffered audio.
     * Only returns false when the speaker has truly finished outputting sound.
     */
    val isSpeaking: Boolean
        get() {
            if (audioQueue.isNotEmpty()) return true
            val track = audioTrack ?: return false
            val written = totalFramesWritten.get()
            if (written == 0L) return false
            return track.playbackHeadPosition < written
        }

    fun start() {
        val bufferSize = AudioTrack.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(4096)

        audioTrack = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setBufferSizeInBytes(bufferSize)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()

        totalFramesWritten.set(0)
        audioTrack?.play()
        isPlaying.set(true)

        playThread = Thread {
            while (isPlaying.get()) {
                val data = audioQueue.poll()
                if (data != null) {
                    audioTrack?.write(data, 0, data.size)
                    // 16-bit mono = 2 bytes per frame
                    totalFramesWritten.addAndGet((data.size / 2).toLong())
                } else {
                    Thread.sleep(10)
                }
            }
        }.apply {
            name = "AudioPlayer"
            start()
        }
    }

    fun queueAudio(data: ByteArray) {
        audioQueue.add(data)
    }

    fun stop() {
        isPlaying.set(false)
        playThread?.join(1000)
        playThread = null
        audioQueue.clear()
        totalFramesWritten.set(0)
        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
    }

    fun clearQueue() {
        audioQueue.clear()
    }
}
