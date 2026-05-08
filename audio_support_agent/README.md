# 🎙️ Audio Customer Support Agent

A full-stack AI-powered customer support agent that processes voice input, generates intelligent responses, and returns audio output — with full transcript support.

**Pipeline:** `Audio Input → STT → LLM Agent → TTS → Audio Output + Transcript`

---

## 📁 Project Structure

```
audio_support_agent/
├── src/
│   ├── pipeline.py          # Core STT → LLM → TTS orchestration
│   ├── api/
│   │   └── server.py        # FastAPI REST endpoints
│   ├── stt/
│   │   └── base_stt.py      # Speech-to-Text service
│   ├── tts/
│   │   └── base_tts.py      # Text-to-Speech service
│   ├── llm/
│   │   └── agent.py         # LLM customer support agent
│   └── utils/
│       └── kb_test.py       # Knowledge base utilities
├── streamlit_app.py         # Web UI for testing
├── tests/
│   └── test_stt.py
├── data/                    # Knowledge base documents
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & create virtual environment

```bash
git clone <your-repo-url>
cd audio_support_agent
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
STT_API_KEY=your_stt_api_key_here
TTS_API_KEY=your_tts_api_key_here
```

> **Key sources:**
> - OpenAI → https://platform.openai.com/api-keys
> - Deepgram (STT) → https://console.deepgram.com/
> - ElevenLabs (TTS) → https://elevenlabs.io/

---

## 🚀 Running the Application

### Start the API server

```bash
cd audio_support_agent
python -m src.api.server
```

Server starts at `http://localhost:8000`

### Start the Streamlit UI

```bash
streamlit run streamlit_app.py
```

UI opens at `http://localhost:8501`

---

## 🌐 API Endpoints

### `GET /health`
Check status of all pipeline components.

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "pipeline_initialized": true,
    "stt_ready": true,
    "llm_ready": true,
    "tts_ready": true
  },
  "message": "All components ready"
}
```

---

### `POST /chat/text`
Send a text query and receive a text response.

```powershell
# PowerShell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/chat/text" `
  -ContentType "application/json" `
  -Body '{"text": "What is your return policy?"}'
```

**Response:**
```json
{
  "response_text": "We offer a 30-day return policy for all products...",
  "audio_available": true,
  "processing_time_ms": 950
}
```

---

### `POST /chat/audio`
Upload an audio file and receive a JSON response with base64-encoded audio + transcript.

```powershell
# PowerShell
$form = @{ audio = Get-Item "test.wav" }
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/chat/audio" -Form $form
```

**Response:**
```json
{
  "success": true,
  "audio_response": "<base64_encoded_mp3>",
  "transcript": {
    "user_input": "How long does shipping take?",
    "agent_response": "Shipping typically takes 3-5 business days..."
  },
  "processing_time_ms": 2050
}
```

---

### `GET /chat/audio/{text}`
Convert text directly to audio (TTS only, no STT or LLM).

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/chat/audio/Hello%20world"
```

---

### `POST /debug/stt`
Test the STT component in isolation.

```powershell
$form = @{ audio = Get-Item "test.wav" }
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/debug/stt" -Form $form
```

---

## 🖥️ Streamlit UI

The web interface has 4 tabs:

| Tab | Purpose |
|-----|---------|
| **Text Chat** | Type messages and see agent responses with timing |
| **Audio Chat** | Record or upload audio → plays response + shows transcript |
| **Health Monitor** | Live status of all pipeline components |
| **Documentation** | Quick reference guide |

### Audio Chat tab layout

```
┌─────────────────────┬───────────────────────────────────┐
│   Audio Controls    │         Transcript                │
│                     │                                   │
│  [Record Audio]     │  🗣️ You said:                     │
│  [Upload File]      │  "What is your return policy?"    │
│                     │                                   │
│  [Send to Agent]    │  🤖 Agent responded:              │
│                     │  "We offer a 30-day return..."    │
│                     │                                   │
│                     │  ⏱️ Processing: 2.05s             │
└─────────────────────┴───────────────────────────────────┘
```

---

## 🧪 Testing

### Create a test WAV file (if you don't have one)

```python
python -c "
import wave, struct, math
with wave.open('test.wav', 'w') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
    f.writeframes(struct.pack('<' + 'h'*16000, *[int(3000*math.sin(2*math.pi*440*i/16000)) for i in range(16000)]))
print('test.wav created')
"
```

### Run unit tests

```bash
pytest tests/ -v
```

---

## 🔧 Configuration Options

### STT Services (choose one)

| Service | Type | Env Var |
|---------|------|---------|
| OpenAI Whisper | Local model | *(no key needed)* |
| Deepgram | API | `DEEPGRAM_API_KEY` |
| AssemblyAI | API | `ASSEMBLYAI_API_KEY` |

### LLM Services (choose one)

| Service | Env Var |
|---------|---------|
| OpenAI GPT | `OPENAI_API_KEY` |
| Anthropic Claude | `ANTHROPIC_API_KEY` |

### TTS Services (choose one)

| Service | Type | Env Var |
|---------|------|---------|
| Edge TTS | Free, local | *(no key needed)* |
| ElevenLabs | API | `ELEVENLABS_API_KEY` |
| OpenAI TTS | API | `OPENAI_API_KEY` |
| Azure Speech | API | `AZURE_SPEECH_KEY` |

---

## 🛠️ Troubleshooting

**Server not starting**
- Check all required API keys are set in `.env`
- Verify virtual environment is activated
- Check port 8000 is not in use: `netstat -ano | findstr :8000`

**Audio recording not working in UI**
- Install sounddevice: `pip install sounddevice`
- Allow microphone permissions in browser/OS

**STT returns empty transcription**
- Ensure audio file is valid WAV format, 16kHz mono
- Check STT API key is correct
- Try the `/debug/stt` endpoint to isolate the issue

**`curl` commands not working on Windows**
- Use PowerShell's `Invoke-RestMethod` instead (see examples above)
- Or install Git Bash and use standard curl commands

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `langchain` | LLM agent framework |
| `chromadb` | Vector store for RAG |
| `sentence-transformers` | Embeddings |
| `pydub` / `librosa` | Audio processing |
| `streamlit` | Web UI |
| `edge-tts` | Free TTS voices |
| `openai-whisper` | Local STT model |

---

## 📄 License

MIT License — free to use and modify.