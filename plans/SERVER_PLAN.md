# Server Plan — Pipecat Voice Pipeline

## Overview
Python server using Pipecat framework to handle real-time voice conversations over WebSocket. Receives raw audio from clients (app/web), runs through VAD → STT → LLM (OpenClaw) → TTS pipeline, streams audio back.

## Components

### 1. WebSocket Transport
- Accept WebSocket connections on configurable port (HTTPS)
- Protocol: Binary audio frames (16-bit PCM, 16kHz mono) + JSON control messages
- Auth: Bearer token in connection handshake (from device pairing)
- Handle multiple clients (though typically 1 at a time)

### 2. Silero VAD (Voice Activity Detection)
- **THE key fix** — replaces dumb silence detection
- Silero V5 ONNX model (~2MB)
- Runs on 30ms audio chunks
- Detects speech start/end with ML accuracy
- Configurable `stop_secs` (how long silence = "done talking", default 0.6s)
- Filters out background noise (AC, fan, street) that currently triggers false transcriptions

### 3. Whisper STT (Speech to Text)
- Local Whisper (tiny or base model)
- Receives clean audio segments from VAD (not raw noisy stream)
- Only transcribes when VAD says "speech detected" — no more noise-as-sentences
- Streaming approach: accumulate VAD speech frames → on speech end → transcribe batch

### 4. OpenClaw LLM Integration
- HTTP POST to OpenClaw Chat Completions API (`/v1/chat/completions`)
- Uses gateway token for auth
- Sends user's transcribed text
- Receives Jarvis's response (streamed)
- Maintains conversation context (last N turns) for continuity within the call

### 5. Edge TTS (Text to Speech)
- Microsoft Edge TTS (free, no API key)
- Voice: en-GB-RyanNeural (British Ryan)
- Streaming: start playing audio before full response is generated
- Chunk response by sentence boundaries for faster first-byte

### 6. Device Pairing & Auth
- `/api/pair` endpoint: client sends device name → server generates 6-digit code
- Server logs code to console + sends to Jarvis (WhatsApp notification)
- `/api/confirm` endpoint: client sends code → server returns persistent JWT token
- All subsequent WebSocket connections require valid token
- Paired devices stored in SQLite

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
{"type": "connect", "token": "jwt...", "timezone": "Asia/Jerusalem"}
{"type": "hangup"}

// Audio data (binary frames)
// Raw PCM 16-bit, 16kHz, mono
```

### Server → Client
```json
// Control messages (JSON, text frame)
{"type": "connected", "greeting": "afternoon"}
{"type": "listening"}           // VAD detected speech start
{"type": "processing"}          // VAD detected speech end, transcribing
{"type": "transcript", "text": "..."} // What the user said
{"type": "responding"}          // Jarvis is generating response
{"type": "response_text", "text": "..."}  // Jarvis's text (for display)
{"type": "done"}                // Response complete
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
SSL_CERT=/etc/ssl/apps/server.crt
SSL_KEY=/etc/ssl/apps/server.key

# OpenClaw
OPENCLAW_HOST=127.0.0.1
OPENCLAW_PORT=28789
OPENCLAW_TOKEN=<gateway-token>

# Whisper
WHISPER_MODEL=tiny

# VAD
VAD_STOP_SECS=0.6

# Auth
JWT_SECRET=<random-secret>
```

## File Structure
```
server/
├── main.py              # Entry point, WebSocket server, SSL
├── pipeline.py          # Pipecat pipeline assembly
├── openclaw_llm.py      # Custom LLM service for OpenClaw
├── auth.py              # Device pairing, JWT tokens
├── db.py                # SQLite for paired devices + call logs
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
PyJWT                 # Token auth
python-dotenv         # Env files
```

---

*Port: Choose an available port and add to ari-apps.md and UFW*
