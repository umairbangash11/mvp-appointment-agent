import httpx
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from config.settings import settings

_client: Client | None = None


def _get_client() -> Client | None:
    global _client
    if _client is None:
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            return None
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def _ensure_whatsapp_prefix(phone: str) -> str:
    return phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"


def _client_ready() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID) and not settings.TWILIO_ACCOUNT_SID.startswith("AC_")


def send_whatsapp_text(to: str, body: str) -> None:
    client = _get_client()
    if not client or not _client_ready():
        return
    client.messages.create(
        body=body,
        from_=_ensure_whatsapp_prefix(settings.TWILIO_WHATSAPP_NUMBER),
        to=_ensure_whatsapp_prefix(to),
    )


def send_whatsapp_media(to: str, media_url: str, body: str = "") -> None:
    client = _get_client()
    if not client or not _client_ready():
        return
    client.messages.create(
        body=body,
        media_url=[media_url],
        from_=_ensure_whatsapp_prefix(settings.TWILIO_WHATSAPP_NUMBER),
        to=_ensure_whatsapp_prefix(to),
    )


def build_whatsapp_twiml_text(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message><Body>{_escape_xml(body)}</Body></Message></Response>"
    )


def build_whatsapp_twiml_media(media_url: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message><Media>{_escape_xml(media_url)}</Media></Message></Response>"
    )


async def download_twilio_media(media_url: str) -> bytes:
    async with httpx.AsyncClient(
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN), timeout=30.0
    ) as client:
        resp = await client.get(media_url)
        resp.raise_for_status()
        return resp.content


def validate_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Verify an inbound webhook actually came from Twilio.

    Always skipped by the caller when ENVIRONMENT == "development" (no public
    HTTPS callback URL to sign against during local dev), same convenience
    pattern used for signup email verification.
    """
    if not settings.TWILIO_AUTH_TOKEN:
        return False
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, params, signature)


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
