"""60db cloud provider helpers — STT, LLM, TTS.

Drop-in companion for ``translation.py``. Activated by setting
``PROVIDER=sixtydb`` in the environment. Each function mirrors what
the OpenAI/ElevenLabs leg of the pipeline does, so callers can branch
on the active provider without restructuring the Flask app.

Endpoints (per https://docs.60db.ai):
  - STT  : POST  https://api.60db.ai/stt           (multipart audio)
  - LLM  : POST  https://api.60db.ai/v1/chat/completions
  - TTS  : WSS   wss://api.60db.ai/ws/tts          (realtime LINEAR16 24kHz)

Auth everywhere: ``Authorization: Bearer ${SIXTYDB_API_KEY}``.
"""

from __future__ import annotations

import base64
import io
import json
import os
import struct
import wave

import requests

API_BASE = os.environ.get("SIXTYDB_API_BASE", "https://api.60db.ai").rstrip("/")
WS_BASE = API_BASE.replace("https://", "wss://").replace("http://", "ws://")

LLM_MODEL = os.environ.get("SIXTYDB_LLM_MODEL", "60db-tiny")
TTS_SAMPLE_RATE = int(os.environ.get("SIXTYDB_TTS_SAMPLE_RATE", "24000"))


def _key() -> str:
    """Resolve the API key; raise a clear error if missing."""
    key = os.environ.get("SIXTYDB_API_KEY")
    if not key:
        raise RuntimeError(
            "SIXTYDB_API_KEY env var is not set. Required when PROVIDER=sixtydb."
        )
    return key


# -------------------- STT ---------------------------------------------------


def transcribe_chunk(filepath: str, language: str | None = None) -> str:
    """Send an audio file to ``POST /stt`` and return the transcript text.

    Diarization is forced off — translation.py owns the chunking and we only
    need plain text per chunk to match the Whisper return shape.
    """
    url = f"{API_BASE}/stt"
    headers = {"Authorization": f"Bearer {_key()}"}
    data: dict[str, str] = {"diarize": "false"}
    if language:
        data["language"] = language

    with open(filepath, "rb") as fh:
        files = {"file": (os.path.basename(filepath), fh, "audio/mpeg")}
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    resp.raise_for_status()
    body = resp.json()
    return str(body.get("text", "")).strip()


# -------------------- LLM ---------------------------------------------------


def chat_translate(chunk: str, target_language: str) -> str:
    """Run one ``/v1/chat/completions`` turn with the same prompt translation.py
    uses for OpenAI. Returns the assistant's reply string.
    """
    url = f"{API_BASE}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }
    body = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You're a professional language translator.",
            },
            {
                "role": "user",
                "content": (
                    f"Translate {chunk} to {target_language}, "
                    "don't say anything else except the translation."
                ),
            },
        ],
        "stream": False,
        "temperature": 0.3,
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return str(
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
    ).strip()


# -------------------- TTS over WebSocket ------------------------------------


def synthesize_ws(text: str, voice_id: str) -> bytes:
    """Open ``/ws/tts``, speak ``text`` in ``voice_id``, return a WAV file blob.

    60db's WS TTS emits raw LINEAR16 PCM at ``TTS_SAMPLE_RATE`` (24 kHz by
    default). The existing translation.py pipeline expects bytes it can hand
    off as ``audio/mpeg`` over SocketIO; wrapping the PCM in a WAV container
    keeps the browser side working (just change the mime-type emit to
    ``audio/wav`` on the consumer side, see translation.py).
    """
    try:
        from websockets.sync.client import connect  # websockets >= 12
    except ImportError as exc:
        raise RuntimeError(
            "websockets>=12 not installed. Run: pip install -r requirements.txt"
        ) from exc

    url = f"{WS_BASE}/ws/tts?apiKey={_key()}"
    pcm_chunks: list[bytes] = []

    with connect(url) as ws:
        _await_msg(ws, "connection_established")

        ws.send(
            json.dumps(
                {
                    "type": "create_context",
                    "voice_id": voice_id,
                    "audio_encoding": "LINEAR16",
                    "sample_rate_hertz": TTS_SAMPLE_RATE,
                }
            )
        )
        created = _await_msg(ws, "context_created")
        context_id = str(created.get("context_id", ""))

        ws.send(json.dumps({"type": "send_text", "text": text, "context_id": context_id}))
        ws.send(json.dumps({"type": "flush_context", "context_id": context_id}))

        # Drain audio_chunk frames until flush_completed arrives.
        for raw in ws:
            if not isinstance(raw, str):
                continue
            msg = json.loads(raw)
            kind = msg.get("type")
            if kind == "audio_chunk":
                b64 = msg.get("audioContent") or msg.get("audio")
                if b64:
                    pcm_chunks.append(base64.b64decode(b64))
            elif kind == "flush_completed":
                break
            elif kind == "error":
                raise RuntimeError(
                    f"60db /ws/tts error: {msg.get('message', 'unknown')}"
                )

        try:
            ws.send(json.dumps({"type": "close_context", "context_id": context_id}))
        except Exception:
            pass

    pcm = b"".join(pcm_chunks)
    return _pcm_to_wav(pcm, sample_rate=TTS_SAMPLE_RATE)


