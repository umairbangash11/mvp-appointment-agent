"""
WhatsApp booking agent — Dr. Wasim's Clinic, bilingual (Roman Urdu / English).

Clinic schedule:
  Mon / Tue / Wed  → F10 Clinic
  Thu / Fri / Sat  → Bahria Phase 4 Clinic
  Sunday           → closed

Hours: 9:00 AM – 5:00 PM  |  Slot duration: 30 min

Conversation flow:
  greeting → collect_name → collect_reason → select_slot → confirm → done

Language rules:
  - Patient writes English  → agent replies in English only
  - Patient writes Roman Urdu (or Arabic script) → agent replies in Roman Urdu only
  - NEVER use Arabic script; NEVER mix languages

- Groq LLaMA generates conversational replies; fixed strings are fallbacks.
- Structured data (slot list, confirmation, booking confirmed) always uses
  fixed format so numbers / locations are never hallucinated.
- "start" resets from any step; "done" restarts on any message.
"""
import logging
import re
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import settings
from models.patient import Patient, hash_phone
from models.appointment import Appointment, AppointmentStatus, BookingChannel
from models.conversation_session import ConversationSession, SessionChannel
from models.doctor import Doctor
from services.groq_service import chat
from services.sendgrid_service import send_booking_confirmation_email

logger = logging.getLogger(__name__)

# Detects Arabic-script characters → treated as Roman Urdu intent
_ARABIC_RE = re.compile(r"[؀-ۿ]")

# Detects common Roman Urdu words (Urdu written in Latin letters)
_ROMAN_URDU_RE = re.compile(
    r"\b(mujhe|muje|chahiye|chahye|hoon|hain|theek|achha|acha|nahin|nahi|nay|"
    r"shukriya|shukria|assalam|walaikum|apka|apni|apna|kitna|poochna|batao|"
    r"milna|mera|meri|mere|karna|karein|karenge|aap|tum|hum|han|haan|"
    r"kab|kahan|kyun|kyunke|subah|shaam|naam|abhi|kal|parson|"
    r"band|khula|waqt|masla|sabab|wajah)\b",
    re.IGNORECASE,
)

# ── Day → location mapping ─────────────────────────────────────────────────────
F10_DAYS    = {0, 1, 2}   # Monday, Tuesday, Wednesday
BAHRIA_DAYS = {3, 4, 5}   # Thursday, Friday, Saturday
# Sunday (6) = closed

# ── Keyword sets ───────────────────────────────────────────────────────────────
YES_WORDS  = {"en": {"yes", "y", "ok", "sure", "confirm", "yep", "yeah", "yup"},
              "ru": {"han", "haan", "ji", "theek", "theek hai", "bilkul", "confirm", "ok"}}
NO_WORDS   = {"en": {"no", "n", "nope", "change", "nah"},
              "ru": {"nahi", "nahin", "na", "nai", "change"}}
STOP_WORDS = {"en": {"stop", "cancel", "quit", "unsubscribe"},
              "ru": {"band", "cancel", "rukein", "rukjao"}}
HELP_TRIGGERS = {"help", "confused", "lost", "idk", "huh"}

# Words that must NOT appear in a valid patient name.
# If every word in the message is a non-name word → not a valid name.
# If ANY blacklisted word appears → not a valid name.
NAME_BLACKLIST = {
    "hi", "hello", "hey", "need", "i", "appointment", "appointments",
    "book", "booking", "help", "want", "yes", "no", "please", "ok",
    "okay", "thanks", "thank", "you", "good", "morning", "afternoon",
    "evening", "night", "start", "stop", "cancel", "doctor", "clinic",
    "visit", "schedule", "see", "get", "make", "can", "could", "would",
    "like", "just", "now", "today", "tomorrow", "asap", "urgent",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "a", "an", "the", "to", "for", "in", "at", "on", "with", "and", "or", "is", "are",
    "im", "i'm", "me", "my",
}

