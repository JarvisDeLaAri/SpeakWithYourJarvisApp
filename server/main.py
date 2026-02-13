"""SpeakWithYourJarvis — Voice Server Entry Point.

Pipecat pipeline: WebSocket → Silero VAD → Whisper STT → OpenClaw LLM → Edge TTS → WebSocket
"""

import asyncio
import os
import ssl
import json
import time
import wave
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from loguru import logger

import numpy as np
from call_state import CallManager, CallState

load_dotenv()

# ── Config ──────────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10011"))
SSL_CERT = os.getenv("SSL_CERT", "")
SSL_KEY = os.getenv("SSL_KEY", "")
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "")
OPENCLAW_TOKEN = os.getenv("OPENCLAW_TOKEN", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
VAD_STOP_SECS = float(os.getenv("VAD_STOP_SECS", "0.6"))
MAX_CALL_DURATION_MIN = int(os.getenv("MAX_CALL_DURATION_MIN", "30"))
WEB_DIR = Path(__file__).parent.parent / "web"
SOUNDS_DIR = Path(__file__).parent / "sounds"
SAMPLE_RATE = 16000

# ── Call Manager ────────────────────────────────────────────────
call_manager = CallManager(max_duration_min=MAX_CALL_DURATION_MIN)

# ── Pre-load Models (once at startup, not per-call) ────────────
logger.info("Pre-loading Pipecat models...")
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams, VADState
from pipecat.services.whisper.stt import WhisperSTTService, Model
from pipecat.frames.frames import TranscriptionFrame, TTSAudioRawFrame
from edge_tts_service import EdgeTTSService

_shared_stt = WhisperSTTService(model=WHISPER_MODEL, device="cpu", compute_type="int8", no_speech_prob=0.4)

# Direct faster-whisper model for fast transcription (beam_size=1)
from faster_whisper import WhisperModel as _FWModel
_fast_whisper = _FWModel(WHISPER_MODEL, device="cpu", compute_type="int8")
logger.info("Fast Whisper (beam=1) loaded ✓")
_shared_tts = EdgeTTSService(voice="en-GB-RyanNeural", sample_rate=SAMPLE_RATE)
logger.info("Models pre-loaded ✓")


def get_greeting_key(timezone: str = "UTC") -> str:
    """Determine time-appropriate greeting based on timezone."""
    from datetime import datetime
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(timezone)
        hour = datetime.now(tz).hour
    except Exception:
        hour = datetime.utcnow().hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def load_sound(name: str) -> bytes:
    """Load a WAV file and return raw PCM bytes."""
    path = SOUNDS_DIR / name
    if not path.exists():
        logger.warning(f"Sound file not found: {path}")
        return b""

    with wave.open(str(path), "rb") as wf:
        return wf.readframes(wf.getnframes())


# ── Pre-load sounds ────────────────────────────────────────────
RING_AUDIO = load_sound("ring.wav")
PICKUP_AUDIO = load_sound("pickup.wav")
GREETINGS = {
    key: load_sound(f"greetings/{key}.wav")
    for key in ["morning", "afternoon", "evening", "night"]
}


# ── Pipecat Pipeline ───────────────────────────────────────────
async def run_pipeline(ws: web.WebSocketResponse, timezone: str = "UTC"):
    """Run the voice pipeline for a single call."""

    # ── Start call ──
    call = call_manager.start_call()
    call_manager.transition(CallState.RINGING)

    # Send ring sound
    await send_audio(ws, RING_AUDIO)
    await asyncio.sleep(0.1)

    # Send pickup + greeting
    call_manager.transition(CallState.ANSWERED)
    await send_audio(ws, PICKUP_AUDIO)
    await asyncio.sleep(0.05)

    greeting_key = get_greeting_key(timezone)
    greeting_audio = GREETINGS.get(greeting_key, b"")
    if greeting_audio:
        call_manager.transition(CallState.ACTIVE)
        call_manager.transition(CallState.SPEAKING)
        await send_control(ws, {"type": "state", "state": "speaking"})
        await send_audio(ws, greeting_audio)
        call_manager.add_transcript("bot", f"Good {greeting_key} sir.")

    call_manager.transition(CallState.LISTENING)
    await send_control(ws, {"type": "state", "state": "listening"})

    # ── Services (shared, pre-loaded at startup) ──
    # VAD is lightweight and stateful per-call, so create fresh
    current_vad_stop = VAD_STOP_SECS
    vad = SileroVADAnalyzer(sample_rate=SAMPLE_RATE, params=VADParams(
        stop_secs=current_vad_stop,
        start_secs=0.3,
        confidence=0.6,
        min_volume=0.4,
    ))
    vad.set_sample_rate(SAMPLE_RATE)
    logger.info(f"Call {call.call_id}: VAD params: stop={vad.params.stop_secs}s start={vad.params.start_secs}s conf={vad.params.confidence}")

    # STT and TTS are shared (models loaded once)
    stt = _shared_stt
    tts = _shared_tts

    # ── Main loop: read audio from WebSocket, feed to VAD ──
    logger.info(f"Call {call.call_id}: pipeline started")
    speech_buffer = bytearray()
    is_speaking = False

    # Silence gap tracking: record gaps between speech segments within one utterance
    silence_start_time = None  # when current silence gap began
    silence_gaps = []  # list of gap durations (seconds) within this utterance
    prev_vad_state = VADState.QUIET

    # Bytes per second for time calculations
    BYTES_PER_SEC = SAMPLE_RATE * 2  # 16kHz * 16-bit = 32000 bytes/sec

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                # Audio from client
                audio_bytes = msg.data
                # Feed to VAD
                vad_state = await vad.analyze_audio(audio_bytes)

                # Track silence gaps within speech
                if prev_vad_state in (VADState.SPEAKING, VADState.STARTING) and vad_state == VADState.STOPPING:
                    # Just went from speaking to silence — start timing the gap
                    silence_start_time = time.time()
                elif vad_state in (VADState.SPEAKING, VADState.STARTING) and silence_start_time is not None:
                    # Resumed speaking after a gap — record the gap
                    gap = time.time() - silence_start_time
                    silence_gaps.append(gap)
                    silence_start_time = None
                prev_vad_state = vad_state

                if vad_state == VADState.STARTING:
                    # Speech just started
                    if not is_speaking:
                        is_speaking = True
                        speech_buffer = bytearray()
                        silence_gaps = []
                        silence_start_time = None
                        logger.debug(f"Call {call.call_id}: VAD speech start")
                    speech_buffer.extend(audio_bytes)

                elif vad_state == VADState.SPEAKING:
                    # Speech continuing
                    is_speaking = True
                    speech_buffer.extend(audio_bytes)

                elif vad_state == VADState.STOPPING:
                    # Still counting silence — keep buffering but don't transcribe yet
                    speech_buffer.extend(audio_bytes)

                elif vad_state == VADState.QUIET and is_speaking:
                    # Full stop_secs of silence elapsed — NOW transcribe
                    speech_buffer.extend(audio_bytes)
                    is_speaking = False
                    speech_audio = bytes(speech_buffer)
                    speech_buffer = bytearray()

                    # Record the final silence (the one that ended the utterance)
                    final_silence = 0.0
                    if silence_start_time is not None:
                        final_silence = time.time() - silence_start_time

                    # Calculate silence stats
                    mid_gaps = list(silence_gaps)  # pauses where speech resumed
                    max_mid_gap = max(mid_gaps) if mid_gaps else 0.0
                    total_duration = len(speech_audio) / BYTES_PER_SEC
                    silence_report = {
                        "maxGap": round(max_mid_gap, 1),
                        "gapCount": len(mid_gaps),
                        "audioDuration": round(total_duration, 1),
                        "finalSilence": round(final_silence, 1),
                    }
                    silence_gaps = []
                    silence_start_time = None

                    # At least 0.5s of audio (16000 samples/sec * 2 bytes = 32000 bytes/sec)
                    if len(speech_audio) > SAMPLE_RATE:
                        logger.info(f"Call {call.call_id}: transcribing {len(speech_audio)} bytes "
                                    f"(maxGap={silence_report['maxGap']}s, gaps={silence_report['gapCount']})")

                        # Show transcribing status
                        await send_control(ws, {"type": "state", "state": "transcribing"})

                        # Run STT (direct faster-whisper with beam=1 for speed)
                        audio_float = np.frombuffer(speech_audio, dtype=np.int16).astype(np.float32) / 32768.0
                        segments, _ = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: _fast_whisper.transcribe(audio_float, beam_size=1, language="en")
                        )
                        user_text = " ".join(s.text.strip() for s in segments if s.no_speech_prob < 0.4).strip()
                        if user_text:
                            logger.info(f"Call {call.call_id}: user said: {user_text}")
                            call_manager.add_transcript("user", user_text)
                            await send_control(ws, {
                                "type": "transcript",
                                "text": user_text,
                                "silence": silence_report,
                            })

                            # Show thinking status while waiting for LLM
                            await send_control(ws, {"type": "state", "state": "thinking"})
                            call_manager.transition(CallState.SPEAKING)

                            response_text = await get_llm_response(None, user_text, call)
                            if response_text:
                                logger.info(f"Call {call.call_id}: jarvis says: {response_text[:80]}")
                                call_manager.add_transcript("bot", response_text)

                                # If response is long, send full to WhatsApp and voice just a summary
                                MAX_VOICE_CHARS = 200
                                if len(response_text) > MAX_VOICE_CHARS:
                                    # Send full response to WhatsApp
                                    await send_to_whatsapp(response_text)
                                    # Get first sentence for voice
                                    first_sentence = response_text.split('.')[0].strip() + '.'
                                    voice_text = first_sentence + " Sent the details to WhatsApp."
                                    logger.info(f"Call {call.call_id}: long response ({len(response_text)} chars), sent to WA")
                                else:
                                    voice_text = response_text

                                await send_control(ws, {
                                    "type": "response_text",
                                    "text": voice_text,
                                })

                                # TTS → send audio
                                async for tts_frame in tts.run_tts(voice_text, "ctx"):
                                    if isinstance(tts_frame, TTSAudioRawFrame):
                                        await send_audio(ws, tts_frame.audio)

                            await send_control(ws, {"type": "done"})
                            call_manager.transition(CallState.LISTENING)
                            await send_control(ws, {"type": "state", "state": "listening"})
                    else:
                        logger.debug(f"Call {call.call_id}: speech too short ({len(speech_audio)} bytes), skipping")

                # VADState.QUIET — no speech, do nothing

            elif msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                logger.debug(f"Call {call.call_id}: text msg: {data.get('type')}")
                if data.get("type") == "hangup":
                    logger.info(f"Call {call.call_id}: user hangup")
                    break
                elif data.get("type") == "vad_stop":
                    # Client adjusting VAD silence threshold
                    new_stop = float(data.get("value", current_vad_stop))
                    new_stop = max(0.5, min(15.0, new_stop))  # clamp 0.5-15s
                    current_vad_stop = new_stop
                    vad = SileroVADAnalyzer(sample_rate=SAMPLE_RATE, params=VADParams(
                        stop_secs=current_vad_stop,
                        start_secs=0.3,
                        confidence=0.6,
                        min_volume=0.4,
                    ))
                    vad.set_sample_rate(SAMPLE_RATE)
                    logger.info(f"Call {call.call_id}: VAD stop updated to {current_vad_stop}s")
                    await send_control(ws, {"type": "vad_updated", "value": current_vad_stop})

            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                break

    except Exception as e:
        logger.error(f"Call {call.call_id}: pipeline error: {e}")
        import traceback
        traceback.print_exc()
        call_manager.end_call(CallState.ERROR)
    else:
        call_manager.end_call(CallState.HANGUP_USER)

    logger.info(f"Call {call.call_id}: ended ({call.state.value}), "
                f"duration {call.duration_seconds:.1f}s, "
                f"{len(call.transcript)} transcript entries")


