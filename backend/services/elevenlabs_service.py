import logging
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER = "your_key"
_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"


async def text_to_speech(text: str) -> bytes | None:
    """Synthesize speech via ElevenLabs (single multilingual voice covers Arabic + English).

    Returns None (graceful no-op) when no real API key is configured, matching
    the SendGrid/Twilio placeholder-key pattern used elsewhere in this project.
    """
    api_key = settings.ELEVENLABS_API_KEY.strip()
    if not api_key or _PLACEHOLDER in api_key:
        logger.info("[ElevenLabs SKIP — no real key] text_to_speech skipped")
        return None

    url = f"{_BASE_URL}/{settings.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.error(
                    "ElevenLabs HTTP %s: %s", resp.status_code, resp.text[:500]
                )
                return None
            return resp.content
    except httpx.HTTPError:
        logger.exception("ElevenLabs request failed")
        return None
