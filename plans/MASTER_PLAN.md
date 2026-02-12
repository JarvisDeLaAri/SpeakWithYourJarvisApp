# SpeakWithYourJarvisApp — Master Plan

## Vision
A real-time voice conversation app where you press "Call Jarvis", hear a phone ring, and talk naturally — like calling a friend. Available as Android app, web app, and backed by a Pipecat-powered server that routes through OpenClaw (real Jarvis, full memory + personality).

## Architecture Overview

```
┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  Android App │    │   Web App    │    │   (Future)   │
│  (Kotlin)    │    │ (HTML/JS)    │    │  iOS App     │
└──────┬───────┘    └──────┬───────┘    └──────────────┘
       │                   │
       │    WebSocket      │    WebSocket
       └────────┬──────────┘
                ▼
     ┌─────────────────────┐
     │   Pipecat Server    │
     │   (Python)          │
     │                     │
     │  ┌───────────────┐  │
     │  │ Silero VAD    │  │  ← ML voice activity detection
     │  │ (ONNX, 2MB)   │  │
     │  └───────┬───────┘  │
     │          ▼          │
     │  ┌───────────────┐  │
     │  │ Whisper STT   │  │  ← Speech to text (local, free)
     │  │ (tiny/base)   │  │
     │  └───────┬───────┘  │
     │          ▼          │
     │  ┌───────────────┐  │
     │  │ OpenClaw API  │──┼──→ Main session (real Jarvis)
     │  │ (Chat Compl.) │  │
     │  └───────┬───────┘  │
     │          ▼          │
     │  ┌───────────────┐  │
     │  │ Edge TTS      │  │  ← Text to speech (free, British Ryan)
     │  │ (en-GB-Ryan)  │  │
     │  └───────────────┘  │
     └─────────────────────┘
```

## Project Structure

```
SpeakWithYourJarvisApp/
├── server/           # Pipecat voice server (Python)
│   ├── main.py       # Server entry point
│   ├── pipeline.py   # Pipecat pipeline config
│   ├── openclaw.py   # OpenClaw LLM integration
│   ├── auth.py       # Device pairing & confirmation codes
│   ├── sounds/       # Ring tone, pickup sound, greetings
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile    # Optional containerization
│
├── app/              # Android app (Kotlin)
│   ├── (Android Studio project)
│   ├── README.md     # Build & publish instructions
│   └── ...
│
├── web/              # Web client (HTML/CSS/JS)
│   ├── index.html    # Single page app
│   ├── style.css
│   ├── app.js        # WebSocket + audio handling
│   └── sounds/       # Client-side ring/pickup sounds
│
├── plans/            # This folder
│   ├── MASTER_PLAN.md
│   ├── SERVER_PLAN.md
│   ├── APP_PLAN.md
│   ├── WEB_PLAN.md
│   └── TASKS.md
│
├── .env.example      # Root env template
├── .gitignore
└── README.md
```

## Key Design Decisions

### 1. Pipecat over LiveKit
**Why:** Lighter (~40MB vs full media server), simpler pipeline model, easier OpenClaw integration, we're 1 user not a call center. Silero VAD (ONNX) fixes the 8-second cut problem without PyTorch (873MB).

### 2. WebSocket transport (not WebRTC)
**Why:** WebRTC requires STUN/TURN servers, ICE negotiation, complex NAT traversal. WebSocket over HTTPS is simpler, works through any firewall, and for 1-2 concurrent users the latency difference is negligible (~20ms). Our existing SSL cert works directly.

### 3. Local Whisper STT (not Deepgram)
**Why:** Free, no API key, no external dependency, no per-minute cost. We already use it. Tiny model is fast enough for real-time with VAD feeding clean audio segments.

### 4. Edge TTS (not ElevenLabs)
**Why:** Free, British Ryan voice already chosen, no API key. Good enough quality for conversation.

### 5. OpenClaw Chat Completions API for LLM
**Why:** Routes to main session = real Jarvis with full memory, personality, tools. Not a raw Claude API call with no context.

### 6. Device pairing with confirmation code
**Why:** Security. After app install, user enters server IP:port, server generates a 6-digit code, user confirms in app. Prevents random people from talking to your Jarvis. Paired devices get a persistent token stored locally.

### 7. Kotlin for Android (not React Native/Flutter)
**Why:** Native performance for audio handling, better microphone access, smaller APK, no JavaScript bridge latency for real-time audio. Ariel wants it on the Play Store — native is the right call.

### 8. Web client as standalone HTML/CSS/JS
**Why:** Consistent with our style (no frameworks). Works as fallback when you don't have the app. Same WebSocket protocol as the Android app.

## The Call Experience (UX Flow)

1. **Open app** → See "Call Jarvis" button (big, green, phone icon)
2. **Tap "Call Jarvis"** → Connect WebSocket to server
3. **Ring sound** plays (0.7s "tuuuu" tone) — feels like a real call
4. **Pickup sound** plays (click/soft tone)
5. **Jarvis greeting** plays: "Good morning/afternoon/evening/night, sir" (time-aware, pre-generated Edge TTS)
6. **Conversation begins** — full duplex, streaming, with proper VAD
7. **Hang up** → Tap red button or say "goodbye"

## Cost Analysis

| Component | Cost |
|-----------|------|
| Pipecat | Free (open source) |
| Silero VAD | Free (ONNX) |
| Whisper STT | Free (local) |
| Edge TTS | Free |
| OpenClaw/Claude | Already paying |
| Android Dev Account | $25 one-time |
| **Total ongoing** | **$0/month** |

## Google Play Store Requirements

- **Developer account**: $25 one-time fee, Google account required
- **App signing**: Google Play App Signing (mandatory)
- **Testing**: Personal accounts created after Nov 2023 need 12+ testers for 14+ days before public release
- **Content rating**: IARC questionnaire
- **Privacy policy**: Required (we handle voice data)
- **Target API level**: Must target recent Android API level
- **App bundle**: AAB format (not APK) for Play Store

## Phases

### Phase 1: Server (Pipecat pipeline)
Get the voice pipeline working: WebSocket → VAD → STT → OpenClaw → TTS → back

### Phase 2: Web Client
HTML/JS client that connects to the server. Prove the pipeline works end-to-end.

### Phase 3: Android App
Native Kotlin app with the same WebSocket protocol. Polish UX (call sounds, greeting).

### Phase 4: Play Store
Set up developer account, testing track, publish.

---

*Created: 2026-02-12*
*Author: Jarvis de la Ari 🦞*
