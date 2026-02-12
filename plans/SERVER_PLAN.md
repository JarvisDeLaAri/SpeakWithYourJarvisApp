# Server Plan v2 — OpenClaw Plugin Fork

## Overview
Fork OpenClaw's `@openclaw/voice-call` extension. Keep the architecture (call manager, state machine, media streaming, agent integration). Replace 3 paid components with free alternatives.

## Source Location
Original: `openclaw-source/extensions/voice-call/`

## What We Keep (unchanged)
```
src/
├── manager/           # Call lifecycle, state machine
│   ├── context.ts     # Call context
│   ├── store.ts       # Active calls storage
│   ├── timers.ts      # Timeout management
│   ├── lookup.ts      # Call lookup
│   ├── state.ts       # State transitions
│   ├── events.ts      # Event handling
│   └── outbound.ts    # Outbound call logic
├── types.ts           # Type definitions
├── voice-mapping.ts   # Voice configuration
├── config.ts          # Plugin config schema (extend)
└── runtime.ts         # Plugin runtime (modify to add our providers)
```

## What We Build (3 new files)

### 1. `src/providers/websocket.ts` — WebSocket Telephony Provider

Implements `VoiceCallProvider` interface. Instead of dialing a phone number:

```typescript
interface VoiceCallProvider {
  makeCall(params: { to: string; from: string; webhookUrl: string }): Promise<CallResult>;
  endCall(callId: string): Promise<void>;
  // ...
}
```

Our WebSocket provider:
- Runs a WSS server (on plugin's configured port)
- Clients connect directly — no phone network
- "makeCall" = send push notification to paired device → device connects back
- "endCall" = close WebSocket
- Audio: binary PCM frames bidirectional
- Device auth: JWT token from pairing flow

**Pairing flow:**
- Client POST `/api/pair` with device name → server generates 6-digit code
- Code shown in Jarvis's WhatsApp chat
- Client POST `/api/confirm` with code → gets JWT
- JWT stored on device, sent in WebSocket handshake

### 2. `src/tts-edge.ts` — Edge TTS Adapter

Implements `TelephonyTtsProvider` interface:

```typescript
interface TelephonyTtsProvider {
  synthesizeForTelephony(text: string): Promise<Buffer>;
}
```

Our implementation:
- Uses `edge-tts` npm package (or spawn `edge-tts` Python CLI)
- Voice: en-GB-RyanNeural (configurable)
- Returns PCM buffer (16-bit, 16kHz or 8kHz mulaw for telephony compat)
- Sentence chunking for streaming (split on `.!?` → synthesize each → stream)

### 3. `src/stt-whisper.ts` — Local Whisper STT

Implements `RealtimeSTTSession` interface:

```typescript
interface RealtimeSTTSession {
  sendAudio(buffer: Buffer): void;
  onTranscript(callback: (text: string) => void): void;
  onPartialTranscript(callback: (text: string) => void): void;
  onSpeechStart(callback: () => void): void;
  close(): void;
}
```

Our implementation:
- Silero VAD (ONNX via `onnxruntime-node` or direct ONNX runtime)
- Accumulate audio frames while VAD detects speech
- On speech end → save to temp WAV → run Whisper CLI → return transcript
- OR: use `whisper.cpp` WASM/native for faster inference
- Fire `onSpeechStart` when VAD first detects voice

## Config Extension

Add to plugin config schema:
```json
{
  "provider": "websocket",
  "websocket": {
    "port": "<your-port>",
    "sslCert": "/path/to/cert",
    "sslKey": "/path/to/key",
    "jwtSecret": "<secret>"
  },
  "stt": {
    "provider": "whisper",
    "whisper": {
      "model": "tiny",
      "language": "en"
    }
  },
  "tts": {
    "provider": "edge",
    "edge": {
      "voice": "en-GB-RyanNeural"
    }
  }
}
```

## Call Sounds
Pre-generate with Edge TTS and store in `sounds/`:
- `ring.wav` — 0.7s phone ring tone (synthesize or use free sound)
- `pickup.wav` — pickup click
- `greeting_morning.wav` — "Good morning, sir"
- `greeting_afternoon.wav` — "Good afternoon, sir"
- `greeting_evening.wav` — "Good evening, sir"
- `greeting_night.wav` — "Good night, sir"

## Dependencies (new, added to package.json)
```
edge-tts              # Free TTS (npm or Python subprocess)
onnxruntime-node      # Silero VAD
jsonwebtoken          # Device pairing auth
```

Whisper: use existing system `whisper` CLI or bundle `whisper.cpp` for speed.

## Integration Points
- Registers as provider "websocket" in `resolveProvider()` in runtime.ts
- TTS adapter registered alongside existing OpenAI/ElevenLabs
- STT adapter registered alongside existing OpenAI Realtime
- All existing CLI commands work: `openclaw voicecall call/end/status`
- Installs via `openclaw plugins install`

---

*Language: TypeScript (same as original plugin)*
*Installs into: OpenClaw gateway process*
