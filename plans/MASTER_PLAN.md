# SpeakWithYourJarvisApp — Master Plan

## Vision
A real-time voice conversation app where you press "Call Jarvis", hear a phone ring, and talk naturally — like calling a friend. Available as Android app, web app, and backed by a Pipecat-powered server that routes through OpenClaw (real Jarvis, full memory + personality).

## Architecture Overview

```
┌──────────────┐    ┌──────────────┐
│  Android App │    │   Web Client  │
│  (Kotlin)    │    │ (HTML/JS)     │
└──────┬───────┘    └──────┬────────┘
       │                   │
       │    WebSocket (WSS) │
       └────────┬──────────┘
                ▼
     ┌─────────────────────┐
     │  Pipecat Server     │
     │  (Python)           │
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
│   ├── sounds/       # Ring tone, pickup sound, greetings
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile    # Optional containerization
│
├── app/              # Android app (Kotlin)
│   ├── (Android Studio project)
│   ├── README.md     # Build & install instructions
│   └── ...
│
├── web/              # Web client (HTML/CSS/JS)
│   ├── index.html    # Single page app
│   ├── style.css
│   ├── app.js        # WebSocket + audio handling
│   └── sounds/       # Client-side ring/pickup sounds
│
├── plans/            # This folder
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

### 6. No pairing / no setup for web
**Why:** Web client is served from the same server. If you can reach the page, you can talk. SSL + firewall is enough security for personal use.

### 7. Simple IP:port config for Android
**Why:** Enter server address once, stored forever. No pairing ceremony, no confirmation codes. It's your personal Jarvis — keep it simple.

### 8. Kotlin for Android (not React Native/Flutter)
**Why:** Native performance for audio handling, better microphone access, smaller APK, no JavaScript bridge latency for real-time audio.

### 9. Web client as standalone HTML/CSS/JS
**Why:** Consistent with our style (no frameworks). Works as fallback when you don't have the app. Same WebSocket protocol as the Android app.

### 10. Call state machine (learned from OpenClaw voice-call plugin)
**Why:** OpenClaw's voice-call plugin uses a strict state machine: `initiated → ringing → answered → active → speaking ⇄ listening → ended`. This prevents race conditions (e.g. sending audio while disconnecting). We adopt this pattern — simpler than OpenClaw's (no phone-network states) but same principle: enforce valid transitions, never process events in terminal states.

### 11. Transcript logging per call
**Why:** OpenClaw's plugin logs every transcript entry with timestamp + speaker. We do the same — call history stored in SQLite. Useful for debugging and review.

### 12. Max duration timer
**Why:** OpenClaw's plugin has a safety timer that auto-hangs up after N minutes. We add this too — prevents runaway calls (e.g. phone left on, background noise loop). Default 30 min.

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
| **Total ongoing** | **$0/month** |

## Phases

### Phase 1: Server (Pipecat pipeline)
Get the voice pipeline working: WebSocket → VAD → STT → OpenClaw → TTS → back

### Phase 2: Web Client
HTML/JS client that connects to the server. Prove the pipeline works end-to-end.

### Phase 3: Android App
Native Kotlin app with the same WebSocket protocol. Polish UX (call sounds, greeting).

### Phase 4: Distribute
Generate signed APK, host on server for direct download. Optional Play Store later.

---

*Created: 2026-02-12*
*Author: Jarvis de la Ari 🦞*
