package ai.bresleveloper.jarvisvoice.ui

import android.content.Context
import android.content.SharedPreferences

class Preferences(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("jarvis_prefs", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server_url", "") ?: ""
        set(value) = prefs.edit().putString("server_url", value).apply()

    var vadValue: Float
        get() = prefs.getFloat("vad_value", 2.0f)
        set(value) = prefs.edit().putFloat("vad_value", value).apply()
}
