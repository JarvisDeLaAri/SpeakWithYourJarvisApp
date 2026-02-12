# Task List — Step by Step

## Phase 1: Server (Pipecat Pipeline)

### 1.1 Project Setup
- [ ] Create Python virtual environment
- [ ] Install pipecat-ai[silero], aiohttp, edge-tts, PyJWT, python-dotenv
- [ ] Verify Silero VAD loads (ONNX, no PyTorch)
- [ ] Create .env.example with all config vars
- [ ] Create .gitignore (venv, .env, __pycache__, *.pyc, db files)

### 1.2 WebSocket Server
- [ ] Basic aiohttp server with HTTPS (using existing SSL cert)
- [ ] WebSocket endpoint `/ws` accepting binary + text frames
- [ ] Health check endpoint `/api/health`
- [ ] Static file serving for web client at `/`
- [ ] Connection lifecycle: connect → auth → active → hangup

### 1.3 Device Pairing
- [ ] SQLite database for paired devices (device_name, token, paired_at)
- [ ] POST `/api/pair` — generate 6-digit code, store pending, return device_id
- [ ] POST `/api/confirm` — verify code, return JWT token
- [ ] Notification to Jarvis (WhatsApp) when new pairing requested
- [ ] JWT validation middleware for WebSocket connections

### 1.4 Pipecat Pipeline — VAD
- [ ] Initialize Silero VAD (ONNX)
- [ ] Feed incoming audio frames to VAD
- [ ] Detect speech start → send {"type": "listening"} to client
- [ ] Detect speech end → collect speech frames → pass to STT
- [ ] Configure stop_secs (0.6s default, configurable)

### 1.5 Pipecat Pipeline — STT
- [ ] Load Whisper model (tiny, from existing voice-env or fresh)
- [ ] Receive clean audio segments from VAD
- [ ] Transcribe → send {"type": "transcript", "text": "..."} to client
- [ ] Handle empty transcriptions (VAD false positive) gracefully

### 1.6 Pipecat Pipeline — LLM (OpenClaw)
- [ ] Custom Pipecat LLM service class for OpenClaw Chat Completions API
- [ ] POST to OpenClaw Chat Completions endpoint (configured via OPENCLAW_HOST and OPENCLAW_PORT env vars)
- [ ] Include OPENCLAW_TOKEN from env in Authorization header
- [ ] Maintain conversation history (last 10 turns per call)
- [ ] Stream response for faster first-word
- [ ] Send {"type": "response_text", "text": "..."} to client

### 1.7 Pipecat Pipeline — TTS
- [ ] Edge TTS integration (en-GB-RyanNeural)
- [ ] Stream TTS audio as PCM frames back to client
- [ ] Sentence-boundary chunking for faster first-audio

### 1.8 Call Sounds
- [ ] Generate ring.wav (0.7s phone ring tone) using synthesizer or download free sound
- [ ] Generate pickup.wav (phone pickup click)
- [ ] Generate 4 greeting WAVs using Edge TTS:
  - "Good morning, sir"
  - "Good afternoon, sir"
  - "Good evening, sir"  
  - "Good night, sir"
- [ ] Server sends appropriate greeting based on client timezone

### 1.9 Integration Test
- [ ] End-to-end test: WebSocket → speak → VAD → STT → OpenClaw → TTS → audio back
- [ ] Verify no 8-second cuts
- [ ] Verify background noise doesn't trigger false transcriptions
- [ ] Verify interrupt handling (speak while Jarvis is talking)
- [ ] Measure latency: speech-end to first-audio-back (target: <2s)

---

## Phase 2: Web Client

### 2.1 Setup Flow
- [ ] Dark-themed HTML page with setup form (server address, port)
- [ ] Pairing flow: request code → enter code → store JWT in localStorage
- [ ] Store server config in localStorage
- [ ] "Connected" confirmation with transition to call screen

### 2.2 Call Interface
- [ ] Big "Call Jarvis" button (green, centered)
- [ ] WebSocket connection on button tap
- [ ] Play ring sound (0.7s) from local file or server stream
- [ ] Play pickup sound
- [ ] Play greeting audio from server
- [ ] Status indicator: Connecting → Ringing → Listening → Processing → Responding

### 2.3 Audio Pipeline
- [ ] getUserMedia for microphone access
- [ ] AudioWorklet or ScriptProcessorNode for raw PCM extraction
- [ ] Resample to 16kHz mono if needed
- [ ] Send binary frames over WebSocket
- [ ] Receive binary audio frames and play through AudioContext
- [ ] Queue management for gapless playback

### 2.4 Transcript Display
- [ ] Show user's speech (from server transcript messages)
- [ ] Show Jarvis's responses (from server response_text messages)
- [ ] Auto-scroll, recent at bottom

### 2.5 Polish
- [ ] Pulse animation while listening
- [ ] Different animation while Jarvis speaks
- [ ] Hang up button (red)
- [ ] Settings gear → re-pair, change server
- [ ] Mobile responsive (works on phone browser too)

---

## Phase 3: Android App

### 3.1 Project Setup
- [ ] Create Android Studio project (Kotlin, min SDK 26, target 34)
- [ ] Package name: ai.bresleveloper.jarvisvoice
- [ ] Add OkHttp dependency
- [ ] Add Material Design components
- [ ] Configure app permissions (RECORD_AUDIO, INTERNET, FOREGROUND_SERVICE)

### 3.2 Setup Screen
- [ ] Layout: server address input, port input, Connect button
- [ ] Network discovery or manual entry
- [ ] SSL certificate trust (accept self-signed on first connect)
- [ ] Pairing flow → confirmation code → store JWT in Android Keystore

### 3.3 Call Screen
- [ ] Big call button with animation
- [ ] AudioRecord for microphone capture (16kHz, 16-bit, mono)
- [ ] AudioTrack for playback (low-latency mode)
- [ ] OkHttp WebSocket client
- [ ] Same protocol as web client
- [ ] Foreground service to keep call alive

### 3.4 Audio Management
- [ ] AudioFocus handling (pause media, duck audio)
- [ ] Bluetooth headset support
- [ ] Speaker/earpiece toggle
- [ ] Volume control

### 3.5 Polish
- [ ] App icon (lobster 🦞 themed)
- [ ] Splash screen
- [ ] Call notification (ongoing, with hang up action)
- [ ] Haptic feedback on button taps
- [ ] Error handling (server unreachable, auth expired, etc.)

### 3.6 Build
- [ ] Generate signed AAB (Android App Bundle)
- [ ] Test on physical device
- [ ] ProGuard/R8 minification

---

## Phase 4: Play Store

### 4.1 Developer Account
- [ ] Create Google Play Developer account ($25)
- [ ] Verify identity

### 4.2 Store Listing
- [ ] App title: "Speak With Your Jarvis"
- [ ] Description (short + full)
- [ ] Screenshots (phone + tablet if applicable)
- [ ] Feature graphic (1024x500)
- [ ] App icon (512x512)
- [ ] Privacy policy URL
- [ ] Content rating (IARC questionnaire)

### 4.3 Testing Track
- [ ] Upload AAB to internal testing track
- [ ] Add 12+ testers (email addresses)
- [ ] Run closed testing for 14+ days (Google requirement for personal accounts)

### 4.4 Production Release
- [ ] Promote from testing to production
- [ ] Review and publish

---

## Priority Order
1. **Server** first — this is the brain
2. **Web client** second — fastest way to test end-to-end
3. **Android app** third — once server+web are proven
4. **Play Store** fourth — once app is polished

---

*Created: 2026-02-12*
*Author: Jarvis de la Ari 🦞*
