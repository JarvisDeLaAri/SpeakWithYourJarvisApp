"""Edge TTS service for Pipecat.

Free text-to-speech using Microsoft Edge's TTS API.
No API key required. Voice: en-GB-RyanNeural (British Ryan).
"""

import asyncio
import io
from typing import AsyncGenerator, Optional

from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService

try:
    import edge_tts
except ModuleNotFoundError:
    logger.error("edge-tts not installed. Run: pip install edge-tts")
    raise


class EdgeTTSService(TTSService):
    """Text-to-speech using Microsoft Edge TTS (free, no API key)."""

    def __init__(
        self,
        *,
        voice: str = "en-GB-RyanNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        sample_rate: int = 16000,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._voice = voice
        self._rate = rate
        self._volume = volume
        # Force sample rate (normally set by StartFrame in pipeline)
        self._sample_rate = sample_rate

    def can_generate_metrics(self) -> bool:
        return True

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize text to speech using Edge TTS."""
        logger.debug(f"Edge TTS generating: [{text[:50]}...]")

        await self.start_processing_metrics()

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self._voice,
                rate=self._rate,
                volume=self._volume,
            )

            # Collect audio data
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            if not audio_data:
                logger.warning("Edge TTS returned no audio")
                yield ErrorFrame("Edge TTS returned no audio")
                return

            # Edge TTS returns MP3 — convert to PCM
            pcm_data = await self._mp3_to_pcm(bytes(audio_data))

            if pcm_data:
                yield TTSStartedFrame()
                # Send in chunks for streaming feel
                chunk_size = max(1, self.sample_rate * 2)  # 1 second chunks (16-bit = 2 bytes/sample)
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i:i + chunk_size]
                    if chunk:
                        yield TTSAudioRawFrame(
                            audio=chunk,
                            sample_rate=self.sample_rate,
                            num_channels=1,
                        )
                yield TTSStoppedFrame()

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            import traceback
            traceback.print_exc()
            yield ErrorFrame(f"Edge TTS error: {e}")
        finally:
            await self.stop_processing_metrics()

    async def _mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """Convert MP3 audio to 16-bit PCM at target sample rate."""
        try:
            import subprocess

            # Use ffmpeg to convert MP3 → raw PCM
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i", "pipe:0",
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ar", str(self.sample_rate),
                "-ac", "1",
                "pipe:1",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            pcm_data, stderr = await proc.communicate(input=mp3_data)

            if proc.returncode != 0:
                logger.error(f"ffmpeg error: {stderr.decode()[:200]}")
                return None

            return pcm_data

        except FileNotFoundError:
            logger.error("ffmpeg not found. Install with: apt install ffmpeg")
            return None
        except Exception as e:
            logger.error(f"MP3 to PCM conversion error: {e}")
            return None
