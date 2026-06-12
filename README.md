# Speech and Speech Translation App

This is a Flask web app that allows you to translate audio and video files to an audio output in any languag of your choice using OpenAI's whisper, gpt-3.5-turbo and Eleven labs. It uses the pytube, moviepy, and pydub libraries to download and process the videos, and nltk for tokenizing the text.

## Watch a simple demo of the project:

https://user-images.githubusercontent.com/96517814/229331997-4525a982-a482-462a-8a3a-559073905151.mp4

## Installation
Clone this repository and navigate to the project directory:

```bash
git clone https://github.com/<username>/<project-name>.git
cd <project-name>
```

Create a virtual environment and install the required packages:

```bash
python -m venv venv
source venv/bin/activate  # on Windows, use "venv\Scripts\activate"
pip install -r requirements.txt
```
  
## Usage
Run the app locally using Flask:

```arduino
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```
Navigate to `http://localhost:5000/` in your web browser to access the app.

## Features
- Upload audio or video files or links.
- Transcribe audio or video and generate a text output.
- Chuck words of over 3000 tokens.
- Use the OpenAI API to translate.
- Use Elevenlabs API to convert text to audio.

## 60db provider (alternative to OpenAI + ElevenLabs)

Set `PROVIDER=sixtydb` and the entire STT + LLM + TTS pipeline routes to
[60db](https://docs.60db.ai) instead. The original OpenAI/ElevenLabs path
is untouched when `PROVIDER` is unset or `openai`.

| Step | OpenAI / ElevenLabs path | 60db path |
|---|---|---|
| STT | `openai.Audio.transcribe("whisper-1", ...)` | `POST /stt` (multipart, `diarize=false`) |
| Translate | `gpt-3.5-turbo` ChatCompletion | `POST /v1/chat/completions` model `60db-tiny` |
| TTS | `POST /v1/text-to-speech/{voice}/stream` (MP3) | `wss://api.60db.ai/ws/tts` (LINEAR16 24 kHz wrapped as WAV) |

The 60db TTS path emits WAV — the SocketIO `new_audio` event carries a
`type: 'audio/wav'` field so the client picks the right mime-type.

```bash
export PROVIDER=sixtydb
export SIXTYDB_API_KEY=sk_live_...
export SIXTYDB_DEFAULT_VOICE_ID=fbb75ed2-...      # pick from GET /default-voices
# Optional overrides:
# export SIXTYDB_LLM_MODEL=60db-tiny
# export SIXTYDB_TTS_SAMPLE_RATE=24000
# export SIXTYDB_API_BASE=https://api.60db.ai
flask run
```

All 60db calls live in `provider_sixtydb.py`. To revert to OpenAI/ElevenLabs,
unset `PROVIDER` (or set it to `openai`).

### 60db surface coverage

| Surface | Function in `provider_sixtydb.py` |
|---|---|
| `POST /stt` (multipart) | `transcribe_chunk()` — used by `translation.py` STT branch |
| `POST /v1/chat/completions` (sync) | `chat_translate()` — used by `generate_response` branch |
| `POST /v1/chat/completions` (SSE) | `chat_stream()` — yields content deltas |
| `wss://api.60db.ai/ws/tts` (LINEAR16 24 kHz) | `synthesize_ws()` — wired into `audio_output` |
| `POST /tts-synthesize` (sync, base64 mp3) | `synthesize_sync()` — drop-in alt transport |
| `POST /tts-stream` (NDJSON) | `synthesize_stream()` — yields decoded chunks |
| `GET /default-voices` | `list_default_voices()` + Flask `GET /sixtydb/voices` |
| `GET /my-voices` | `list_my_voices()` + Flask `GET /sixtydb/voices` |
| `GET /tts/models` | `list_tts_models()` + Flask `GET /sixtydb/models` |
| `GET /stt/models` | `list_stt_models()` + Flask `GET /sixtydb/models` |

The browser-facing routes (`/sixtydb/voices`, `/sixtydb/models`) proxy the
server-side call so `SIXTYDB_API_KEY` never reaches the browser. They return
HTTP 400 when `PROVIDER` isn't `sixtydb`.

## Dependencies
```
- Flask
- Flask-SocketIO
- Flask-Bootstrap
- PyTube
- moviepy
- pydub
- nltk
- OpenAI API key
- Elevenlabs API key
```

## Contributing
Contributions to this project are welcome. To contribute, please follow these steps:
1. Fork this repository.
2. Create a new branch: `git checkout -b my-new-branch`
3. Make your changes and commit them: `git commit -m "Add some feature"`
4. Push to the branch: `git push origin my-new-branch`
5. Create a new pull request.
6. Please include a clear description of your changes and their purpose.
