package ai.bresleveloper.jarvisvoice.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import ai.bresleveloper.jarvisvoice.databinding.ActivitySettingsBinding

class SettingsActivity : AppCompatActivity() {
    private lateinit var binding: ActivitySettingsBinding
    private lateinit var prefs: Preferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = Preferences(this)
        binding.serverUrlInput.setText(prefs.serverUrl)

        binding.saveBtn.setOnClickListener {
            val url = binding.serverUrlInput.text.toString().trim()
            if (url.isEmpty()) {
                Toast.makeText(this, "Please enter a server URL", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            prefs.serverUrl = url
            Toast.makeText(this, "Saved!", Toast.LENGTH_SHORT).show()
            finish()
        }

        binding.backBtn.setOnClickListener { finish() }
    }
}
