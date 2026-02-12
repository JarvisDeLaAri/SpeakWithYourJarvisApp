# Android App Plan — SpeakWithYourJarvisApp

## Overview
Native Android app (Kotlin) that connects to the Pipecat voice server over WebSocket. Simple UI: one big "Call Jarvis" button. Handles microphone capture and audio playback natively for lowest latency.

## UX Flow

### First Launch (Setup)
1. Welcome screen: "Connect to Your Jarvis"
2. Input fields: Server IP/hostname, Port
3. Tap "Connect" → verifies server is reachable (/api/health)
4. "Connected! ✅" → navigate to main screen
5. Server address stored locally forever (SharedPreferences)

### Main Screen
1. Big green circle button: 📞 "Call Jarvis"
2. Tap → button turns red, text changes to "Calling..."
3. Ring sound plays (0.7s)
4. Pickup sound plays
5. Jarvis greeting plays ("Good afternoon, sir")
6. Status: "Connected — Speak now"
7. Visual: pulsing animation when listening, different animation when Jarvis speaks
8. Transcript area: shows what you said + what Jarvis said
9. Call duration timer
10. Red "Hang Up" button to end call

### Settings Screen
- Server address (IP:port) — change if needed
- Audio settings (volume, etc.)
- About

## Technical Architecture

### Audio Capture
- `AudioRecord` API (Android native)
- Format: 16-bit PCM, 16kHz, mono
- Continuous recording while call is active
- Send raw PCM frames over WebSocket (binary)

### Audio Playback
- `AudioTrack` API (Android native)
- Plays incoming PCM audio from server (ring, pickup, greeting, TTS)
- Low-latency mode for real-time conversation feel

### WebSocket
- OkHttp WebSocket client (standard Android library)
- HTTPS/WSS with self-signed cert support (trust custom CA on first connect)
- Auto-reconnect on disconnect
- Binary frames for audio, text frames for JSON control messages

### Security
- Self-signed SSL cert: trust on first use (TOFU)
- Server address stored in SharedPreferences
- SSL protects the connection — if you know the IP:port, you're in

### Permissions
- `RECORD_AUDIO` — microphone access
- `INTERNET` — server communication
- `FOREGROUND_SERVICE` — keep call alive when screen off

## Screen Layouts

### 1. Setup Screen
```
┌─────────────────────────┐
│   🦞 Jarvis Voice       │
│                         │
│  Server Address:        │
│  ┌───────────────────┐  │
│  │ your-server-ip    │  │
│  └───────────────────┘  │
│  Port:                  │
│  ┌───────────────────┐  │
│  │ <your-port>       │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │    Connect        │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### 2. Main Call Screen
```
┌─────────────────────────┐
│   🦞 Jarvis      02:34  │
│                         │
│        ┌─────┐          │
│        │     │          │
│        │ 📞  │  ← big   │
│        │     │    green  │
│        └─────┘          │
│    "Call Jarvis"        │
│                         │
│  ── Transcript ──────── │
│  You: "What's the..."  │
│  Jarvis: "Good after.." │
│                         │
│         ⚙️               │
└─────────────────────────┘
```

## Project Structure (Android Studio)
```
app/
├── src/main/
│   ├── java/ai/bresleveloper/jarvisvoice/
│   │   ├── MainActivity.kt
│   │   ├── SetupActivity.kt
│   │   ├── CallActivity.kt
│   │   ├── audio/
│   │   │   ├── AudioCapture.kt      # Mic recording
│   │   │   └── AudioPlayer.kt       # Playback
│   │   ├── network/
│   │   │   └── WebSocketClient.kt   # WS connection
│   │   └── storage/
│   │       └── Preferences.kt       # SharedPreferences wrapper
│   ├── res/
│   │   ├── layout/
│   │   │   ├── activity_setup.xml
│   │   │   └── activity_call.xml
│   │   ├── raw/                     # Ring/pickup sounds
│   │   └── values/
│   └── AndroidManifest.xml
├── build.gradle.kts
└── README.md
```

## Dependencies (Gradle)
```kotlin
implementation("com.squareup.okhttp3:okhttp:4.12.0")  // WebSocket
implementation("com.google.android.material:material:1.11.0")  // UI
```

## Distribution
- **Primary**: Signed APK hosted on the server itself for direct download
- **Optional**: Google Play Store ($25 one-time, 14-day testing requirement for personal accounts)

---

*Package name: ai.bresleveloper.jarvisvoice*
