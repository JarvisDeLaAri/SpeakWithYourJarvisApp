# Task List — Step by Step (v2 — Fork Approach)

## Phase 1: Server (Plugin Fork)

### 1.1 Fork & Setup
- [ ] Copy `openclaw-source/extensions/voice-call/` to `server/`
- [ ] Review all existing source files — understand the architecture
- [ ] Map the provider interface (`VoiceCallProvider`)
- [ ] Map the STT interface (`RealtimeSTTSession`)
- [ ] Map the TTS interface (`TelephonyTtsProvider`)
- [ ] Set up TypeScript build (keep existing tsconfig)
- [ ] Create .env.example
- [ ] Create .gitignore

### 1.2 WebSocket Telephony Provider
- [ ] Create `src/providers/websocket.ts` implementing `VoiceCallProvider`
- [ ] WSS server on configurable port (using existing SSL cert pattern)
- [ ] Binary audio frame handling (PCM 16-bit, 16kHz mono)
- [ ] JSON control messages (connect, hangup, status)
- [ ] Register "websocket" in `resolveProvider()` in runtime.ts

### 1.3 Device Pairing & Auth
- [ ] JWT-based auth (jsonwebtoken package)
- [ ] POST `/api/pair` — generate 6-digit code, notify Jarvis via WhatsApp
- [ ] POST `/api/confirm` — verify code, return JWT
- [ ] SQLite or JSON file for paired devices
- [ ] WebSocket auth middleware (validate JWT on connect)

### 1.4 Edge TTS Adapter
- [ ] Create `src/tts-edge.ts` implementing `TelephonyTtsProvider`
- [ ] Edge TTS via npm package or Python subprocess
- [ ] Voice: en-GB-RyanNeural (configurable)
- [ ] Output: PCM buffer compatible with media stream
- [ ] Sentence chunking for streaming (split on sentence boundaries)
- [ ] Register in TTS config alongside existing providers

### 1.5 Whisper STT Adapter
- [ ] Create `src/stt-whisper.ts` implementing `RealtimeSTTSession`
- [ ] Silero VAD integration (ONNX runtime)
- [ ] Audio accumulation during speech
- [ ] On speech end → temp WAV → Whisper transcribe → callback
- [ ] `onSpeechStart` fires when VAD detects voice
- [ ] `onPartialTranscript` — optional, could skip for v1
- [ ] Register in STT config alongside existing providers

### 1.6 Call Sounds
- [ ] Generate greeting WAVs with Edge TTS (morning/afternoon/evening/night)
- [ ] Source or synthesize ring tone (0.7s)
- [ ] Source or synthesize pickup click sound
- [ ] Server sends appropriate sounds during call setup

### 1.7 Config Schema
- [ ] Extend config to accept provider: "websocket"
- [ ] Add websocket config block (port, ssl, jwt)
- [ ] Add stt.provider: "whisper" option
- [ ] Add tts.provider: "edge" option
- [ ] Document all config options

### 1.8 Integration & Testing
- [ ] Plugin loads in OpenClaw gateway
- [ ] End-to-end test: WebSocket connect → speak → VAD → STT → agent → TTS → audio back
- [ ] Verify no 8-second cuts (VAD working)
- [ ] Verify background noise filtered
- [ ] Verify interrupt/barge-in works
- [ ] Test CLI commands: `openclaw voicecall call/end/status`
- [ ] Measure latency: speech-end to first-audio (target: <2s)

---

## Phase 2: Web Client

### 2.1 UI
- [ ] Dark-themed single-page HTML
- [ ] Setup flow: server address, pairing code
- [ ] Big "Call Jarvis" button
- [ ] Status indicators (connecting, ringing, listening, responding)
- [ ] Transcript display
- [ ] Hang up button

### 2.2 Audio
- [ ] getUserMedia for microphone
- [ ] AudioWorklet for PCM extraction + resampling to 16kHz
- [ ] WebSocket binary frames for send/receive
- [ ] AudioContext playback with queue for gapless audio
- [ ] Play ring, pickup, greeting from server

### 2.3 Polish
- [ ] Pulse animation while listening
- [ ] Wave animation while Jarvis speaks
- [ ] Settings screen (re-pair, server config)
- [ ] Mobile responsive

---

## Phase 3: Android App

### 3.1 Project Setup
- [ ] Android Studio project (Kotlin, min SDK 26, target 34)
- [ ] Package: ai.bresleveloper.jarvisvoice
- [ ] OkHttp for WebSocket
- [ ] Permissions: RECORD_AUDIO, INTERNET, FOREGROUND_SERVICE

### 3.2 Setup Screen
- [ ] Server address + port input
- [ ] Pairing flow with 6-digit code
- [ ] JWT stored in Android Keystore
- [ ] Self-signed cert trust

### 3.3 Call Screen
- [ ] Big call button with animation
- [ ] AudioRecord (16kHz, 16-bit, mono)
- [ ] AudioTrack (low-latency playback)
- [ ] Ring → pickup → greeting → conversation
- [ ] Foreground service for background audio

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
1. **Phase 1** — Server plugin (the brain)
2. **Phase 2** — Web client (prove it works)
3. **Phase 3** — Android app (mobile experience)

---

*Created: 2026-02-12 (v2 — fork approach)*
*Author: Jarvis de la Ari 🦞*