async def get_llm_response(llm, user_text: str, call) -> str:
    """Get a response from OpenClaw main session via Chat Completions API.

    Uses X-OpenClaw-Session-Key header with the full session key "agent:main:main"
    to inject into the actual main session (same as WhatsApp conversation).
    """
    import aiohttp

    prompt = (
        f"[🎤 Voice Call] The user is speaking through the voice call app. "
        f"Your response will be converted to speech via TTS.\n\n"
        f"RULES:\n"
        f"- Keep voice responses SHORT (1-3 sentences max)\n"
        f"- Do NOT use the tts tool. Do NOT include MEDIA: tags\n"
        f"- If the answer requires detail (code, lists, steps, long explanations): "
        f"send a BRIEF voice summary, then use the message tool to send the full details "
        f"to WhatsApp, and end your voice response with 'sent the details to WhatsApp'\n"
        f"- If the answer is simple, just reply with plain text\n\n"
        f'They said: "{user_text}"'
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENCLAW_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                    "Content-Type": "application/json",
                    "X-OpenClaw-Session-Key": "agent:main:main",
                },
                json={
                    "model": "agent:main",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                },
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"]
                    logger.debug(f"OpenClaw response: {text[:100]}")
                    return text
                else:
                    error = await resp.text()
                    logger.error(f"OpenClaw API error {resp.status}: {error[:300]}")
                    return "I'm sorry, I couldn't process that. Could you try again?"
    except Exception as e:
        logger.error(f"OpenClaw request failed: {e}")
        return "I'm having trouble connecting. Please try again in a moment."


