from groq import AsyncGroq
from config.settings import settings

_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"


async def chat(messages: list[dict], system: str | None = None, temperature: float = 0.3) -> str:
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = await _client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=temperature,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> dict:
    """Transcribe a WhatsApp voice note via Groq Whisper, auto-detecting Arabic/English.

    Returns {"text": str, "language": "ar" | "en"}.
    """
    response = await _client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=settings.GROQ_WHISPER_MODEL,
        response_format="verbose_json",
    )
    text = (response.text or "").strip()
    detected = (getattr(response, "language", "") or "").lower()
    language = "ar" if detected.startswith("ar") else "en"
    return {"text": text, "language": language}
