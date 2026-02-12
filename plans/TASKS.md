# Task List — Step by Step

## Phase 1: Server (Pipecat Pipeline)

### 1.1 Project Setup
- [ ] Create Python virtual environment
- [ ] Install pipecat-ai[silero], aiohttp, edge-tts, python-dotenv
- [ ] Verify Silero VAD loads (ONNX, no PyTorch)
- [ ] Verify Whisper loads (tiny model)
- [ ] Create .env.example with all config vars
- [ ] Create .gitignore (venv, .env, __pycache__, *.pyc, db files)

### 1.2 Call State Machine
- [ ] Implement state enum: initiated, ringing, answered, active, speaking, listening, + terminal states
- [ ] Forward-only transitions (no backwards)
- [ ] Speaking ⇄ Listening cycling for multi-turn
- [ ] Terminal states are final — reject further events
- [ ] CallRecord: callId, state, startedAt, answeredAt, endedAt, transcript[]
- [ ] Max duration timer (30 min default, configurable via env)
- [ ] SQLite persistence for call history

### 1.3 WebSocket Server
- [ ] aiohttp server with HTTPS (SSL cert from env vars)
- [ ] WebSocket endpoint `/ws`
- [ ] Health check endpoint `/api/health`
- [ ] Static file serving for web client at `/`
- [ ] Connection lifecycle: connect → ring → pickup → greeting → active → hangup
- [ ] No auth required (SSL + firewall = security)

### 1.4 Pipecat Pipeline — VAD
- [ ] Initialize Silero VAD (ONNX)
- [ ] Feed incoming audio frames to VAD
- [ ] Detect speech start → send state change to client
- [ ] Detect speech end → collect speech frames → pass to STT
- [ ] Configure stop_secs (0.6s default, configurable via env)

### 1.5 Pipecat Pipeline — STT
- [ ] Load Whisper model (tiny, configurable via env)
- [ ] Receive clean audio segments from VAD
- [ ] Transcribe → send transcript to client
- [ ] Handle empty transcriptions (VAD false positive) gracefully

### 1.6 Pipecat Pipeline — LLM (OpenClaw)
- [ ] Custom Pipecat LLM service for OpenClaw Chat Completions API
- [ ] POST to OPENCLAW_URL (from env)
- [ ] Include OPENCLAW_TOKEN in Authorization header (from env)
- [ ] Maintain conversation history (last 10 turns per call)
- [ ] Stream response for faster first-word
- [ ] Send response text to client for transcript display

### 1.7 Pipecat Pipeline — TTS
- [ ] Edge TTS integration (en-GB-RyanNeural)
- [ ] Stream TTS audio as PCM frames back to client
- [ ] Sentence-boundary chunking for faster first-audio

### 1.8 Call Sounds
- [ ] Generate 4 greeting WAVs using Edge TTS (morning/afternoon/evening/night)
- [ ] Source or synthesize ring tone (0.7s)
- [ ] Source or synthesize pickup click sound
- [ ] Server sends appropriate greeting based on client timezone

### 1.9 Integration Test
- [ ] End-to-end: WebSocket → speak → VAD → STT → OpenClaw → TTS → audio back
- [ ] Verify no 8-second cuts (VAD working)
- [ ] Verify background noise doesn't trigger false transcriptions
- [ ] Verify interrupt handling (speak while Jarvis is talking)
- [ ] Measure latency: speech-end to first-audio (target: <2.5s)
- [ ] Verify max duration timer auto-hangup works

---

## Phase 2: Web Client

### 2.1 Call Interface
- [ ] Dark-themed single-page HTML (served from the Pipecat server itself)
- [ ] Big "Call Jarvis" button (green, centered)
- [ ] Status indicator: Connecting → Ringing → Listening → Processing → Responding
- [ ] Transcript display (user + Jarvis, timestamped)
- [ ] Hang up button (red)
- [ ] No setup needed — page connects to its own server

### 2.2 Audio Pipeline
- [ ] getUserMedia for microphone access
- [ ] AudioWorklet for raw PCM extraction
- [ ] Resample to 16kHz mono if needed
- [ ] Send binary frames over WebSocket
- [ ] Receive binary audio frames and play through AudioContext
- [ ] Queue management for gapless playback

### 2.3 Polish
- [ ] Pulse animation while listening
- [ ] Different animation while Jarvis speaks
- [ ] Play ring + pickup sounds from server
- [ ] Mobile responsive
- [ ] Call duration timer display

---

## Phase 3: Android App

### 3.1 Project Setup
- [ ] Android Studio project (Kotlin, min SDK 26, target 34)
- [ ] Package: ai.bresleveloper.jarvisvoice
- [ ] OkHttp for WebSocket
- [ ] Permissions: RECORD_AUDIO, INTERNET, FOREGROUND_SERVICE

### 3.2 Setup Screen
- [ ] Server address + port input (one-time, stored in SharedPreferences)
- [ ] Connection test (hit /api/health)
- [ ] Self-signed cert trust (TOFU)

### 3.3 Call Screen
- [ ] Big call button with animation
- [ ] AudioRecord (16kHz, 16-bit, mono)
- [ ] AudioTrack (low-latency playback)
- [ ] Ring → pickup → greeting → conversation
- [ ] Foreground service for background audio
- [ ] Call duration display

### 3.4 Polish
- [ ] App icon (🦞 themed)
- [ ] Call notification with hang up action
- [ ] Bluetooth headset support
- [ ] Speaker/earpiece toggle

### 3.5 Build & Distribute
- [ ] Generate signed APK
- [ ] Host APK on server for direct download
- [ ] Test on physical device
- [ ] Optional: Play Store ($25, 14-day testing)

---

## Priority Order
1. **Phase 1** — Server (the brain)
2. **Phase 2** — Web client (prove it works)
3. **Phase 3** — Android app (mobile experience)

---

*Created: 2026-02-12*
*Author: Jarvis de la Ari 🦞*