# ── Fallback strings (used when Groq is unavailable) ──────────────────────────
FALLBACK: dict[str, dict[str, str]] = {
    "greeting": {
        "en": (
            "Hi! How are you? 😊\n"
            f"Welcome to {settings.CLINIC_NAME}.\n"
            "I'm here to help you book an appointment.\n"
            "May I know your full name please?"
        ),
        "ru": (
            "Assalam o Alaikum! 😊\n"
            f"Dr. Wasim Clinic mein khush aamdeed!\n"
            "Appointment book karne mein madad karoonga.\n"
            "Apna poora naam batayein?"
        ),
    },
    "name_invalid": {
        "en": (
            "I didn't catch your name 😊\n"
            "Please share your full name.\n"
            "Example: Ahmed Ali"
        ),
        "ru": (
            "Naam samajh nahi aaya 😊\n"
            "Apna poora naam batayein.\n"
            "Misaal: Ahmed Ali"
        ),
    },
    "ask_reason": {
        "en": "Nice to meet you, {name}! 😊\nWhat is the reason for your visit today?",
        "ru": "Milke khushi hui, {name}! 😊\nAaj clinic aanay ka kya sabab hai?",
    },
    "no_slots": {
        "en": f"No slots available right now 😔\nPlease call us: {settings.CLINIC_PHONE}",
        "ru": f"Abhi koi slot available nahi 😔\nHamein call karein: {settings.CLINIC_PHONE}",
    },
    "slot_invalid": {
        "en": "Please reply with a number from 1 to {max} 😊",
        "ru": "1 se {max} ke darmiyan number reply karein 😊",
    },
    "sunday_closed": {
        "en": (
            f"🚫 {settings.DOCTOR_NAME} is closed on Sundays.\n"
            "Please choose a day from Monday to Saturday 😊"
        ),
        "ru": (
            f"🚫 {settings.DOCTOR_NAME} Sunday ko band hain.\n"
            "Monday se Saturday mein koi din chunein 😊"
        ),
    },
    "change_slot": {
        "en": "No problem! 😊\nWhich day works better for you?",
        "ru": "Koi baat nahi! 😊\nKonsa din aap ko suit karta hai?",
    },
    "opted_out": {
        "en": "No worries! 😊\nReply START anytime to book.",
        "ru": "Theek hai! 😊\nJab chahein START reply karein.",
    },
    "no_doctor": {
        "en": f"No doctor available right now.\nPlease call us: {settings.CLINIC_PHONE}",
        "ru": f"Abhi koi doctor available nahi.\nHamein call karein: {settings.CLINIC_PHONE}",
    },
    "help": {
        "en": "No problem! 😊 Just tell me:\n1️⃣ Your full name\n2️⃣ Reason for visit\n3️⃣ Pick a time slot\nThat's all!",
        "ru": "Koi baat nahi! 😊 Bas yeh batayein:\n1️⃣ Apna poora naam\n2️⃣ Aanay ka sabab\n3️⃣ Time slot chunein\nBas itna hi!",
    },
    "off_topic": {
        "en": "I can only help with appointment booking 😊\nShall we book you in with {doctor}?",
        "ru": "Mein sirf appointment booking mein madad kar sakta hoon 😊\nKya {doctor} se appointment book karein?",
    },
    "generic_error": {
        "en": "Oops, something went wrong 😔\nReply START to try again.",
        "ru": "Maafi! Kuch masla ho gaya 😔\nSTART reply karein dobara koshish ke liye.",
    },
}

FAQ_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "hours":    {"en": ["hours", "open", "timing", "when are"], "ru": ["timing", "waqt", "khula", "band"]},
    "location": {"en": ["location", "address", "where"],        "ru": ["address", "kahan", "jagah"]},
    "phone":    {"en": ["phone", "call", "contact"],            "ru": ["phone", "call", "number"]},
}

