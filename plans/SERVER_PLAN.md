# Server Plan — Pipecat Voice Pipeline

## Overview
Python server using Pipecat framework to handle real-time voice conversations over WebSocket. Receives raw audio from clients (app/web), runs through VAD → STT → LLM (OpenClaw) → TTS pipeline, streams audio back.

## Components

### 1. WebSocket Transport
- Accept WebSocket connections on configurable port (HTTPS)
- Protocol: Binary audio frames (16-bit PCM, 16kHz mono) + JSON control messages
- No auth needed — secured by SSL + firewall (personal server, not public)
- Handle multiple clients (though typically 1 at a time)

### 2. Call State Machine
Learned from OpenClaw's voice-call plugin — enforce valid state transitions:

```
initiated → ringing → answered → active → speaking ⇄ listening → [terminal]
```

Terminal states: `completed`, `hangup-user`, `hangup-bot`, `timeout`, `error`

Rules:
- Only forward transitions allowed (no going backwards)
- Speaking ⇄ Listening can cycle (multi-turn conversation)
- Terminal states are final — ignore further events
- Max duration timer: auto-hangup after 30 min (configurable)

Each call gets a `CallRecord` with:
- callId, state, startedAt, answeredAt, endedAt
- transcript[] (timestamped entries, speaker: "user" | "bot")
- Persisted to SQLite for history

### 3. Silero VAD (Voice Activity Detection)
- **THE key fix** — replaces dumb silence detection
- Silero V5 ONNX model (~2MB)
- Runs on 30ms audio chunks
- Detects speech start/end with ML accuracy
- Configurable `stop_secs` (how long silence = "done talking", default 0.6s)
- Filters out background noise (AC, fan, street) that currently triggers false transcriptions

### 4. Whisper STT (Speech to Text)
- Local Whisper (tiny or base model)
- Receives clean audio segments from VAD (not raw noisy stream)
- Only transcribes when VAD says "speech detected" — no more noise-as-sentences
- Streaming approach: accumulate VAD speech frames → on speech end → transcribe batch

### 5. OpenClaw LLM Integration
- HTTP POST to OpenClaw Chat Completions API (host/port from env vars)
- Uses gateway token for auth (from env vars)
- Sends user's transcribed text
- Receives Jarvis's response (streamed)
- Maintains conversation context (last N turns) for continuity within the call

### 6. Edge TTS (Text to Speech)
- Microsoft Edge TTS (free, no API key)
- Voice: en-GB-RyanNeural (British Ryan)
- Streaming: start playing audio before full response is generated
- Chunk response by sentence boundaries for faster first-byte

### 7. Call Sounds
- Pre-generated audio files in `sounds/` directory:
  - `ring.wav` — 0.7s phone ring tone
  - `pickup.wav` — phone pickup click
  - `greeting_morning.wav` — "Good morning, sir"
  - `greeting_afternoon.wav` — "Good afternoon, sir"
  - `greeting_evening.wav` — "Good evening, sir"
  - `greeting_night.wav` — "Good night, sir"
- Server sends appropriate greeting based on client's timezone (sent in connect message)

## Message Protocol (WebSocket)

### Client → Server
```json
// Control messages (JSON, text frame)
{"type": "connect", "timezone": "Asia/Jerusalem"}
{"type": "hangup"}

// Audio data (binary frames)
// Raw PCM 16-bit, 16kHz, mono
```

### Server → Client
```json
// Control messages (JSON, text frame)
{"type": "connected", "callId": "uuid", "greeting": "afternoon"}
{"type": "state", "state": "listening"}    // Call state changed
{"type": "transcript", "text": "..."}      // What the user said
{"type": "response_text", "text": "..."}   // Jarvis's text (for display)
{"type": "done"}                           // Response complete
{"type": "error", "message": "..."}

// Audio data (binary frames)
// Ring sound, pickup sound, greeting, TTS response audio
// Same format: PCM 16-bit, 16kHz, mono
```

## Environment Variables (.env)
```
# Server
HOST=0.0.0.0
PORT=<your-port>
SSL_CERT=/path/to/your/cert.crt
SSL_KEY=/path/to/your/key.key

# OpenClaw
OPENCLAW_URL=<your-openclaw-url>
OPENCLAW_TOKEN=<your-gateway-token>

# Whisper
WHISPER_MODEL=tiny

# VAD
VAD_STOP_SECS=0.6

# Call limits
MAX_CALL_DURATION_MIN=30
```

## File Structure
```
server/
├── main.py              # Entry point, WebSocket server, SSL
├── pipeline.py          # Pipecat pipeline assembly
├── openclaw_llm.py      # Custom LLM service for OpenClaw
├── call_state.py        # Call state machine + records
├── db.py                # SQLite for call logs
├── sounds/              # Pre-generated audio files
│   ├── ring.wav
│   ├── pickup.wav
│   └── greetings/
│       ├── morning.wav
│       ├── afternoon.wav
│       ├── evening.wav
│       └── night.wav
├── requirements.txt
├── .env.example
└── README.md
```

## Dependencies
```
pipecat-ai[silero]    # Core + Silero VAD (~40MB total)
aiohttp               # WebSocket server
edge-tts              # Free TTS
openai-whisper        # Local STT (already installed in voice-env)
python-dotenv         # Env files
```

## Latency Budget (realistic)
| Step | Estimate |
|------|----------|
| VAD speech end detection | ~100ms |
| Whisper tiny transcription | ~300ms |
| OpenClaw → Claude response (first token) | ~800-1500ms |
| Edge TTS first sentence | ~400ms |
| **Total speech-end to first-audio** | **~1.6-2.3s** |

This is acceptable for conversation. Phone calls to real humans have similar thinking pauses.

---

*Port: Choose an available port and add to ari-apps.md and UFW*
