# Web Client Plan — Browser Voice Interface

## Overview
Single-page web app (pure HTML/CSS/JS, no frameworks) served from the Pipecat server itself. No setup, no config — open the page and call Jarvis.

## UX Flow
1. Open the page (served from the same server)
2. See "Call Jarvis" button
3. Ring → pickup → greeting → conversation
4. Hang up button

No pairing, no setup, no configuration. If you can reach the page, you can talk.

## Technical Approach

### Audio Capture
- `navigator.mediaDevices.getUserMedia({audio: true})` — browser microphone
- `AudioWorklet` for raw PCM extraction
- Resample to 16kHz mono if needed (browsers typically capture at 44.1/48kHz)
- Send raw PCM frames over WebSocket (binary)

### Audio Playback
- `AudioContext` + `AudioBufferSourceNode`
- Queue incoming PCM frames for gapless playback
- Handle ring, pickup, greeting, and TTS audio

### WebSocket
- Native browser `WebSocket` API
- WSS (secure) connection to same origin
- Binary frames for audio, text frames for JSON control

### UI Design
- Dark theme (consistent with our other apps)
- Big centered call button with pulse animation
- Status indicator (connecting, ringing, listening, responding)
- Transcript display below (user + Jarvis, timestamped)
- Call duration timer
- Hang up button

## File Structure
```
web/
├── index.html      # Single page — call UI
├── style.css       # Dark theme styling
├── app.js          # WebSocket, audio capture/playback
└── audio.js        # AudioContext helpers, resampling
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
- Microphone permission prompt each session (some browsers)

## Constraints
- Pure HTML/CSS/JS — no React, no build tools, no npm
- Must work with self-signed SSL cert (user accepts browser warning once)
- Must be served over HTTPS (browser requires it for microphone access)

---

*Served from the Pipecat server on the same port (static files route)*
