# Android App Plan — SpeakWithYourJarvisApp

## Overview
Native Android app (Kotlin) that connects to the Pipecat voice server over WebSocket. Simple UI: one big "Call Jarvis" button. Handles microphone capture, audio playback, and device pairing.

## UX Flow

### First Launch (Setup)
1. Welcome screen: "Connect to Your Jarvis"
2. Input fields: Server IP/hostname, Port
3. Tap "Connect" → app sends pairing request
4. Server generates 6-digit code → shows in Jarvis's WhatsApp
5. App shows: "Enter the confirmation code Jarvis sent you"
6. User enters code → app receives JWT token → stored securely
7. "Connected! ✅" → navigate to main screen

### Main Screen
1. Big green circle button: 📞 "Call Jarvis"
2. Tap → button turns red, text changes to "Calling..."
3. Ring sound plays (0.7s)
4. Pickup sound plays
5. Jarvis greeting plays ("Good afternoon, sir")
6. Status: "Connected — Speak now"
7. Visual: pulsing animation when listening, different animation when Jarvis speaks
8. Transcript area: shows what you said + what Jarvis said
9. Red "Hang Up" button to end call

### Settings Screen
- Server address (IP:port)
- Re-pair device
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
- HTTPS/WSS with self-signed cert support (trust custom CA)
- Auto-reconnect on disconnect
- Binary frames for audio, text frames for JSON control messages

### Security
- JWT token stored in Android Keystore (encrypted)
- Self-signed SSL cert: user accepts on first connect (TOFU model)
- No credentials in app code — everything from pairing flow

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
│  │ your-server-ip     │  │
│  └───────────────────┘  │
│  Port:                  │
│  ┌───────────────────┐  │
│  │ <your-port>             │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │    Connect        │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### 2. Confirmation Code Screen
```
┌─────────────────────────┐
│                         │
│  Jarvis sent you a code │
│                         │
│     ┌─┐┌─┐┌─┐┌─┐┌─┐┌─┐│
│     │ ││ ││ ││ ││ ││ ││
│     └─┘└─┘└─┘└─┘└─┘└─┘│
│                         │
│  ┌───────────────────┐  │
│  │    Confirm        │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### 3. Main Call Screen
```
┌─────────────────────────┐
│   🦞 Jarvis             │
│                         │
│        ┌─────┐          │
│        │     │          │
│        │ 📞  │  ← big   │
│        │     │    green  │
│        └─────┘          │
│    "Call Jarvis"        │
│                         │
│  ── Recent ──────────── │
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
│   │   │   ├── WebSocketClient.kt   # WS connection
│   │   │   └── PairingService.kt    # Device pairing
│   │   └── storage/
│   │       └── TokenStore.kt        # Secure JWT storage
│   ├── res/
│   │   ├── layout/
│   │   │   ├── activity_setup.xml
│   │   │   ├── activity_call.xml
│   │   │   └── activity_confirm.xml
│   │   ├── raw/                     # Ring/pickup sounds
│   │   └── values/
│   └── AndroidManifest.xml
├── build.gradle.kts
└── README.md
```

## Dependencies (Gradle)
```kotlin
implementation("com.squareup.okhttp3:okhttp:4.12.0")  // WebSocket
implementation("androidx.security:security-crypto:1.1.0-alpha06")  // Keystore
implementation("com.google.android.material:material:1.11.0")  // UI
```

## Play Store Publishing Requirements
1. Google Play Developer Account ($25 one-time)
2. App signed with Play App Signing
3. AAB format (Android App Bundle)
4. Content rating (IARC)
5. Privacy policy URL
6. Testing: 12+ testers, 14+ days closed testing (personal accounts)
7. Target API level: 34+ (Android 14)
8. Minimum SDK: 26 (Android 8.0)

---

*Package name: ai.bresleveloper.jarvisvoice*
