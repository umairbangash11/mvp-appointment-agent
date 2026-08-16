import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"


def _credentials_ready() -> bool:
    return bool(settings.WHATSAPP_TOKEN) and bool(settings.WHATSAPP_PHONE_NUMBER_ID)


def _messages_url() -> str:
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}


async def send_whatsapp_message(to: str, body: str) -> None:
    if not _credentials_ready():
        logger.warning("Meta WhatsApp credentials not configured; skipping send to %s", to)
        return
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    await _post(payload)


async def upload_whatsapp_media(audio_bytes: bytes, mime_type: str = "audio/mpeg") -> str | None:
    """Upload audio bytes to Meta's media hosting; returns a media_id for use in send_whatsapp_audio."""
    if not _credentials_ready():
        logger.warning("Meta WhatsApp credentials not configured; skipping media upload")
        return None
    upload_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                upload_url,
                headers=_auth_headers(),
                data={"messaging_product": "whatsapp", "type": mime_type},
                files={"file": ("audio.mp3", audio_bytes, mime_type)},
            )
            if resp.status_code >= 400:
                logger.error("Meta media upload failed (%s): %s", resp.status_code, resp.text[:500])
                return None
            return resp.json().get("id")
    except httpx.HTTPError:
        logger.exception("Meta media upload request failed")
        return None


async def send_whatsapp_audio(to: str, media_id: str) -> None:
    """Send an audio message using a media_id returned by upload_whatsapp_media."""
    if not _credentials_ready():
        logger.warning("Meta WhatsApp credentials not configured; skipping audio send to %s", to)
        return
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id},
    }
    await _post(payload)


async def _post(payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_messages_url(), json=payload, headers=_auth_headers())
        if resp.status_code >= 400:
            logger.error("Meta WhatsApp send failed (%s): %s", resp.status_code, resp.text)
    except httpx.HTTPError:
        logger.exception("Meta WhatsApp send request failed")


async def download_meta_media(media_id: str) -> bytes | None:
    """Meta media is fetched in two hops: resolve the media id to a short-lived
    CDN URL, then download from that URL — both requests need the bearer token."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            meta_resp = await client.get(
                f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}",
                headers=_auth_headers(),
            )
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url")
            if not media_url:
                return None

            file_resp = await client.get(media_url, headers=_auth_headers())
            file_resp.raise_for_status()
            return file_resp.content
    except httpx.HTTPError:
        logger.exception("Failed to download Meta media %s", media_id)
        return None
