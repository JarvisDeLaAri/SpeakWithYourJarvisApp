package ai.bresleveloper.jarvisvoice.audio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean

class AudioPlayer {
    companion object {
        const val SAMPLE_RATE = 16000
    }

    private var audioTrack: AudioTrack? = null
    private val audioQueue = ConcurrentLinkedQueue<ByteArray>()
    private val isPlaying = AtomicBoolean(false)
    private val _isActive = AtomicBoolean(false)
    private var playThread: Thread? = null
    private var bufferDrainMs = 200L

    /** True while audio is queued, being written, or draining from AudioTrack buffer */
    val isActive: Boolean get() = _isActive.get()

    fun start() {
        val bufferSize = AudioTrack.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(4096)

        // How long AudioTrack's internal buffer takes to drain
        bufferDrainMs = (bufferSize * 1000L) / (SAMPLE_RATE * 2)

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

        audioTrack?.play()
        isPlaying.set(true)

        playThread = Thread {
            while (isPlaying.get()) {
                val data = audioQueue.poll()
                if (data != null) {
                    audioTrack?.write(data, 0, data.size)
                    if (audioQueue.isEmpty()) {
                        // Queue drained but AudioTrack buffer still playing
                        Thread.sleep(bufferDrainMs)
                        // Recheck — new audio may have arrived during sleep
                        if (audioQueue.isEmpty()) {
                            _isActive.set(false)
                        }
                    }
                } else {
                    _isActive.set(false)
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
        _isActive.set(true)
    }

    fun stop() {
        isPlaying.set(false)
        _isActive.set(false)
        playThread?.join(1000)
        playThread = null
        audioQueue.clear()
        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
    }

    fun clearQueue() {
        audioQueue.clear()
        _isActive.set(false)
    }
}