def _await_msg(ws, type_name: str) -> dict:
    """Block until a JSON message of the given ``type`` arrives on the socket."""
    for raw in ws:
        if not isinstance(raw, str):
            continue
        msg = json.loads(raw)
        if msg.get("type") == "error":
            raise RuntimeError(f"60db /ws/tts error: {msg.get('message', 'unknown')}")
        if msg.get("type") == type_name:
            return msg
    raise RuntimeError(f"60db /ws/tts closed before '{type_name}' was received")


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw mono LINEAR16 PCM bytes in a WAV container so the browser can
    play it directly. PCM is little-endian int16, mono."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)            # int16
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    # Sanity check — empty PCM should still produce a valid 44-byte header.
    assert len(buf.getvalue()) >= 44, struct.calcsize("<4sI4s")
    return buf.getvalue()


def default_voice_id() -> str:
    """Resolve the default 60db voice id from env. Required if the SocketIO
    voice picker hasn't sent one yet."""
    voice = os.environ.get("SIXTYDB_DEFAULT_VOICE_ID")
    if not voice:
        raise RuntimeError(
            "SIXTYDB_DEFAULT_VOICE_ID env var is not set. Pick a voice id "
            "from GET https://api.60db.ai/default-voices."
        )
    return voice


# -------------------- LLM streaming -----------------------------------------


def chat_stream(chunk: str, target_language: str):
    """SSE-streaming variant of ``chat_translate``. Yields content deltas.

    Useful for surfacing the partial translation to the browser before the
    full reply lands. Stops on ``data: [DONE]`` per OpenAI-compat SSE.
    """
    url = f"{API_BASE}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You're a professional language translator."},
            {
                "role": "user",
                "content": (
                    f"Translate {chunk} to {target_language}, "
                    "don't say anything else except the translation."
                ),
            },
        ],
        "stream": True,
        "temperature": 0.3,
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    with requests.post(url, headers=headers, json=body, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            payload = raw[5:].strip()
            if payload == "[DONE]":
                return
            try:
                msg = json.loads(payload)
            except Exception:
                continue
            delta = (((msg.get("choices") or [{}])[0]).get("delta") or {}).get("content")
            if delta:
                yield str(delta)


# -------------------- TTS alternatives (REST sync + NDJSON) -----------------


def synthesize_sync(text: str, voice_id: str, output_format: str = "mp3") -> bytes:
    """``POST /tts-synthesize`` — single base64 payload decoded to raw bytes.

    Use when you want MP3 out (no WAV-wrap) and don't need the WebSocket's
    sub-second time-to-first-byte. Compatible with the same SocketIO emit
    flow the ElevenLabs leg already uses.
    """
    url = f"{API_BASE}/tts-synthesize"
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "voice_id": voice_id,
        "enhance": True,
        "speed": 1.0,
        "stability": 50,
        "similarity": 75,
        "output_format": output_format,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success") or not data.get("audio_base64"):
        raise RuntimeError(
            f"60db /tts-synthesize returned no audio: {data.get('message', 'unknown')}"
        )
    return base64.b64decode(data["audio_base64"])


def synthesize_stream(text: str, voice_id: str, output_format: str = "mp3"):
    """``POST /tts-stream`` — yields decoded audio bytes per NDJSON line.

    Lower time-to-first-byte than ``synthesize_sync``; matches the streamed
    shape of the ElevenLabs ``/text-to-speech/{voice}/stream`` endpoint.
    """
    url = f"{API_BASE}/tts-stream"
    headers = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "voice_id": voice_id,
        "output_format": output_format,
    }
    with requests.post(url, headers=headers, json=body, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=True):
            line = (raw or "").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            kind = msg.get("type")
            if kind == "error":
                raise RuntimeError(
                    f"60db /tts-stream error: {msg.get('message', 'unknown')}"
                )
            if kind == "complete":
                return
            b64 = msg.get("audioContent")
            if b64:
                yield base64.b64decode(b64)


# -------------------- Discovery (voices + models) ---------------------------


def _get_list(path: str) -> list[dict]:
    """``GET <path>`` with bearer auth, return the ``data`` array."""
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {_key()}"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data") if isinstance(body, dict) else body
    return list(data) if isinstance(data, list) else []


def list_default_voices() -> list[dict]:
    """``GET /default-voices`` — public voice catalog."""
    return _get_list("/default-voices")


def list_my_voices() -> list[dict]:
    """``GET /my-voices`` — voices in the caller's account."""
    return _get_list("/my-voices")


def list_tts_models() -> list[dict]:
    """``GET /tts/models`` — typically "60db Fast" and "60db Quality"."""
    return _get_list("/tts/models")


def list_stt_models() -> list[dict]:
    """``GET /stt/models`` — currently "60db-stt-v01" per docs."""
    return _get_list("/stt/models")
