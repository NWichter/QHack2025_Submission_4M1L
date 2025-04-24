import os
from typing import Optional

import chainlit as cl
from openai import OpenAI


class AudioHandler:
    def __init__(self):
        """Initialize the AudioHandler with OpenAI client."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def process_audio(self, audio_file) -> Optional[str]:
        """Process audio file and return transcribed text."""
        try:
            # Transcribe audio using Whisper API
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", file=audio_file, language="de"
            )

            return transcript.text

        except Exception as e:
            await cl.Message(
                content=f"Sorry, I could not process the audio input: {str(e)}"
            ).send()
            return None
