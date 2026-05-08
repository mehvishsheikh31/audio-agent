"""
Audio Customer Support Agent Pipeline

This module orchestrates the complete STT -> LLM -> TTS pipeline.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from src.stt.base_stt import BaseSTT, STTService
from src.llm.agent import BaseAgent, CustomerSupportAgent
from src.tts.base_tts import BaseTTS, TTSService


@dataclass
class PipelineConfig:
    """Configuration for the audio support pipeline."""
    stt_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    enable_logging: bool = True

# Add after PipelineConfig dataclass (around line 20)

@dataclass
class TranscriptData:
    """Data structure for transcript information"""
    user_input: str
    agent_response: str
    
    
class AudioSupportPipeline:
    """
    Main pipeline class that orchestrates STT -> LLM -> TTS flow.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stt: Optional[BaseSTT] = None
        self.llm_agent: Optional[BaseAgent] = None
        self.tts: Optional[BaseTTS] = None
        self.is_initialized = False

        logging.basicConfig(level=logging.INFO if config.enable_logging else logging.CRITICAL)
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """
        Initialize all pipeline components: STT, LLM Agent, and TTS.

        Raises:
            Exception: If any component fails to initialize
        """
        try:
            self.logger.info("Initializing Audio Support Pipeline...")

            # Step 1: Initialize STT
            self.logger.info("Initializing STT service...")
            self.stt = STTService(self.config.stt_config)
            await self.stt.initialize()
            self.logger.info("STT service ready.")

            # Step 2: Initialize LLM Agent
            self.logger.info("Initializing LLM agent...")
            self.llm_agent = CustomerSupportAgent(self.config.llm_config)
            await self.llm_agent.initialize()
            self.logger.info("LLM agent ready.")

            # Step 3: Initialize TTS
            self.logger.info("Initializing TTS service...")
            self.tts = TTSService(self.config.tts_config)
            await self.tts.initialize()
            self.logger.info("TTS service ready.")

            # Step 4: Verify all components are ready
            if not all([
                self.stt.is_ready(),
                self.llm_agent.is_initialized,
                self.tts.is_ready()
            ]):
                raise RuntimeError("One or more pipeline components failed to initialize.")

            self.is_initialized = True
            self.logger.info("Pipeline initialized successfully!")

        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {str(e)}")
            await self.cleanup()
            raise

    async def process_audio(self, audio_bytes: bytes, **kwargs) -> bytes:
        """
        Process audio input through the complete STT -> LLM -> TTS pipeline.

        Args:
            audio_bytes: Input audio data (WAV format recommended)
            **kwargs: Additional parameters for processing

        Returns:
            bytes: Response audio data

        Raises:
            RuntimeError: If pipeline is not initialized
        """
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        try:
            # Step 1: Speech to Text
            self.logger.info("Converting speech to text...")
            text_input = await self.stt.transcribe(audio_bytes, **kwargs)
            self.logger.info(f"Transcribed text: {text_input}")

            if not text_input or not text_input.strip():
                self.logger.warning("Empty transcription received.")
                text_input = "I didn't catch that. Could you please repeat?"

            # Step 2: Process with LLM Agent
            self.logger.info("Processing query with LLM agent...")
            agent_response = await self.llm_agent.process_query(text_input, **kwargs)
            self.logger.info(f"Agent response: {agent_response}")

            # Step 3: Text to Speech
            self.logger.info("Converting response to speech...")
            response_audio = await self.tts.synthesize(agent_response, **kwargs)
            self.logger.info("Audio response generated successfully.")

            return response_audio

        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {str(e)}")
            raise

    async def process_text(self, text_input: str, **kwargs) -> Tuple[str, bytes]:
        """
        Process text input — useful for testing without STT.

        Args:
            text_input: Text query from user
            **kwargs: Additional parameters

        Returns:
            Tuple[str, bytes]: (agent_response_text, response_audio)
        """
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        try:
            # Process with LLM Agent
            self.logger.info(f"Processing text query: {text_input}")
            agent_response = await self.llm_agent.process_query(text_input, **kwargs)
            self.logger.info(f"Agent response: {agent_response}")

            # Convert to speech
            self.logger.info("Synthesizing speech...")
            response_audio = await self.tts.synthesize(agent_response, **kwargs)

            return agent_response, response_audio

        except Exception as e:
            self.logger.error(f"Text processing failed: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, bool]:
        """
        Check the health status of all pipeline components.

        Returns:
            Dict[str, bool]: Status of each component
        """
        return {
            "pipeline_initialized": self.is_initialized,
            "stt_ready": self.stt.is_ready() if self.stt else False,
            "llm_ready": self.llm_agent.is_initialized if self.llm_agent else False,
            "tts_ready": self.tts.is_ready() if self.tts else False,
        }

    async def cleanup(self) -> None:
        """Cleanup all pipeline resources."""
        self.logger.info("Cleaning up pipeline resources...")

        try:
            if self.stt:
                await self.stt.cleanup()
            if self.llm_agent:
                await self.llm_agent.cleanup()
            if self.tts:
                await self.tts.cleanup()

            self.stt = None
            self.llm_agent = None
            self.tts = None
            self.is_initialized = False

            self.logger.info("Pipeline cleanup completed.")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise


async def create_pipeline(
    stt_config: Dict[str, Any],
    llm_config: Dict[str, Any],
    tts_config: Dict[str, Any],
    enable_logging: bool = True
) -> AudioSupportPipeline:
    """
    Factory function to create and initialize a pipeline.

    Args:
        stt_config: STT configuration dict
        llm_config: LLM configuration dict
        tts_config: TTS configuration dict
        enable_logging: Whether to enable INFO logging

    Returns:
        AudioSupportPipeline: Fully initialized pipeline instance
    """
    config = PipelineConfig(
        stt_config=stt_config,
        llm_config=llm_config,
        tts_config=tts_config,
        enable_logging=enable_logging
    )

    pipeline = AudioSupportPipeline(config)
    await pipeline.initialize()

    return pipeline


if __name__ == "__main__":
    async def main():
        import os
        from dotenv import load_dotenv
        load_dotenv()

        stt_config = {
            "model": "base"             # Whisper local model
        }
        llm_config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        }
        tts_config = {
            "voice": "en-US-AriaNeural"  # Edge TTS free voice
        }

        pipeline = await create_pipeline(stt_config, llm_config, tts_config)

        # Test with text input
        response_text, response_audio = await pipeline.process_text(
            "What is your return policy?"
        )
        print(f"\nAgent Response:\n{response_text}")
        print(f"\nAudio bytes generated: {len(response_audio)} bytes")

        # Health check
        health = await pipeline.health_check()
        print(f"\nHealth Check: {health}")

        await pipeline.cleanup()

    asyncio.run(main())