# Web Client Plan — Browser Voice Interface

## Overview
Single-page web app (pure HTML/CSS/JS, no frameworks) that connects to the same Pipecat server. Acts as a fallback for when you don't have the Android app, and as a development/testing tool.

## UX Flow
Same as Android app:
1. First visit → setup: enter server address + port, pair with confirmation code
2. Main screen → "Call Jarvis" button
3. Ring → pickup → greeting → conversation
4. Hang up button

## Technical Approach

### Audio Capture
- `navigator.mediaDevices.getUserMedia({audio: true})` — browser microphone
- `AudioContext` + `ScriptProcessorNode` or `AudioWorklet` for raw PCM
- Resample to 16kHz mono if needed (browsers typically capture at 44.1/48kHz)
- Send raw PCM frames over WebSocket (binary)

### Audio Playback
- `AudioContext` + `AudioBufferSourceNode`
- Queue incoming PCM frames for gapless playback
- Handle ring, pickup, greeting, and TTS audio

### WebSocket
- Native browser `WebSocket` API
- WSS (secure) connection
- Same protocol as Android app (binary audio + JSON control)

### Device Pairing
- Server address + port stored in `localStorage`
- JWT token stored in `localStorage` (acceptable for web)
- Setup flow: fetch `/api/pair` → show code prompt → confirm → store token

### UI Design
- Dark theme (consistent with our other apps)
- Big centered call button with pulse animation
- Status indicator (connecting, ringing, listening, responding)
- Transcript display below
- Settings gear icon for server config

## File Structure
```
web/
├── index.html      # Single page — setup + call UI
├── style.css       # Dark theme styling
├── app.js          # WebSocket, audio capture/playback, pairing
├── audio.js        # AudioContext helpers, resampling
└── sounds/         # Ring + pickup as base64 or small files
    ├── ring.mp3
    └── pickup.mp3
```

## Browser Compatibility
- Chrome 66+ (AudioWorklet)
- Firefox 76+ (AudioWorklet)
- Safari 14.1+ (AudioWorklet)
- Edge 79+ (Chromium-based)

## Key Differences from Android
- No background audio (tab must be active/visible)
- No push notifications
- Audio may have slightly higher latency (AudioWorklet vs native AudioTrack)
- LocalStorage instead of Android Keystore for tokens (less secure)
- Microphone permission prompt each session (some browsers)

## Constraints
- Pure HTML/CSS/JS — no React, no build tools, no npm
- Must work with self-signed SSL cert (user accepts browser warning)
- Single HTML file preferred (inline CSS/JS) for easy deployment
- Must be served over HTTPS (browser requires it for microphone access)

---

*Will be served from the same Pipecat server on the same port (static files route)*