_BRANCH_QUESTION = (
    "Konsi branch prefer karein ge?\n\n"
    "1️⃣ F10 Islamabad\n"
    "   📅 Mon, Tue, Wed\n"
    "   ⏰ 9AM to 5PM\n\n"
    "2️⃣ Bahria Town Rawalpindi\n"
    "   📅 Thu, Fri, Sat\n"
    "   ⏰ 10AM to 6PM\n\n"
    "Reply 1 or 2"
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Return 'ru' (Roman Urdu) if Arabic script or Roman Urdu words detected, else 'en'."""
    if not text:
        return "en"
    # Arabic script → treat as Roman Urdu intent
    if _ARABIC_RE.search(text):
        return "ru"
    # Roman Urdu written in Latin letters
    if _ROMAN_URDU_RE.search(text):
        return "ru"
    return "en"


def _fb(key: str, lang: str, **kwargs) -> str:
    """Get a fallback string by key and language, with optional format args."""
    template = FALLBACK[key].get(lang, FALLBACK[key]["en"])
    return template.format(**kwargs) if kwargs else template


def _get_location(weekday: int) -> str | None:
    """Return clinic branch name for the weekday, or None if Sunday (closed)."""
    if weekday in F10_DAYS:
        return settings.CLINIC_F10
    if weekday in BAHRIA_DAYS:
        return settings.CLINIC_BAHRIA
    return None   # Sunday


def _location_short(location: str) -> str:
    """Return short branch label used in slot display lines."""
    return "F10" if "F10" in location else "Bahria"


def _is_valid_name(text: str) -> bool:
    """Return True if text looks like a real person name (min 2 words, no blacklisted words)."""
    stripped = text.strip()
    if not stripped:
        return False
    words = [re.sub(r"[^\w]", "", w).lower() for w in stripped.split()]
    words = [w for w in words if w]
    # Minimum 2 words
    if len(words) < 2:
        return False
    # No digits (e.g. "2pm", "3rd")
    if any(any(c.isdigit() for c in w) for w in words):
        return False
    # Any blacklisted word → reject
    if any(w in NAME_BLACKLIST for w in words):
        return False
    return True


def _build_schedule_display(lang: str) -> str:
    """Return formatted clinic schedule string for the given language."""
    f10    = settings.CLINIC_F10
    bahria = settings.CLINIC_BAHRIA
    doctor = settings.DOCTOR_NAME
    if lang == "ru":
        return (
            f"{doctor} ka Schedule:\n"
            f"📅 Mon, Tue, Wed → {f10}\n"
            f"📅 Thu, Fri, Sat → {bahria}\n"
            f"⏰ 9:00 AM – 5:00 PM\n"
            f"🚫 Sunday: Band"
        )
    return (
        f"{doctor}'s Schedule:\n"
        f"📅 Mon, Tue, Wed → {f10}\n"
        f"📅 Thu, Fri, Sat → {bahria}\n"
        f"⏰ 9:00 AM – 5:00 PM\n"
        f"🚫 Sunday: Closed"
    )


def _build_slot_list(slots: list[dict], lang: str) -> str:
    lines = [f"{i + 1}. {s['label']}" for i, s in enumerate(slots[:5])]
    numbered = "\n".join(lines)
    count = min(5, len(slots))
    if lang == "ru":
        return f"Available appointments:\n{numbered}\n\n1 se {count} mein se number reply karein ✅"
    return f"Available appointments:\n{numbered}\n\nReply 1 to {count} to book your slot ✅"


def _format_confirmation(data: dict, lang: str) -> str:
    """Fixed-format confirmation block (exactness matters — not Groq-generated)."""
    name   = data.get("name", "")
    slot   = data.get("selected_slot", {})
    disp   = slot.get("display", "") if isinstance(slot, dict) else str(slot)
    loc    = slot.get("location", "") if isinstance(slot, dict) else ""
    reason = data.get("reason_for_visit", "")
    if lang == "ru":
        return (
            "Please confirm karein:\n"
            f"👤 Naam: {name}\n"
            f"📅 Date: {disp}\n"
            f"📍 Location: {loc}\n"
            f"💬 Wajah: {reason}\n\n"
            "Han reply karein confirm ke liye ✅\nNa reply karein change ke liye"
        )
    return (
        "Perfect! Please confirm:\n"
        f"👤 Name: {name}\n"
        f"📅 Date: {disp}\n"
        f"📍 Location: {loc}\n"
        f"💬 Reason: {reason}\n\n"
        "Reply YES to confirm ✅\nReply NO to change"
    )


# ── Patient lookup ────────────────────────────────────────────────────────────

async def get_existing_patient(
    phone_hash: str,
    db: AsyncSession
):
    """
    Search patients table by phone hash.
    Returns patient if found.
    Returns None if new patient.
    """
    result = await db.execute(
        select(Patient).where(
            Patient.phone_hash == phone_hash
        )
    )
    return result.scalar_one_or_none()


def _branch_address_block(branch: str) -> str:
    """Return the address + Maps link for the chosen branch."""
    if "F10" in branch:
        return (
            "📍 Clinic Address:\n"
            "Plot No. 2, Bazar No. 3\n"
            "Idrees Market, F-10/2\n"
            "Adj. Shalimar Police Station\n"
            "Islamabad\n\n"
            "🗺️ Google Maps:\n"
            "https://maps.google.com/?q=Idrees+Market+F-10+Islamabad"
        )
    # Bahria (default fallback)
    return (
        "📍 Clinic Address:\n"
        "Shaheen Plaza No. 20S\n"
        "Mini Commercial Ext-1\n"
        "Phase 7, Bahria Town\n"
        "Rawalpindi\n\n"
        "🗺️ Google Maps:\n"
        "https://maps.google.com/?q=Bahria+Town+Phase+7+Rawalpindi"
    )


def _format_booking_confirmed(data: dict, lang: str) -> str:
    """Fixed-format booking confirmation (exactness matters — not Groq-generated)."""
    name   = data.get("name", "")
    slot   = data.get("selected_slot", {})
    disp   = slot.get("display", "") if isinstance(slot, dict) else str(slot)
    reason = data.get("reason_for_visit", "")
    branch = data.get("branch", slot.get("location", "")) if isinstance(slot, dict) else data.get("branch", "")
    address_block = _branch_address_block(branch)

    return (
        "✅ Appointment Confirm Ho Gayi!\n\n"
        f"👤 Naam: {name}\n"
        f"📅 Din: {disp}\n"
        f"💬 Masla: {reason}\n"
        f"🏥 Branch: {branch}\n\n"
        f"{address_block}\n\n"
        "🔔 Appointment se 1 ghanta pehle\n"
        "reminder milega!\n\n"
        "Koi sawal ho toh poochein 😊\n"
        "Reply START naya appointment book\n"
        "karne ke liye."
    )


# ── LLM integration ───────────────────────────────────────────────────────────

def _build_system_prompt(data: dict, lang: str, step: str) -> str:
    """Build system prompt for Groq: clinic rules, language, and current booking state."""
    if lang == "ru":
        lang_rule = (
            "STRICT LANGUAGE RULE — Roman Urdu ONLY:\n"
            "- The patient is writing in Roman Urdu (or used Arabic script, which means they prefer Urdu).\n"
            "- You MUST reply in Roman Urdu — that is Urdu language written with English/Latin letters.\n"
            "- Example of correct reply: 'Assalam o Alaikum! Apna poora naam batayein 😊'\n"
            "- NEVER use Arabic or Urdu script (no اردو حروف).\n"
            "- NEVER reply in English.\n"
            "- Match the patient's Roman Urdu style exactly."
        )
    else:
        lang_rule = (
            "STRICT LANGUAGE RULE — English ONLY:\n"
            "- The patient is writing in English.\n"
            "- You MUST reply in English only.\n"
            "- Example of correct reply: 'Hi! Please share your full name 😊'\n"
            "- NEVER use Arabic script.\n"
            "- NEVER use Roman Urdu or Urdu words.\n"
            "- Match the patient's English style exactly."
        )

    collected = []
    if data.get("name"):          collected.append(f"name: {data['name']}")
    if data.get("reason_for_visit"): collected.append(f"reason: {data['reason_for_visit']}")
    slot = data.get("selected_slot")
    if slot and isinstance(slot, dict):
        collected.append(f"slot: {slot.get('display')} at {slot.get('location')}")
    collected_str = ", ".join(collected) or "nothing yet"

    return (
        f"You are a friendly receptionist assistant for {settings.CLINIC_NAME} ({settings.DOCTOR_NAME}).\n"
        f"You help patients book WhatsApp appointments.\n\n"
        f"Rules:\n"
        f"- Warm, friendly, respectful — like a real receptionist\n"
        f"- Maximum 4 lines per reply — no long paragraphs\n"
        f"- Simple everyday language — no medical jargon\n"
        f"- Use friendly emojis occasionally (😊 ✅ 👋 📅)\n"
        f"- ONLY discuss appointment booking — if asked anything else, politely redirect\n"
        f"- Always tell the patient what to do next\n"
        f"- {lang_rule}\n\n"
        f"Clinic: {settings.CLINIC_NAME} | Doctor: {settings.DOCTOR_NAME}\n"
        f"Phone: {settings.CLINIC_PHONE}\n"
        f"Schedule: Mon–Wed → {settings.CLINIC_F10} | Thu–Sat → {settings.CLINIC_BAHRIA} | Sun: closed\n"
        f"Hours: 9:00 AM – 5:00 PM\n\n"
        f"Current booking step: {step}\n"
        f"Info collected: {collected_str}"
    )


async def _groq_reply(task: str, data: dict, lang: str, step: str, fallback: str) -> str:
    """Call Groq LLaMA with a task prompt; return fallback string if API is unavailable or errors."""
    if not settings.GROQ_API_KEY:
        logger.info("Using fallback (no GROQ_API_KEY, step=%s)", step)
        return fallback
    try:
        system = _build_system_prompt(data, lang, step)
        reply = await chat(
            messages=[{"role": "user", "content": task}],
            system=system,
            temperature=0.6,
        )
        logger.info("Using Groq for reply (step=%s)", step)
        return reply
    except Exception:
        logger.warning("Using fallback (Groq error, step=%s)", step)
        return fallback


# ── Slot generation ────────────────────────────────────────────────────────────

async def _get_available_slots(db: AsyncSession, branch: str | None = None) -> list[dict]:
    """Return up to 10 available 30-min slots filtered by branch.

    branch == "F10 Islamabad"      → Mon/Tue/Wed, 9:00 AM – 5:00 PM
    branch == "Bahria Rawalpindi"  → Thu/Fri/Sat, 10:00 AM – 6:00 PM
    branch is None                 → all days (backwards compat)
    """
    now = datetime.now(timezone.utc)
    slots: list[dict] = []
    current = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    if branch == "F10 Islamabad":
        allowed_days = F10_DAYS
        day_start, day_end = 9, 17
        location = settings.CLINIC_F10
    elif branch == "Bahria Rawalpindi":
        allowed_days = BAHRIA_DAYS
        day_start, day_end = 10, 18
        location = settings.CLINIC_BAHRIA
    else:
        allowed_days = F10_DAYS | BAHRIA_DAYS
        day_start, day_end = 9, 17
        location = None   # determined per slot below

    doctor = await _get_clinic_doctor(db)
    booked: set = set()
    if doctor:
        result = await db.execute(
            select(Appointment.scheduled_at).where(
                Appointment.doctor_id == doctor.id,
                Appointment.status == AppointmentStatus.scheduled,
                Appointment.scheduled_at >= now,
            )
        )
        booked = {row[0] for row in result.fetchall()}

    days_checked = 0
    while len(slots) < 10 and days_checked < 21:
        wday = current.weekday()

        # Skip days not in the allowed set (or Sunday=6 always)
        if wday not in allowed_days:
            current += timedelta(days=1)
            current = current.replace(hour=day_start, minute=0, second=0, microsecond=0)
            days_checked += 1
            continue

        if current.hour < day_start:
            current = current.replace(hour=day_start, minute=0)
        if current.hour >= day_end:
            current += timedelta(days=1)
            current = current.replace(hour=day_start, minute=0, second=0, microsecond=0)
            days_checked += 1
            continue

        slot_location = location if location else _get_location(wday)
        if current not in booked and slot_location:
            display = current.strftime("%A %b %d at %I:%M %p")
            short   = _location_short(slot_location)
            slots.append({
                "display":  display,
                "location": slot_location,
                "label":    f"{display} ({short})",
                "iso":      current.isoformat(),
            })
        current += timedelta(minutes=30)

    return slots


def _filter_slots_by_day(pref: str, slots: list[dict]) -> list[dict]:
    """Filter slot list by the patient's day preference. Returns all slots on no match."""
    pref_lower = pref.lower()

    # Sunday check
    if "sunday" in pref_lower or pref_lower.strip() in {"sun", "sunday"}:
        return []   # caller shows closed message

    day_map = {
        "monday": "Monday",    "mon": "Monday",
        "tuesday": "Tuesday",  "tue": "Tuesday",  "tues": "Tuesday",
        "wednesday": "Wednesday", "wed": "Wednesday",
        "thursday": "Thursday","thu": "Thursday", "thur": "Thursday",
        "friday": "Friday",    "fri": "Friday",
        "saturday": "Saturday","sat": "Saturday",
    }
    target = None
    for word, day_name in day_map.items():
        if word in pref_lower:
            target = day_name
            break

    if target:
        filtered = [s for s in slots if s["display"].startswith(target)]
        return filtered if filtered else slots   # fall back to all if none on that day

    return slots


# ── Session management ─────────────────────────────────────────────────────────

async def handle_whatsapp_message(phone: str, text: str, language: str, db: AsyncSession) -> tuple[str, str]:
    """Entry point called by the WhatsApp webhook route for every inbound message."""
    phone_hash = hash_phone(phone)
    session    = await _get_or_create_session(phone_hash, db)
    data: dict = session.collected_data or {}

    session_lang = data.get("_language", "en")
    # Detect language from message only when it's long enough to be meaningful;
    # short replies like "1", "2", "yes", "no" inherit the session language.
    if len(text.strip()) > 3:
        lang = detect_language(text)
    else:
        lang = session_lang
    data["_language"] = lang

    step  = session.current_step or "greeting"
    reply = await _process_step(step, text.strip(), data, phone, lang, db)

    session.current_step    = data.get("_next_step", step)
    session.collected_data  = {k: v for k, v in data.items() if k != "_next_step"}
    session.expires_at      = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.commit()

    return reply, lang


def _reset(data: dict, lang: str) -> None:
    """Clear all session data and restart the flow from the collect_name step."""
    data.clear()
    data["_language"]  = lang
    data["_next_step"] = "collect_name"


async def _get_or_create_session(phone_hash: str, db: AsyncSession) -> ConversationSession:
    """Fetch an active WhatsApp session for this phone hash, or create a fresh one."""
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.phone_hash == phone_hash,
            ConversationSession.channel    == SessionChannel.whatsapp,
            ConversationSession.expires_at > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ConversationSession(
            phone_hash    = phone_hash,
            channel       = SessionChannel.whatsapp,
            current_step  = "greeting",
            collected_data= {},
            expires_at    = datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(session)
        await db.flush()
    return session


# ── State machine ──────────────────────────────────────────────────────────────

async def _process_step(step: str, message: str, data: dict, phone: str, lang: str, db: AsyncSession) -> str:
    """Route an inbound message to the correct step handler in the booking state machine."""
    msg_lower = message.lower().strip()

    # ── Global: START resets from any step ────────────────────────────────────
    if msg_lower == "start":
        _reset(data, lang)
        return _fb("greeting", lang)

    # ── Global: STOP opts out ─────────────────────────────────────────────────
    if msg_lower in STOP_WORDS["en"] or msg_lower in STOP_WORDS["ru"]:
        _reset(data, lang)
        data["_next_step"] = "greeting"
        return _fb("opted_out", lang)

    # ── Global: HELP ──────────────────────────────────────────────────────────
    if (msg_lower in HELP_TRIGGERS
            or "don't understand" in msg_lower
            or "dont understand" in msg_lower
            or msg_lower == "?"):
        task = (
            "Patient seems confused. Warmly explain the 3 steps: "
            "1) share full name, 2) reason for visit, 3) pick a time slot. Keep it very short."
        )
        return await _groq_reply(task, data, lang, step, fallback=_fb("help", lang))

    # ── FAQ (static — never hallucinated) ─────────────────────────────────────
    for category, kws in FAQ_KEYWORDS.items():
        if any(kw in msg_lower for kw in kws["en"]) or any(kw in msg_lower for kw in kws["ru"]):
            answer = _faq_answer(category, lang)
            if answer:
                return answer

    # ── STEP: greeting ────────────────────────────────────────────────────────
    if step == "greeting":
        data["_next_step"] = "collect_name"
        return _fb("greeting", lang)

    # ── STEP: collect_name ────────────────────────────────────────────────────
    if step == "collect_name":
        if not _is_valid_name(message):
            data["_next_step"] = "collect_name"
            task = (
                "Patient sent something that is not a real name (e.g. a greeting or a request). "
                "Politely apologise and ask them to share their full name. "
                "Give a friendly example like 'Ahmed Ali' or 'Sara Khan'."
            )
            return await _groq_reply(task, data, lang, step, fallback=_fb("name_invalid", lang))

        data["name"] = message.strip()
        data["_next_step"] = "collect_reason"
        task = (
            f"Patient's name is {data['name']}. Greet them by name warmly. "
            f"Ask what the reason for their visit is today."
        )
        return await _groq_reply(
            task, data, lang, step,
            fallback=_fb("ask_reason", lang, name=data["name"]),
        )

    # ── STEP: collect_reason ──────────────────────────────────────────────────
    if step == "collect_reason":
        reason = message.strip()
        if len(reason) < 2:
            data["_next_step"] = "collect_reason"
            task = "Patient didn't provide a clear reason. Ask again what they'd like to see the doctor about."
            return await _groq_reply(
                task, data, lang, step,
                fallback=_fb("ask_reason", lang, name=data.get("name", "")),
            )

        data["reason_for_visit"] = reason
        data["_next_step"] = "collect_branch"
        return _BRANCH_QUESTION

    # ── STEP: collect_branch ──────────────────────────────────────────────────
    if step == "collect_branch":
        choice = message.strip()
        if choice == "1":
            data["branch"] = "F10 Islamabad"
        elif choice == "2":
            data["branch"] = "Bahria Rawalpindi"
        else:
            data["_next_step"] = "collect_branch"
            return "Please reply 1 or 2 only 😊\n\n" + _BRANCH_QUESTION

        data["_next_step"] = "collect_datetime"
        task = (
            f"Patient chose {data['branch']}. Confirm their branch warmly in 1 line "
            f"and ask which day and time works for them."
        )
        fallback = f"Great choice! 😊 Which day and time works for you at {data['branch']}?"
        return await _groq_reply(task, data, lang, step, fallback=fallback)

    # ── STEP: collect_datetime ────────────────────────────────────────────────
    if step == "collect_datetime":
        branch = data.get("branch")
        slots  = await _get_available_slots(db, branch=branch)
        if not slots:
            data["_next_step"] = "greeting"
            return _fb("no_slots", lang)

        filtered = _filter_slots_by_day(message, slots)
        if not filtered:
            # Sunday or no match — use all branch slots
            filtered = slots

        data["_available_slots"] = filtered
        data["_next_step"] = "select_slot"
        slot_list = _build_slot_list(filtered, lang)
        return slot_list

    # ── STEP: select_slot ─────────────────────────────────────────────────────
    if step == "select_slot":
        slots = data.get("_available_slots", [])
        try:
            idx = int(message.strip()) - 1
            if idx < 0 or idx >= min(5, len(slots)):
                raise ValueError
            data["selected_slot"] = slots[idx]
            data["_next_step"]    = "confirm"
            # Confirmation always uses fixed format
            return _format_confirmation(data, lang)
        except (ValueError, IndexError):
            task = (
                f"Patient replied with an invalid number. "
                f"Ask them to reply with a number from 1 to {min(5, len(slots))}."
            )
            return await _groq_reply(
                task, data, lang, step,
                fallback=_fb("slot_invalid", lang, max=min(5, len(slots))),
            )

    # ── STEP: confirm ─────────────────────────────────────────────────────────
    if step == "confirm":
        if msg_lower in YES_WORDS["en"] or msg_lower in YES_WORDS["ru"]:
            result = await _finalize_booking(data, phone, lang, db)
            data["_next_step"] = "done"
            return result

        if msg_lower in NO_WORDS["en"] or msg_lower in NO_WORDS["ru"]:
            data.pop("selected_slot", None)
            data["_next_step"] = "change_slot"
            task = "Patient wants to change their appointment. Say no problem warmly and ask which day works better for them."
            return await _groq_reply(task, data, lang, step, fallback=_fb("change_slot", lang))

        task = "Patient's YES/NO response was unclear. Ask them to reply YES to confirm or NO to change."
        return await _groq_reply(
            task, data, lang, step,
            fallback="Reply YES to confirm ✅ or NO to change 😊",
        )

    # ── STEP: change_slot ─────────────────────────────────────────────────────
    if step == "change_slot":
        # Sunday check
        if "sunday" in msg_lower or msg_lower.strip() == "sun":
            task = (
                f"Patient asked for Sunday. Explain that {settings.DOCTOR_NAME} is closed on Sundays. "
                f"Ask them to choose Mon–Sat."
            )
            return await _groq_reply(task, data, lang, step, fallback=_fb("sunday_closed", lang))

        all_slots  = data.get("_available_slots") or await _get_available_slots(db, branch=data.get("branch"))
        data["_available_slots"] = all_slots
        filtered   = _filter_slots_by_day(message, all_slots)

        if not filtered:
            data["_next_step"] = "greeting"
            return _fb("no_slots", lang)

        data["_next_step"] = "select_slot"
        task = (
            f"Patient prefers a different day. Show them updated slots. 1–2 line warm intro only."
        )
        intro     = await _groq_reply(task, data, lang, step,
                                      fallback="Here are the available slots for that day:")
        slot_list = _build_slot_list(filtered, lang)
        return f"{intro}\n\n{slot_list}"

    # ── STEP: done ────────────────────────────────────────────────────────────
    if step == "done":
        _reset(data, lang)
        return _fb("greeting", lang)

    return _fb("generic_error", lang)


# ── FAQ answers ────────────────────────────────────────────────────────────────

def _faq_answer(category: str, lang: str) -> str | None:
    if category == "hours":
        return (f"We're open Mon–Sat, 9:00 AM – 5:00 PM 🕐\nSunday is closed."
                if lang == "en"
                else "Hum Mon–Sat, 9:00 AM – 5:00 PM khule hain 🕐\nSunday band hai.")
    if category == "location":
        return (f"Mon/Tue/Wed → {settings.CLINIC_F10} 📍\nThu/Fri/Sat → {settings.CLINIC_BAHRIA} 📍"
                if lang == "en"
                else f"Mon/Tue/Wed → {settings.CLINIC_F10} 📍\nThu/Fri/Sat → {settings.CLINIC_BAHRIA} 📍")
    if category == "phone":
        return (f"Call us: {settings.CLINIC_PHONE} 📞"
                if lang == "en"
                else f"Hamein call karein: {settings.CLINIC_PHONE} 📞")
    return None


# ── Doctor lookup ──────────────────────────────────────────────────────────────

async def _get_clinic_doctor(db: AsyncSession) -> Doctor | None:
    if settings.CLINIC_DOCTOR_EMAIL:
        result = await db.execute(
            select(Doctor).where(
                Doctor.email == settings.CLINIC_DOCTOR_EMAIL,
                Doctor.is_verified.is_(True),
            )
        )
        doctor = result.scalar_one_or_none()
        if doctor:
            return doctor

    result = await db.execute(
        select(Doctor)
        .where(Doctor.is_verified.is_(True))
        .order_by(Doctor.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Booking ────────────────────────────────────────────────────────────────────

async def _finalize_booking(data: dict, phone: str, lang: str, db: AsyncSession) -> str:
    phone_hash = hash_phone(phone)

    result  = await db.execute(select(Patient).where(Patient.phone_hash == phone_hash))
    patient = result.scalar_one_or_none()
    if not patient:
        patient = Patient(phone_hash=phone_hash, name=data.get("name", ""))
        db.add(patient)
        await db.flush()

    doctor = await _get_clinic_doctor(db)
    if not doctor:
        return _fb("no_doctor", lang)

    slot = data.get("selected_slot", {})
    slot_display = slot.get("display", "") if isinstance(slot, dict) else str(slot)
    location     = slot.get("location", "") if isinstance(slot, dict) else ""
    scheduled_at = _parse_slot_string(slot_display)

    appointment = Appointment(
        doctor_id        = doctor.id,
        patient_id       = patient.id,
        scheduled_at     = scheduled_at,
        duration_minutes = 30,
        reason_for_visit = data.get("reason_for_visit", "General consultation"),
        status           = AppointmentStatus.scheduled,
        booking_channel  = BookingChannel.whatsapp,
        insurance_snapshot = {"location": location},
    )
    db.add(appointment)
    await db.commit()

    if patient.email:
        send_booking_confirmation_email(
            to_email       = patient.email,
            patient_name   = patient.name or "Patient",
            doctor_name    = doctor.name,
            clinic_name    = settings.CLINIC_NAME,
            appointment_dt = slot_display,
            reference_id   = str(appointment.id),
        )

    # Booking confirmed always uses fixed format
    return _format_booking_confirmed(data, lang)


def _parse_slot_string(slot: str) -> datetime:
    """Parse a slot display string like 'Monday Sep 14 at 10:00 AM' to a UTC datetime."""
    try:
        year = datetime.now(timezone.utc).year
        dt   = datetime.strptime(f"{slot} {year}", "%A %b %d at %I:%M %p %Y")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc) + timedelta(days=1, hours=9)
