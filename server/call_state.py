"""Call state machine and records.

Learned from OpenClaw's voice-call plugin:
- Strict forward-only transitions
- Speaking ⇄ Listening cycling for multi-turn
- Terminal states are final
- Max duration timer for safety
"""

import asyncio
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable


class CallState(Enum):
    """Call lifecycle states."""
    # Forward states
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    ACTIVE = "active"
    SPEAKING = "speaking"
    LISTENING = "listening"
    # Terminal states
    COMPLETED = "completed"
    HANGUP_USER = "hangup-user"
    HANGUP_BOT = "hangup-bot"
    TIMEOUT = "timeout"
    ERROR = "error"


TERMINAL_STATES = {
    CallState.COMPLETED,
    CallState.HANGUP_USER,
    CallState.HANGUP_BOT,
    CallState.TIMEOUT,
    CallState.ERROR,
}

CONVERSATION_STATES = {CallState.SPEAKING, CallState.LISTENING}

STATE_ORDER = [
    CallState.INITIATED,
    CallState.RINGING,
    CallState.ANSWERED,
    CallState.ACTIVE,
    CallState.SPEAKING,
    CallState.LISTENING,
]


@dataclass
class TranscriptEntry:
    """A single transcript entry."""
    timestamp: float
    speaker: str  # "user" or "bot"
    text: str


@dataclass
class CallRecord:
    """Record of a single call."""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: CallState = CallState.INITIATED
    started_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None
    ended_at: Optional[float] = None
    end_reason: Optional[str] = None
    transcript: list[TranscriptEntry] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or time.time()
        start = self.answered_at or self.started_at
        return end - start

    def add_transcript(self, speaker: str, text: str):
        self.transcript.append(TranscriptEntry(
            timestamp=time.time(),
            speaker=speaker,
            text=text,
        ))


def transition_state(call: CallRecord, new_state: CallState) -> bool:
    """Attempt to transition to a new state. Returns True if successful."""
    # No-op for same state or already terminal
    if call.state == new_state or call.is_terminal:
        return False

    # Terminal states can always be reached
    if new_state in TERMINAL_STATES:
        call.state = new_state
        if new_state != CallState.INITIATED:
            call.ended_at = time.time()
            call.end_reason = new_state.value
        return True

    # Allow cycling between speaking and listening
    if call.state in CONVERSATION_STATES and new_state in CONVERSATION_STATES:
        call.state = new_state
        return True

    # Only allow forward transitions
    try:
        current_idx = STATE_ORDER.index(call.state)
        new_idx = STATE_ORDER.index(new_state)
    except ValueError:
        return False

    if new_idx > current_idx:
        call.state = new_state
        if new_state == CallState.ANSWERED:
            call.answered_at = time.time()
        return True

    return False


class CallManager:
    """Manages active calls with max duration safety timer."""

    def __init__(self, max_duration_min: int = 30):
        self._max_duration_min = max_duration_min
        self._active_call: Optional[CallRecord] = None
        self._duration_timer: Optional[asyncio.Task] = None
        self._on_timeout: Optional[Callable[[str], Awaitable[None]]] = None

    @property
    def active_call(self) -> Optional[CallRecord]:
        return self._active_call

    def start_call(self, on_timeout: Optional[Callable[[str], Awaitable[None]]] = None) -> CallRecord:
        """Start a new call. Ends any existing call first."""
        if self._active_call and not self._active_call.is_terminal:
            self.end_call(CallState.HANGUP_BOT)

        call = CallRecord()
        self._active_call = call
        self._on_timeout = on_timeout
        return call

    def transition(self, new_state: CallState) -> bool:
        """Transition the active call to a new state."""
        if not self._active_call:
            return False

        result = transition_state(self._active_call, new_state)

        # Start duration timer when call is answered
        if result and new_state == CallState.ANSWERED:
            self._start_duration_timer()

        # Clean up on terminal
        if result and self._active_call.is_terminal:
            self._cancel_duration_timer()

        return result

    def end_call(self, reason: CallState = CallState.COMPLETED) -> Optional[CallRecord]:
        """End the active call."""
        if not self._active_call:
            return None

        self.transition(reason)
        self._cancel_duration_timer()
        call = self._active_call
        self._active_call = None
        return call

    def add_transcript(self, speaker: str, text: str):
        """Add a transcript entry to the active call."""
        if self._active_call and not self._active_call.is_terminal:
            self._active_call.add_transcript(speaker, text)

    def _start_duration_timer(self):
        """Start the max duration safety timer."""
        self._cancel_duration_timer()
        self._duration_timer = asyncio.create_task(self._duration_watchdog())

    def _cancel_duration_timer(self):
        """Cancel the duration timer if running."""
        if self._duration_timer and not self._duration_timer.done():
            self._duration_timer.cancel()
            self._duration_timer = None

    async def _duration_watchdog(self):
        """Auto-hangup after max duration."""
        try:
            await asyncio.sleep(self._max_duration_min * 60)
            if self._active_call and not self._active_call.is_terminal:
                self.transition(CallState.TIMEOUT)
                if self._on_timeout and self._active_call:
                    await self._on_timeout(self._active_call.call_id)
        except asyncio.CancelledError:
            pass
