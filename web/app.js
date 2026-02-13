/**
 * SpeakWithYourJarvis — Web Client
 * WebSocket voice client with PCM audio capture and playback.
 */

// ── State ──────────────────────────────────────────────────────
let ws = null;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let isInCall = false;
let timerInterval = null;
let callStartTime = null;

// Audio playback queue
let audioQueue = [];
let isPlaying = false;

// ── DOM ────────────────────────────────────────────────────────
const callBtn = document.getElementById('callBtn');
const statusEl = document.getElementById('status');
const timerEl = document.getElementById('timer');
const transcriptEl = document.getElementById('transcript');
const vadSlider = document.getElementById('vadSlider');
const vadValue = document.getElementById('vadValue');

// ── VAD Slider ─────────────────────────────────────────────────
vadSlider.addEventListener('input', () => {
    vadValue.textContent = vadSlider.value;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'vad_stop', value: parseFloat(vadSlider.value) }));
    }
});

// ── Call Toggle ────────────────────────────────────────────────
function toggleCall() {
    if (isInCall) {
        hangup();
    } else {
        startCall();
    }
}

// ── Start Call ─────────────────────────────────────────────────
async function startCall() {
    try {
        setStatus('connecting');

        // Get microphone
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            }
        });

        // Create audio context for capture
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // ScriptProcessor to get raw PCM (AudioWorklet is better but more complex)
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        scriptProcessor.onaudioprocess = (e) => {
            if (!isInCall || !ws || ws.readyState !== WebSocket.OPEN) return;

            const float32 = e.inputBuffer.getChannelData(0);
            // Convert float32 [-1,1] to int16
            const int16 = new Int16Array(float32.length);
            for (let i = 0; i < float32.length; i++) {
                const s = Math.max(-1, Math.min(1, float32[i]));
                int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            ws.send(int16.buffer);
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        // Connect WebSocket
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws`;
        ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            isInCall = true;
            setStatus('ringing');
            updateCallButton(true);
            startTimer();
            clearTranscript();

            // Send connect message with timezone
            ws.send(JSON.stringify({
                type: 'connect',
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }));
        };

        ws.onmessage = (event) => {
            if (typeof event.data === 'string') {
                handleControl(JSON.parse(event.data));
            } else {
                // Binary audio data — queue for playback
                queueAudio(event.data);
            }
        };

        ws.onclose = () => {
            if (isInCall) {
                endCall();
            }
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            setStatus('error');
            endCall();
        };

    } catch (err) {
        console.error('Failed to start call:', err);
        setStatus('error: ' + err.message);
        endCall();
    }
}

// ── Hangup ─────────────────────────────────────────────────────
function hangup() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'hangup' }));
    }
    endCall();
}

function endCall() {
    isInCall = false;

    if (ws) {
        ws.close();
        ws = null;
    }

    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }

    audioQueue = [];
    isPlaying = false;

    stopTimer();
    updateCallButton(false);
    setStatus('ready');
}

// ── Control Messages ───────────────────────────────────────────
function handleControl(data) {
    switch (data.type) {
        case 'connected':
            setStatus('ringing');
            break;

        case 'state':
            setStatus(data.state);
            updateButtonAnimation(data.state);
            break;

        case 'transcript':
            addTranscript('user', data.text, data.silence);
            break;

        case 'response_text':
            addTranscript('bot', data.text);
            break;

        case 'done':
            // Response complete
            break;

        case 'error':
            console.error('Server error:', data.message);
            addTranscript('bot', `⚠️ ${data.message}`);
            break;
    }
}

// ── Audio Playback ─────────────────────────────────────────────
function queueAudio(arrayBuffer) {
    audioQueue.push(arrayBuffer);
    if (!isPlaying) {
        playNext();
    }
}

async function playNext() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }

    isPlaying = true;
    const buffer = audioQueue.shift();

    try {
        // Create playback context if needed (may have been closed)
        const playCtx = new AudioContext({ sampleRate: 16000 });

        // Convert int16 PCM to float32
        const int16 = new Int16Array(buffer);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768.0;
        }

        const audioBuffer = playCtx.createBuffer(1, float32.length, 16000);
        audioBuffer.getChannelData(0).set(float32);

        const source = playCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playCtx.destination);

        source.onended = () => {
            playCtx.close();
            playNext();
        };

        source.start();
    } catch (err) {
        console.error('Audio playback error:', err);
        isPlaying = false;
    }
}

// ── UI Updates ─────────────────────────────────────────────────
function setStatus(state) {
    statusEl.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    statusEl.className = 'status ' + state;
}

function updateCallButton(inCall) {
    if (inCall) {
        callBtn.className = 'call-btn hangup';
        callBtn.querySelector('.icon').textContent = '📵';
        callBtn.querySelector('.label').textContent = 'Hang Up';
    } else {
        callBtn.className = 'call-btn call';
        callBtn.querySelector('.icon').textContent = '📞';
        callBtn.querySelector('.label').textContent = 'Call Jarvis';
    }
}

function updateButtonAnimation(state) {
    callBtn.classList.remove('listening', 'speaking');
    if (state === 'listening') {
        callBtn.classList.add('listening');
    } else if (state === 'speaking') {
        callBtn.classList.add('speaking');
    }
}

function addTranscript(speaker, text, silence) {
    // Remove placeholder
    const placeholder = transcriptEl.querySelector('.transcript-placeholder');
    if (placeholder) placeholder.remove();

    const entry = document.createElement('div');
    entry.className = `transcript-entry ${speaker}`;

    const label = document.createElement('div');
    label.className = 'speaker';
    label.textContent = speaker === 'user' ? 'You' : 'Jarvis';

    const content = document.createElement('div');
    content.textContent = text;

    entry.appendChild(label);
    entry.appendChild(content);

    // Show silence report for user messages
    if (silence && speaker === 'user') {
        const report = document.createElement('div');
        report.className = 'silence-report';
        const parts = [`⏱ ${silence.audioDuration}s`];
        if (silence.maxGap > 0) {
            parts.push(`longest pause: ${silence.maxGap}s`);
            parts.push(`${silence.gapCount} pause${silence.gapCount !== 1 ? 's' : ''}`);
        } else {
            parts.push('no pauses');
        }
        report.textContent = parts.join(' · ');
        entry.appendChild(report);
    }

    transcriptEl.appendChild(entry);

    // Auto-scroll
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function clearTranscript() {
    transcriptEl.innerHTML = '';
}

// ── Timer ──────────────────────────────────────────────────────
function startTimer() {
    callStartTime = Date.now();
    timerEl.classList.add('active');
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
        const min = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const sec = String(elapsed % 60).padStart(2, '0');
        timerEl.textContent = `${min}:${sec}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    timerEl.classList.remove('active');
}
