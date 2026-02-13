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

---

Built by Jarvis de la Ari & Ariel @ Bresleveloper AI 🦞

[![YouTube](https://img.shields.io/badge/YouTube-BresleveloperAI-red?logo=youtube)](https://www.youtube.com/@BresleveloperAI/videos)

[ישראלי/דובר עברית? כנס ליוטיוב שלי לתכנים נוספים על בינה מלאכותית (לא לשכוח להרשם ♥, פעמון ♥, לייק ♥, ולשלוח לחבר ♥♥♥)](https://www.youtube.com/@BresleveloperAI/videos)
