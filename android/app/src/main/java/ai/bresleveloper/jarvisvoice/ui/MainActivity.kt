package ai.bresleveloper.jarvisvoice.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import ai.bresleveloper.jarvisvoice.R
import ai.bresleveloper.jarvisvoice.audio.AudioCapture
import ai.bresleveloper.jarvisvoice.audio.AudioPlayer
import ai.bresleveloper.jarvisvoice.databinding.ActivityMainBinding
import ai.bresleveloper.jarvisvoice.network.WebSocketClient
import org.json.JSONObject
import java.util.TimeZone

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: Preferences

    private var wsClient: WebSocketClient? = null
    private var audioCapture: AudioCapture? = null
    private var audioPlayer: AudioPlayer? = null

    private val handler = Handler(Looper.getMainLooper())
    private var isInCall = false
    private var callStartTime = 0L
    private var timerRunnable: Runnable? = null

    companion object {
        private const val PERMISSION_REQUEST_CODE = 100
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = Preferences(this)

        // If no server URL, go to settings
        if (prefs.serverUrl.isEmpty()) {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        // Load saved VAD value
        binding.vadSlider.value = prefs.vadValue
        binding.vadValueText.text = "${prefs.vadValue}s"

        binding.callBtn.setOnClickListener { toggleCall() }
        binding.settingsBtn.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        binding.vadSlider.addOnChangeListener { _, value, _ ->
            binding.vadValueText.text = "${value}s"
            prefs.vadValue = value
            sendVadUpdate(value)
        }

        setStatus("Ready", R.color.text_secondary)
    }

    private fun toggleCall() {
        if (isInCall) {
            hangup()
        } else {
            startCall()
        }
    }

    private fun startCall() {
        val url = prefs.serverUrl
        if (url.isEmpty()) {
            Toast.makeText(this, "Set server URL in settings first", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, SettingsActivity::class.java))
            return
        }

        // Check permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.RECORD_AUDIO), PERMISSION_REQUEST_CODE
            )
            return
        }

        setStatus("Connecting...", R.color.text_secondary)
        updateCallButton(true)
        clearTranscript()

        // Start audio player
        audioPlayer = AudioPlayer().also { it.start() }

        // Start audio capture
        audioCapture = AudioCapture(this).also { capture ->
            capture.onAudioData = { data ->
                if (isInCall && audioPlayer?.isActive != true) {
                    wsClient?.sendBinary(data)
                }
            }
        }

        // Connect WebSocket
        wsClient = WebSocketClient().also { ws ->
            ws.onOpen = {
                handler.post {
                    isInCall = true
                    setStatus("Ringing", R.color.status_listening)
                    startTimer()

                    // Send connect message
                    val msg = JSONObject().apply {
                        put("type", "connect")
                        put("timezone", TimeZone.getDefault().id)
                    }
                    wsClient?.sendText(msg)

                    // Send initial VAD value
                    sendVadUpdate(prefs.vadValue)
                }

                // Start mic capture
                handler.post {
                    audioCapture?.start()
                }
            }

            ws.onTextMessage = { json ->
                handler.post { handleControl(json) }
            }

            ws.onBinaryMessage = { data ->
                audioPlayer?.queueAudio(data)
            }

            ws.onClose = {
                handler.post {
                    if (isInCall) endCall()
                }
            }

            ws.onError = { msg ->
                handler.post {
                    setStatus("Error: $msg", R.color.hangup_red)
                    endCall()
                }
            }

            ws.connect(url)
        }
    }

    private fun handleControl(json: JSONObject) {
        when (json.optString("type")) {
            "connected" -> setStatus("Ringing", R.color.status_listening)

            "state" -> {
                val state = json.optString("state")
                when (state) {
                    "listening" -> setStatus("Listening", R.color.status_listening)
                    "transcribing" -> setStatus("Transcribing", R.color.status_transcribing)
                    "thinking" -> setStatus("Thinking", R.color.status_thinking)
                    "speaking" -> setStatus("Speaking", R.color.status_speaking)
                    else -> setStatus(state.replaceFirstChar { it.uppercase() }, R.color.text_secondary)
                }
            }

            "transcript" -> {
                val text = json.optString("text")
                val silence = json.optJSONObject("silence")
                addTranscript("You", text, silence, isUser = true)
            }

            "response_text" -> {
                val text = json.optString("text")
                addTranscript("Jarvis", text, null, isUser = false)
            }

            "error" -> {
                val msg = json.optString("message")
                addTranscript("Jarvis", "⚠️ $msg", null, isUser = false)
            }
        }
    }

    private fun hangup() {
        wsClient?.sendText(JSONObject().apply { put("type", "hangup") })
        endCall()
    }

    private fun endCall() {
        isInCall = false
        audioCapture?.stop()
        audioCapture = null
        audioPlayer?.stop()
        audioPlayer = null
        wsClient?.close()
        wsClient = null
        stopTimer()
        updateCallButton(false)
        setStatus("Ready", R.color.text_secondary)
    }

    private fun setStatus(text: String, colorRes: Int) {
        binding.statusText.text = text
        binding.statusText.setTextColor(ContextCompat.getColor(this, colorRes))
    }

    private fun updateCallButton(inCall: Boolean) {
        if (inCall) {
            binding.callBtn.text = "📵 Hang Up"
            binding.callBtn.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.hangup_red))
        } else {
            binding.callBtn.text = "📞 Call Jarvis"
            binding.callBtn.backgroundTintList =
                ColorStateList.valueOf(ContextCompat.getColor(this, R.color.call_green))
        }
    }

    private fun addTranscript(speaker: String, text: String, silence: JSONObject?, isUser: Boolean) {
        val view = LayoutInflater.from(this).inflate(R.layout.item_transcript, binding.transcriptContainer, false)

        val speakerText = view.findViewById<TextView>(R.id.speakerText)
        val messageText = view.findViewById<TextView>(R.id.messageText)
        val silenceText = view.findViewById<TextView>(R.id.silenceText)

        speakerText.text = speaker
        speakerText.setTextColor(ContextCompat.getColor(this,
            if (isUser) R.color.status_listening else R.color.status_speaking))
        messageText.text = text

        if (silence != null && isUser) {
            silenceText.visibility = View.VISIBLE
            val parts = mutableListOf<String>()
            parts.add("⏱ ${silence.optDouble("audioDuration", 0.0)}s")

            val maxGap = silence.optDouble("maxGap", 0.0)
            val gapCount = silence.optInt("gapCount", 0)
            if (maxGap > 0) {
                parts.add("longest mid-pause: ${maxGap}s")
                parts.add("$gapCount pause${if (gapCount != 1) "s" else ""}")
            } else {
                parts.add("no mid-pauses")
            }

            val finalSilence = silence.optDouble("finalSilence", 0.0)
            if (finalSilence > 0) {
                parts.add("end silence: ${finalSilence}s")
            }

            if (silence.has("sttTime")) {
                parts.add("transcribe: ${silence.optDouble("sttTime")}s")
            }

            silenceText.text = parts.joinToString(" · ")
        }

        view.setBackgroundColor(ContextCompat.getColor(this,
            if (isUser) R.color.user_bubble else R.color.bot_bubble))

        binding.transcriptContainer.addView(view)

        // Auto-scroll
        binding.transcriptScroll.post {
            binding.transcriptScroll.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun clearTranscript() {
        binding.transcriptContainer.removeAllViews()
    }

    private fun sendVadUpdate(value: Float) {
        if (isInCall) {
            wsClient?.sendText(JSONObject().apply {
                put("type", "vad_stop")
                put("value", value.toDouble())
            })
        }
    }

    private fun startTimer() {
        callStartTime = System.currentTimeMillis()
        binding.timerText.visibility = View.VISIBLE
        timerRunnable = object : Runnable {
            override fun run() {
                val elapsed = (System.currentTimeMillis() - callStartTime) / 1000
                val min = (elapsed / 60).toString().padStart(2, '0')
                val sec = (elapsed % 60).toString().padStart(2, '0')
                binding.timerText.text = "$min:$sec"
                handler.postDelayed(this, 1000)
            }
        }
        handler.post(timerRunnable!!)
    }

    private fun stopTimer() {
        timerRunnable?.let { handler.removeCallbacks(it) }
        timerRunnable = null
        binding.timerText.visibility = View.GONE
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE && grantResults.isNotEmpty()
            && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startCall()
        } else {
            Toast.makeText(this, "Microphone permission required", Toast.LENGTH_LONG).show()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isInCall) endCall()
    }
}
