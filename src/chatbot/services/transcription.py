import base64
import io

from openai import OpenAI

from chatbot.config import OPENAI_API_KEY

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_audio_base64(audio_base64: str) -> str | None:
    try:
        if "," in audio_base64:
            audio_base64 = audio_base64.split(",")[1]

        audio_bytes = base64.b64decode(audio_base64)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"

        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="pt",
        )
        return transcription.text

    except Exception as e:
        print(f"[TRANSCRIPTION ERROR] Falha ao transcrever áudio: {e}")
        return None
