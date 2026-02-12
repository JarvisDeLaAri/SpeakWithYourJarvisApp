# SpeakWithYourJarvisApp — Master Plan (v2)

## Vision
A real-time voice conversation app where you press "Call Jarvis", hear a phone ring, and talk naturally. Built by **forking OpenClaw's voice-call plugin** and swapping paid components (Twilio, ElevenLabs, OpenAI STT) for free alternatives.

## Key Insight
OpenClaw already has a production voice-call plugin with call lifecycle, conversation state, interrupt detection, audio streaming, barge-in, and full agent integration. We don't build from zero — we swap 3 components:

| Layer | OpenClaw Default (paid) | Our Swap (free) |
|-------|------------------------|-----------------|
| Telephony | Twilio / Telnyx / Plivo | WebSocket direct (no phone network) |
| TTS | ElevenLabs / OpenAI | Edge TTS (en-GB-RyanNeural) |
| STT | OpenAI Realtime API | Local Whisper (tiny/base) |

## Architecture

```
┌──────────────┐    ┌──────────────┐
│  Android App │    │   Web Client  │
│  (Kotlin)    │    │ (HTML/JS)     │
└──────┬───────┘    └──────┬────────┘
       │    WebSocket (WSS) │
       └────────┬───────────┘
                ▼
     ┌──────────────────────────┐
     │  OpenClaw Gateway        │
     │                          │
     │  voice-call-free plugin  │  ← Our fork
     │  ┌────────────────────┐  │
     │  │ WebSocket Provider │  │  ← Replaces Twilio
     │  │ (direct connect)   │  │
     │  └────────┬───────────┘  │
     │           ▼              │
     │  ┌────────────────────┐  │
     │  │ Whisper STT        │  │  ← Replaces OpenAI Realtime
     │  │ (local, free)      │  │
     │  └────────┬───────────┘  │
     │           ▼              │
     │  ┌────────────────────┐  │
     │  │ Main Session (me!) │  │  ← Real Jarvis, full memory
     │  └────────┬───────────┘  │
     │           ▼              │
     │  ┌────────────────────┐  │
     │  │ Edge TTS           │  │  ← Replaces ElevenLabs
     │  │ (British Ryan)     │  │
     │  └────────────────────┘  │
     └──────────────────────────┘
```

## What We Keep From OpenClaw Voice-Call Plugin
- ✅ Call Manager (lifecycle, state machine)
- ✅ Media Stream Handler (bidirectional audio)
- ✅ Conversation context management
- ✅ Barge-in / interrupt detection
- ✅ TTS queue & serialization
- ✅ Agent integration (main session, tools, memory)
- ✅ Plugin config system
- ✅ CLI commands (`openclaw voicecall call/end/status`)

## What We Build New (3 adapters)

### 1. WebSocket Telephony Provider
Replaces Twilio/Telnyx/Plivo. Instead of phone network:
- Clients connect via WSS directly to the plugin's webhook server
- Binary audio frames (PCM 16-bit, 16kHz mono) + JSON control messages
- Device pairing with confirmation codes
- Same interface as other providers (`VoiceCallProvider`)

### 2. Edge TTS Adapter
Replaces ElevenLabs/OpenAI TTS:
- Uses `edge-tts` npm package or subprocess
- Voice: en-GB-RyanNeural
- Converts output to PCM for streaming
- Same interface as `TelephonyTtsProvider`

### 3. Local Whisper STT Adapter
Replaces OpenAI Realtime API:
- Uses Whisper (tiny/base) locally
- VAD-based: accumulate speech frames → transcribe on speech end
- Silero VAD (ONNX) for voice activity detection
- Same interface as `RealtimeSTTSession`

## Project Structure
```
SpeakWithYourJarvisApp/
├── server/              # OpenClaw plugin fork
│   ├── src/
│   │   ├── providers/
│   │   │   └── websocket.ts    # NEW: WebSocket telephony provider
│   │   ├── stt-whisper.ts      # NEW: Local Whisper STT
│   │   ├── tts-edge.ts         # NEW: Edge TTS adapter
│   │   └── ...                 # Kept from voice-call plugin
│   ├── sounds/                 # Ring, pickup, greetings
│   ├── package.json
│   └── .env.example
│
├── app/                 # Android app (Kotlin)
│   └── ...
│
├── web/                 # Web client (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── plans/               # This folder
├── .env.example
├── .gitignore
└── README.md
```

## Call Experience (UX Flow)
1. **Open app/web** → "Call Jarvis" button
2. **Tap** → WebSocket connects to plugin
3. **Ring** (0.7s) → **Pickup click** → **Greeting** ("Good afternoon, sir")
4. **Talk naturally** — VAD handles turn detection, no 8-second cuts
5. **Interrupt** — start talking while Jarvis speaks, he stops
6. **Hang up** → tap red button or say "goodbye"

## Cost
| Component | Cost |
|-----------|------|
| Everything | **$0/month** |
| Play Store (optional) | $25 one-time |

## Design Decisions

### Fork voice-call plugin, don't build from scratch
**Why:** The plugin already solved all the hard problems (state machine, barge-in, audio queuing, agent integration). We just swap 3 I/O adapters. 10x less work, battle-tested foundation.

### WebSocket over phone network
**Why:** No Twilio account, no per-minute costs, no phone number needed. Works from any device with a browser or our app.

### TypeScript (same as original plugin)
**Why:** The voice-call plugin is TypeScript. Forking it means we stay in the same language, same build system, same plugin architecture. It loads natively into OpenClaw.

### Keep as OpenClaw plugin
**Why:** Once built, it installs with `openclaw plugins install`. Anyone with OpenClaw can use it. No separate server process.

## Phases
1. **Server**: Fork plugin, build 3 adapters, test end-to-end
2. **Web**: HTML/JS client, prove pipeline works
3. **Android**: Native Kotlin app
4. **Publish**: APK sideload + optional Play Store

---

*Created: 2026-02-12 (v2 — fork approach)*
*Author: Jarvis de la Ari 🦞*
