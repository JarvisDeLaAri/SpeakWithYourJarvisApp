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
    private val _isSpeaking = AtomicBoolean(false)
    private var playThread: Thread? = null

    /** True while TTS audio is actively being played */
    val isSpeaking: Boolean get() = _isSpeaking.get()

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

        audioTrack?.play()
        isPlaying.set(true)

        playThread = Thread {
            while (isPlaying.get()) {
                val data = audioQueue.poll()
                if (data != null) {
                    _isSpeaking.set(true)
                    audioTrack?.write(data, 0, data.size)
                    if (audioQueue.isEmpty()) {
                        _isSpeaking.set(false)
                    }
                } else {
                    _isSpeaking.set(false)
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
        _isSpeaking.set(true)
    }

    fun stop() {
        isPlaying.set(false)
        _isSpeaking.set(false)
        playThread?.join(1000)
        playThread = null
        audioQueue.clear()
        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
    }

    fun clearQueue() {
        audioQueue.clear()
        _isSpeaking.set(false)
    }
}