# ── WhatsApp Helper ────────────────────────────────────────────
async def send_to_whatsapp(text: str):
    """Send a message to WhatsApp via OpenClaw Chat Completions.
    Uses a simple instruction to forward the text.
    """
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENCLAW_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                    "Content-Type": "application/json",
                    "X-OpenClaw-Session-Key": "agent:main:main",
                },
                json={
                    "model": "agent:main",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"[🎤 Voice Call — WhatsApp Forward] "
                                f"Send the following text to WhatsApp using the message tool, "
                                f"then reply with ONLY: NO_REPLY\n\n"
                                f"Text to send:\n{text}"
                            ),
                        }
                    ],
                },
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"WhatsApp forward failed: {resp.status}: {error[:200]}")
    except Exception as e:
        logger.error(f"WhatsApp forward error: {e}")


# ── WebSocket Helpers ──────────────────────────────────────────
async def send_audio(ws: web.WebSocketResponse, audio: bytes):
    """Send audio bytes to WebSocket client."""
    if audio and not ws.closed:
        await ws.send_bytes(audio)


async def send_control(ws: web.WebSocketResponse, data: dict):
    """Send JSON control message to WebSocket client."""
    if not ws.closed:
        await ws.send_str(json.dumps(data))


# ── HTTP Routes ────────────────────────────────────────────────
async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket voice connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    logger.info(f"Client connected: {request.remote}")

    # Wait for connect message
    timezone = "UTC"
    try:
        msg = await asyncio.wait_for(ws.receive(), timeout=10)
        if msg.type == web.WSMsgType.TEXT:
            data = json.loads(msg.data)
            if data.get("type") == "connect":
                timezone = data.get("timezone", "UTC")
    except asyncio.TimeoutError:
        pass

    # Send connected acknowledgment
    await send_control(ws, {
        "type": "connected",
        "callId": "pending",
        "greeting": get_greeting_key(timezone),
    })

    # Run the voice pipeline
    await run_pipeline(ws, timezone)

    logger.info(f"Client disconnected: {request.remote}")
    return ws


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "ok", "service": "jarvis-voice-v2"})


