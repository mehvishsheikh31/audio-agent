"""
FastAPI Server for Audio Customer Support Agent

Provides REST API endpoints for the STT -> LLM -> TTS pipeline.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import time
import os

from src.pipeline import AudioSupportPipeline, create_pipeline


# ── Request / Response Models ──────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str
    parameters: Optional[Dict[str, Any]] = {}


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    message: str


class TextResponse(BaseModel):
    response_text: str
    audio_available: bool
    processing_time_ms: int


# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Audio Customer Support Agent API",
    description="REST API for the STT -> LLM -> TTS pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline: Optional[AudioSupportPipeline] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifecycle Events ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize the pipeline on server startup."""
    global pipeline

    try:
        logger.info("Starting Audio Support Agent API server...")

        stt_config = {
            "model": "base"                         # Whisper local model — no API key needed
        }

        llm_config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        }

        tts_config = {
            "voice": "en-US-AriaNeural"             # Edge TTS — no API key needed
        }

        pipeline = await create_pipeline(stt_config, llm_config, tts_config)
        logger.info("Pipeline initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {str(e)}")
        # Server still starts so you can hit /health to debug


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup pipeline on server shutdown."""
    global pipeline
    if pipeline:
        logger.info("Shutting down pipeline...")
        await pipeline.cleanup()
        pipeline = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Audio Customer Support Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — returns status of all pipeline components."""
    global pipeline

    if not pipeline:
        return HealthResponse(
            status="unhealthy",
            components={
                "pipeline_initialized": False,
                "stt_ready": False,
                "llm_ready": False,
                "tts_ready": False
            },
            message="Pipeline not initialized"
        )

    try:
        components = await pipeline.health_check()
        all_healthy = all(components.values())

        return HealthResponse(
            status="healthy" if all_healthy else "degraded",
            components=components,
            message="All components ready" if all_healthy else "Some components not ready"
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="error",
            components={},
            message=f"Health check error: {str(e)}"
        )


@app.post("/chat/text", response_model=TextResponse)
async def chat_text(request: TextRequest):
    """
    Process a text query through LLM + TTS.
    Useful for testing without audio input.
    """
    global pipeline

    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        start_time = time.time()

        response_text, response_audio = await pipeline.process_text(
            request.text,
            **request.parameters
        )

        processing_time = int((time.time() - start_time) * 1000)

        return TextResponse(
            response_text=response_text,
            audio_available=len(response_audio) > 0,
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Text processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/audio")
async def chat_audio(audio: UploadFile = File(...)):
    """
    Process audio through the full STT -> LLM -> TTS pipeline.
    Upload a WAV file and receive an MP3 response.
    """
    global pipeline

    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        logger.info(f"Received audio: {len(audio_bytes)} bytes, type: {audio.content_type}")

        response_audio = await pipeline.process_audio(audio_bytes)

        return Response(
            content=response_audio,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/audio/{text}")
async def text_to_audio(text: str):
    """
    Convert text directly to audio using TTS only.
    Useful for testing the TTS component independently.

    Example: GET /chat/audio/Hello%20world
    """
    global pipeline

    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if not pipeline.tts:
        raise HTTPException(status_code=503, detail="TTS component not available")

    try:
        audio_bytes = await pipeline.tts.synthesize(text)

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=tts_output.mp3"}
        )

    except Exception as e:
        logger.error(f"TTS failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/stt")
async def debug_stt(audio: UploadFile = File(...)):
    """
    Debug endpoint — test STT component independently.
    Upload a WAV file and receive the transcription.

    Example: curl -X POST http://localhost:8000/debug/stt -F "audio=@test.wav"
    """
    global pipeline

    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if not pipeline.stt:
        raise HTTPException(status_code=503, detail="STT component not available")

    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        transcription = await pipeline.stt.transcribe(audio_bytes)

        return {
            "transcription": transcription,
            "audio_size_bytes": len(audio_bytes)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT debug failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )