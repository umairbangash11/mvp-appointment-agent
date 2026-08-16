import base64
import logging

from fastapi import APIRouter, Request, Form, File, UploadFile, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.session import get_db
from agents.whatsapp_agent import handle_whatsapp_message, detect_language
from services.groq_service import transcribe_audio
from services.elevenlabs_service import text_to_speech
from services.meta_whatsapp_service import (
    send_whatsapp_message,
    send_whatsapp_audio,
    upload_whatsapp_media,
    download_meta_media,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook")
async def whatsapp_verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
):
    """Meta's one-time verification handshake, triggered when the callback URL is registered/edited in the App Dashboard."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="Verification failed", status_code=403)


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Meta Cloud API inbound webhook — JSON in, Graph API /messages calls out.

    Always returns 200 (Meta disables a webhook after enough non-200
    responses), so every failure path is caught and logged rather than
    raised.
    """
    try:
        payload = await request.json()

        message = _extract_message(payload)
        if message is None:
            return JSONResponse(content={"status": "ignored"})

        phone = message.get("from")
        msg_type = message.get("type")
        is_voice_input = False

        if msg_type == "text":
            text = message.get("text", {}).get("body", "").strip()
        elif msg_type == "audio":
            media_id = message.get("audio", {}).get("id")
            audio_bytes = await download_meta_media(media_id) if media_id else None
            if audio_bytes is None:
                await send_whatsapp_message(phone, "Sorry, I couldn't process that voice note. Please try again.")
                return JSONResponse(content={"status": "ok"})
            transcription = await transcribe_audio(audio_bytes, filename="voice_note.ogg")
            text = transcription["text"]
            is_voice_input = True
        else:
            await send_whatsapp_message(phone, "Sorry, I can only handle text or voice messages right now.")
            return JSONResponse(content={"status": "ok"})

        language = transcription["language"] if is_voice_input else detect_language(text)
        reply, _ = await handle_whatsapp_message(phone, text, language, db)

        if is_voice_input:
            audio_out = await text_to_speech(reply)
            if audio_out:
                media_id = await upload_whatsapp_media(audio_out)
                if media_id:
                    await send_whatsapp_audio(phone, media_id)
                    return JSONResponse(content={"status": "ok"})
                logger.warning("Meta media upload failed; falling back to text reply for %s", phone)

        await send_whatsapp_message(phone, reply)
        return JSONResponse(content={"status": "ok"})

    except Exception:
        logger.exception("Failed to process Meta WhatsApp webhook payload")
        return JSONResponse(content={"status": "error"})


def _extract_message(payload: dict) -> dict | None:
    """Pull the first inbound message out of a Meta Cloud API webhook payload.

    Messages nest under entry[].changes[].value.messages[]; status callbacks
    (sent/delivered/read receipts) carry no "messages" key and are ignored,
    as are malformed/unexpected payload shapes.
    """
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        messages = value.get("messages")
        if not messages:
            return None
        return messages[0]
    except (KeyError, IndexError, TypeError):
        return None


@router.post("/simulate")
async def whatsapp_simulate(
    phone: str = Form(...),
    text: str = Form(default=""),
    audio: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Browser WhatsApp simulator endpoint — not a Meta Graph API call, JSON in/out.

    Shares the same conversation core (handle_whatsapp_message) as /webhook so
    there is no duplicated booking logic between the real channel and the
    dev/test simulator.
    """
    is_voice_input = False
    message_text = text.strip()
    language = detect_language(message_text)

    if audio is not None:
        audio_bytes = await audio.read()
        transcription = await transcribe_audio(audio_bytes, filename=audio.filename or "voice_note.webm")
        message_text = transcription["text"]
        language = transcription["language"]
        is_voice_input = True

    reply, language = await handle_whatsapp_message(phone.strip(), message_text, language, db)

    response: dict = {
        "reply_text": reply,
        "language": language,
        "transcribed_text": message_text if is_voice_input else None,
    }
    if is_voice_input:
        audio_out = await text_to_speech(reply)
        if audio_out:
            response["audio_base64"] = base64.b64encode(audio_out).decode()

    return JSONResponse(content=response)