async def handle_index(request: web.Request) -> web.FileResponse:
    """Serve web client."""
    index = WEB_DIR / "index.html"
    if index.exists():
        return web.FileResponse(index)
    return web.Response(text="Web client not built yet", status=404)


# ── App Setup ──────────────────────────────────────────────────
def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()
    app.router.add_get("/ws", handle_ws)
    app.router.add_get("/api/health", handle_health)

    # Serve web client static files
    if WEB_DIR.exists():
        app.router.add_get("/", handle_index)
        app.router.add_static("/", WEB_DIR, show_index=False)

    return app


def main():
    """Start the voice server."""
    # Validate config
    if not OPENCLAW_URL:
        logger.error("OPENCLAW_URL not set in .env")
        return
    if not OPENCLAW_TOKEN:
        logger.error("OPENCLAW_TOKEN not set in .env")
        return

    app = create_app()

    # SSL context
    ssl_ctx = None
    if SSL_CERT and SSL_KEY:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_ctx.load_cert_chain(SSL_CERT, SSL_KEY)
        logger.info(f"SSL enabled: {SSL_CERT}")

    protocol = "https" if ssl_ctx else "http"
    logger.info(f"Starting Jarvis Voice Server on {protocol}://{HOST}:{PORT}")
    logger.info(f"OpenClaw: {OPENCLAW_URL}")
    logger.info(f"Whisper model: {WHISPER_MODEL}")
    logger.info(f"VAD stop: {VAD_STOP_SECS}s")
    logger.info(f"Max call duration: {MAX_CALL_DURATION_MIN} min")

    web.run_app(app, host=HOST, port=PORT, ssl_context=ssl_ctx)


if __name__ == "__main__":
    main()
