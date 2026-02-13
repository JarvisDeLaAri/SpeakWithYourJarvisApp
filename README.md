# 🦞 SpeakWithYourJarvisApp

Real-time voice conversation with your AI assistant. Press "Call Jarvis", hear the phone ring, and talk naturally — like calling a friend.

## Architecture

```
📱 Android App ──┐
                 ├── WebSocket (WSS) ──→ 🖥️ Voice Server ──→ 🤖 OpenClaw (Jarvis)
🌐 Web Client ──┘                           │
                                        Silero VAD → Whisper STT → LLM → Edge TTS
```

## Project Structure

| Folder | Description |
|--------|-------------|
| `server/` | Voice pipeline server (Python + Pipecat) |
| `app/` | Android app (Kotlin) |
| `web/` | Web client (HTML/CSS/JS) |
| `plans/` | Architecture docs & task lists |

## Quick Start

### Server
```bash
cd server
cp ../.env.example .env  # Edit with your values
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Web Client
Open `https://your-server:<your-port>/` in a browser.

### Android App
Open `app/` in Android Studio, build, and install.

## Features
- 🎙️ Real-time voice with ML-based voice activity detection (no more 8-second cuts)
- 🧠 Routes through OpenClaw main session (real Jarvis with full memory)
- 🔇 Silero VAD filters background noise (no more AC-as-sentences)
- 📞 Phone call UX: ring → pickup → greeting → conversation
- 🔒 SSL encrypted, firewall secured
- 🆓 Fully free: Whisper (local STT) + Edge TTS + open source pipeline

## Cost
| Component | Cost |
|-----------|------|
| Everything | $0/month |
| Play Store | $25 one-time |

## Tech Stack
- **Pipeline**: Pipecat (open source)
- **VAD**: Silero V5 (ONNX, ~2MB)
- **STT**: Whisper (local, free)
- **LLM**: OpenClaw → Claude (main session)
- **TTS**: Edge TTS (British Ryan)
- **Transport**: WebSocket over HTTPS
- **App**: Kotlin (native Android)
- **Web**: Vanilla HTML/CSS/JS

## Routing to the Real Main Session

The biggest challenge was getting voice responses from the **actual** main session — the same one connected to WhatsApp/Telegram — not a separate parallel session.

### What Doesn't Work

**`/v1/chat/completions` with `model: "agent:main"`** creates a new session context. Even with `user: "main"`, the gateway resolves this to `agent:main:openai-user:main` — a separate session. Your voice app gets a lobotomized version of your agent with no conversation history.

**`X-OpenClaw-Session-Key: main`** (just "main") — the header value is used as-is by `resolveSessionKey()`, not wrapped in `buildAgentMainSessionKey()`. So it becomes a session key of literally `"main"`, not `"agent:main:main"`.

### What Works

Set the **full session key** in the HTTP header:

```
X-OpenClaw-Session-Key: agent:main:main
```

The format is `agent:<agentId>:<mainKey>`. For the default agent's main session, that's `agent:main:main`.

```python
response = requests.post(
    f"{OPENCLAW_URL}/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Content-Type": "application/json",
        "X-OpenClaw-Session-Key": "agent:main:main",
    },
    json={
        "model": "agent:main",
        "messages": [{"role": "user", "content": "Hello from voice app"}],
    },
)
```

### How We Found It

Traced through OpenClaw source code:
1. `openai-http.ts` → `resolveOpenAiSessionKey()` → `resolveSessionKey()` in `http-utils.ts`
2. `resolveSessionKey()` checks for `x-openclaw-session-key` header first — if present, returns it **verbatim**
3. Without the header, it builds `agent:main:openai-user:<user>` — always a separate session
4. The main WhatsApp/Telegram session key is `agent:main:main`

### Alternative: WebSocket RPC

The gateway also supports `chat.send` via WebSocket RPC with explicit `sessionKey`, but the WebSocket connection requires challenge-response authentication (nonce signing), which is complex to implement. The HTTP header approach is much simpler.

---

Built by Jarvis de la Ari & Ariel @ Bresleveloper AI 🦞

[![YouTube](https://img.shields.io/badge/YouTube-BresleveloperAI-red?logo=youtube)](https://www.youtube.com/@BresleveloperAI/videos)

[ישראלי/דובר עברית? כנס ליוטיוב שלי לתכנים נוספים על בינה מלאכותית (לא לשכוח להרשם ♥, פעמון ♥, לייק ♥, ולשלוח לחבר ♥♥♥)](https://www.youtube.com/@BresleveloperAI/videos)
