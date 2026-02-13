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
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.services.whisper.stt import WhisperSTTService, Model
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.frames.frames import (
        InputAudioRawFrame,
        OutputAudioRawFrame,
        TranscriptionFrame,
        LLMFullResponseStartFrame,
        LLMFullResponseEndFrame,
        TextFrame,
        TTSAudioRawFrame,
        EndFrame,
    )
    from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

    from edge_tts_service import EdgeTTSService
    from openclaw_llm import create_openclaw_llm

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
        call_manager.add_transcript("bot", f"Good {greeting_key}, sir.")

    call_manager.transition(CallState.LISTENING)
    await send_control(ws, {"type": "state", "state": "listening"})

    # ── Services ──
    vad = SileroVADAnalyzer(sample_rate=SAMPLE_RATE, params=SileroVADAnalyzer.VADParams(
        stop_secs=VAD_STOP_SECS,
    ))

    stt = WhisperSTTService(
        model=WHISPER_MODEL,
        device="cpu",
        no_speech_prob=0.4,
    )

    llm = create_openclaw_llm(OPENCLAW_URL, OPENCLAW_TOKEN)

    tts = EdgeTTSService(
        voice="en-GB-RyanNeural",
        sample_rate=SAMPLE_RATE,
    )

    # ── Custom processor: bridges WebSocket audio ↔ Pipecat frames ──
    class WebSocketBridge(FrameProcessor):
        """Bridges between WebSocket binary audio and Pipecat frame pipeline."""

        def __init__(self, ws_conn: web.WebSocketResponse, call_mgr: CallManager):
            super().__init__()
            self._ws = ws_conn
            self._call_mgr = call_mgr

        async def process_frame(self, frame: Frame, direction: FrameDirection):
            """Process outgoing frames → send to WebSocket."""
            await super().process_frame(frame, direction)

            if isinstance(frame, TTSAudioRawFrame):
                # Send TTS audio to client
                await send_audio(self._ws, frame.audio)
            elif isinstance(frame, TranscriptionFrame):
                # User said something
                text = frame.text.strip()
                if text:
                    self._call_mgr.add_transcript("user", text)
                    await send_control(self._ws, {
                        "type": "transcript",
                        "text": text,
                    })
                    self._call_mgr.transition(CallState.SPEAKING)
                    await send_control(self._ws, {"type": "state", "state": "speaking"})
            elif isinstance(frame, TextFrame):
                # Jarvis response text
                text = frame.text.strip()
                if text:
                    self._call_mgr.add_transcript("bot", text)
                    await send_control(self._ws, {
                        "type": "response_text",
                        "text": text,
                    })
            elif isinstance(frame, LLMFullResponseEndFrame):
                # Response complete, back to listening
                self._call_mgr.transition(CallState.LISTENING)
                await send_control(self._ws, {"type": "state", "state": "listening"})
                await send_control(self._ws, {"type": "done"})

            await self.push_frame(frame, direction)

    bridge = WebSocketBridge(ws, call_manager)

    # ── Main loop: read audio from WebSocket, feed to VAD ──
    logger.info(f"Call {call.call_id}: pipeline started")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                # Audio from client
                audio_bytes = msg.data
                # Feed to VAD
                vad_state = vad.analyze_audio(audio_bytes)

                if vad_state == "speaking":
                    # Accumulate audio during speech
                    if not hasattr(run_pipeline, '_speech_buffer'):
                        run_pipeline._speech_buffer = bytearray()
                    run_pipeline._speech_buffer.extend(audio_bytes)
                elif vad_state == "stopped" and hasattr(run_pipeline, '_speech_buffer'):
                    # Speech ended — transcribe
                    speech_audio = bytes(run_pipeline._speech_buffer)
                    run_pipeline._speech_buffer = bytearray()

                    if len(speech_audio) > SAMPLE_RATE:  # At least 0.5s of audio
                        # Run STT
                        async for frame in stt.run_stt(speech_audio):
                            if isinstance(frame, TranscriptionFrame) and frame.text.strip():
                                user_text = frame.text.strip()
                                call_manager.add_transcript("user", user_text)
                                await send_control(ws, {
                                    "type": "transcript",
                                    "text": user_text,
                                })

                                # Get LLM response
                                call_manager.transition(CallState.SPEAKING)
                                await send_control(ws, {"type": "state", "state": "speaking"})

                                response_text = await get_llm_response(llm, user_text, call)
                                if response_text:
                                    call_manager.add_transcript("bot", response_text)
                                    await send_control(ws, {
                                        "type": "response_text",
                                        "text": response_text,
                                    })

                                    # TTS → send audio
                                    async for tts_frame in tts.run_tts(response_text, "ctx"):
                                        if isinstance(tts_frame, TTSAudioRawFrame):
                                            await send_audio(ws, tts_frame.audio)

                                await send_control(ws, {"type": "done"})
                                call_manager.transition(CallState.LISTENING)
                                await send_control(ws, {"type": "state", "state": "listening"})

            elif msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "hangup":
                    logger.info(f"Call {call.call_id}: user hangup")
                    break

            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.ERROR):
                break

    except Exception as e:
        logger.error(f"Call {call.call_id}: pipeline error: {e}")
        call_manager.end_call(CallState.ERROR)
    else:
        call_manager.end_call(CallState.HANGUP_USER)

    logger.info(f"Call {call.call_id}: ended ({call.state.value}), "
                f"duration {call.duration_seconds:.1f}s, "
                f"{len(call.transcript)} transcript entries")


async def get_llm_response(llm, user_text: str, call) -> str:
    """Get a response from OpenClaw via Chat Completions API."""
    import aiohttp

    # Build conversation history from call transcript
    messages = []
    for entry in call.transcript[-20:]:  # Last 10 turns (20 entries)
        role = "assistant" if entry.speaker == "bot" else "user"
        messages.append({"role": role, "content": entry.text})

    # Add current user message if not already in transcript
    if not messages or messages[-1]["content"] != user_text:
        messages.append({"role": "user", "content": user_text})

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENCLAW_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "passthrough",
                    "messages": messages,
                },
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await resp.text()
                    logger.error(f"OpenClaw API error {resp.status}: {error[:200]}")
                    return "I'm sorry, I couldn't process that. Could you try again?"
    except Exception as e:
        logger.error(f"OpenClaw request failed: {e}")
        return "I'm having trouble connecting. Please try again in a moment."


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
    call = call_manager.start_call()
    await send_control(ws, {
        "type": "connected",
        "callId": call.call_id,
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
