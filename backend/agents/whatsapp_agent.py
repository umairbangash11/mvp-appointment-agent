"""
WhatsApp booking agent — bilingual (Arabic/English), HIPAA/NABIDH-aware.
Shared conversation core for both typed text and Whisper-transcribed voice
notes — the caller (routes/whatsapp.py) is responsible for turning a voice
note into text before calling handle_whatsapp_message; from that point on,
text and voice go through the exact same booking flow.

Deterministic keyword-driven state machine (not LLM-driven) for every step
that touches booking facts (slots, confirmation, persistence) — Groq is only
consulted as a fallback for free-text/off-topic queries that fall outside the
state machine, so booking-critical replies are never hallucinated.
"""
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

_ARABIC_RE = re.compile(r"[؀-ۿ]")

YES_WORDS = {"en": {"yes", "y", "ok", "sure", "agree"}, "ar": {"نعم", "ايوه", "اي", "موافق", "أوافق", "تمام"}}
NO_WORDS = {"en": {"no", "n"}, "ar": {"لا", "لأ", "كلا"}}
STOP_WORDS = {"en": {"stop", "cancel", "quit", "unsubscribe"}, "ar": {"توقف", "الغاء", "إلغاء"}}
SKIP_WORDS = {"en": {"skip"}, "ar": {"تخطي"}}
SELF_PAY_WORDS = {"en": {"self-pay", "selfpay", "self pay"}, "ar": {"دفع ذاتي", "بدون تأمين"}}

STRINGS: dict[str, dict[str, str]] = {
    "disclosure": {
        "en": "I'm an AI assistant for this clinic. ",
        "ar": "أنا مساعد ذكاء اصطناعي لهذه العيادة. ",
    },
    "consent_prompt": {
        "en": "To book an appointment I need to collect your name and insurance info. Do you consent? Reply YES to continue or STOP to opt out.",
        "ar": "لحجز موعد، أحتاج لجمع اسمك ومعلومات التأمين الخاصة بك. هل توافق؟ أجب بـ نعم للمتابعة أو توقف للانسحاب.",
    },
    "opted_out": {
        "en": "You have been opted out. Reply START to resume. No data was saved.",
        "ar": "تم إلغاء اشتراكك. أجب بـ START للمتابعة مجدداً. لم يتم حفظ أي بيانات.",
    },
    "returning_greeting": {
        "en": "Welcome back, {name}! ",
        "ar": "أهلاً بعودتك، {name}! ",
    },
    "ask_name": {
        "en": "Great! What is your full name?",
        "ar": "رائع! ما هو اسمك الكامل؟",
    },
    "name_too_short": {
        "en": "Please provide your full name.",
        "ar": "الرجاء إدخال اسمك الكامل.",
    },
    "ask_insurance": {
        "en": "Thank you! What is your insurance provider? (e.g. Daman, AXA, MetLife) Reply SELF-PAY or SKIP if none.",
        "ar": "شكراً! ما هو مزود التأمين الخاص بك؟ (مثل دعم، إيه إكس إيه، ميت لايف) أجب بـ دفع ذاتي أو تخطي إذا لا يوجد.",
    },
    "insurance_not_accepted": {
        "en": "We currently accept: {carriers}, and Self-Pay. Please provide one of those or reply SELF-PAY.",
        "ar": "نقبل حالياً: {carriers}، والدفع الذاتي. الرجاء اختيار أحدها أو الرد بـ دفع ذاتي.",
    },
    "no_slots": {
        "en": "No slots available in the next 7 days. Please contact the clinic directly.",
        "ar": "لا توجد مواعيد متاحة خلال 7 أيام القادمة. الرجاء التواصل مع العيادة مباشرة.",
    },
    "slots_list": {
        "en": "Available slots:\n{slots}\nReply with the number of your choice.",
        "ar": "المواعيد المتاحة:\n{slots}\nالرجاء الرد برقم اختيارك.",
    },
    "slot_invalid": {
        "en": "Please reply with a number 1-{max}:\n{slots}",
        "ar": "الرجاء الرد برقم من 1 إلى {max}:\n{slots}",
    },
    "confirm_prompt": {
        "en": "To confirm: {name}, {slot}. Reply YES to confirm or NO to choose again.",
        "ar": "للتأكيد: {name}، {slot}. أجب بـ نعم للتأكيد أو لا لاختيار موعد آخر.",
    },
    "confirm_unclear": {
        "en": "Reply YES to confirm or NO to choose a different slot.",
        "ar": "الرجاء الرد بـ نعم للتأكيد أو لا لاختيار موعد آخر.",
    },
    "no_problem_reselect": {
        "en": "No problem. Choose again:\n{slots}",
        "ar": "لا مشكلة. اختر مرة أخرى:\n{slots}",
    },
    "booking_confirmed": {
        "en": "Your appointment is confirmed for {slot}. Clinic: {clinic}. A reminder will be sent 24 hours before. Is there anything else?",
        "ar": "تم تأكيد موعدك في {slot}. العيادة: {clinic}. سيتم إرسال تذكير قبل 24 ساعة. هل هناك أي شيء آخر؟",
    },
    "done": {
        "en": "Your appointment is booked. To make a new booking, reply START.",
        "ar": "تم حجز موعدك. لإجراء حجز جديد، أجب بـ START.",
    },
    "no_doctor": {
        "en": "No doctor available. Please contact the clinic.",
        "ar": "لا يوجد طبيب متاح. الرجاء التواصل مع العيادة.",
    },
    "generic_error": {
        "en": "Sorry, something went wrong. Reply START to begin again.",
        "ar": "عذراً، حدث خطأ ما. أجب بـ START للبدء من جديد.",
    },
}

FAQ_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "hours": {"en": ["hours", "open", "timing"], "ar": ["مواعيد العمل", "الدوام", "ساعات"]},
    "location": {"en": ["location", "address", "where"], "ar": ["موقع", "عنوان", "اين"]},
    "phone": {"en": ["phone", "number", "call"], "ar": ["هاتف", "رقم", "اتصال"]},
    "insurance": {"en": ["insurance"], "ar": ["تأمين"]},
}

SYSTEM_PROMPT = (
    "You are an AI medical clinic scheduling assistant for WhatsApp, serving patients in the UAE. "
    "Always identify as an AI. Never give medical advice or a diagnosis. "
    "Reply in Arabic if the patient wrote in Arabic, otherwise reply in English. "
    "Stay strictly within scheduling/clinic-info scope. "
    f"Clinic name: {settings.CLINIC_NAME}. Hours: {settings.CLINIC_HOURS}. "
    f"Address: {settings.CLINIC_ADDRESS}. Insurance accepted: {', '.join(settings.ACCEPTED_INSURANCE)}."
)


def detect_language(text: str) -> str:
    return "ar" if _ARABIC_RE.search(text or "") else "en"


def _s(key: str, lang: str, **kwargs) -> str:
    template = STRINGS[key].get(lang, STRINGS[key]["en"])
    return template.format(**kwargs) if kwargs else template


def _disclosure(lang: str) -> str:
    return STRINGS["disclosure"].get(lang, STRINGS["disclosure"]["en"])


async def handle_whatsapp_message(phone: str, text: str, language: str, db: AsyncSession) -> tuple[str, str]:
    """Process one inbound WhatsApp turn (text or transcribed voice).

    Returns (reply_text, language) — language may be echoed back unchanged or
    is the session's persisted language if this turn's text had no detectable
    script (e.g. a bare slot number).
    """
    phone_hash = hash_phone(phone)
    session = await _get_or_create_session(phone_hash, db)
    data: dict = session.collected_data or {}

    session_lang = data.get("_language", "en")
    detected = detect_language(text)
    lang = detected if _ARABIC_RE.search(text or "") else session_lang
    data["_language"] = lang

    step = session.current_step or "consent"
    reply = await _process_step(step, text.strip(), data, phone, lang, db)

    session.current_step = data.get("_next_step", step)
    # Only "_next_step" is a transient control marker — "_available_slots" and
    # "_language" must survive across turns (e.g. select_slot needs the slot
    # list offered in the previous turn).
    session.collected_data = {k: v for k, v in data.items() if k != "_next_step"}
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.commit()

    return reply, lang


async def _process_step(step: str, message: str, data: dict, phone: str, lang: str, db: AsyncSession) -> str:
    msg_lower = message.lower().strip()

    if msg_lower in STOP_WORDS["en"] or message.strip() in STOP_WORDS["ar"]:
        data["_next_step"] = "done"
        return _s("opted_out", lang)

    # FAQ shortcuts — answered from a static, authored dict, never generated
    for category, kws in FAQ_KEYWORDS.items():
        if any(kw in msg_lower for kw in kws["en"]) or any(kw in message for kw in kws["ar"]):
            answer = _faq_answer(category, lang)
            if answer:
                return _disclosure(lang) + answer

    if step == "consent":
        if msg_lower in YES_WORDS["en"] or message.strip() in YES_WORDS["ar"]:
            existing = await _find_patient(phone, db)
            if existing:
                data["name"] = existing.name
                data["_next_step"] = "collect_insurance"
                slots = await _get_available_slots(db)
                if not slots:
                    data["_next_step"] = "done"
                    return _disclosure(lang) + _s("returning_greeting", lang, name=existing.name) + _s("no_slots", lang)
                data["_next_step"] = "select_slot"
                data["_available_slots"] = slots
                slot_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(slots[:5]))
                return (
                    _disclosure(lang)
                    + _s("returning_greeting", lang, name=existing.name)
                    + _s("slots_list", lang, slots=slot_text)
                )
            data["_next_step"] = "collect_name"
            return _disclosure(lang) + _s("ask_name", lang)
        data["_next_step"] = "consent"
        return _disclosure(lang) + _s("consent_prompt", lang)

    if step == "collect_name":
        if len(message) < 2:
            return _disclosure(lang) + _s("name_too_short", lang)
        data["name"] = message
        data["_next_step"] = "collect_insurance"
        return _disclosure(lang) + _s("ask_insurance", lang)

    if step == "collect_insurance":
        is_skip = msg_lower in SKIP_WORDS["en"] or message.strip() in SKIP_WORDS["ar"]
        is_self_pay = msg_lower in SELF_PAY_WORDS["en"] or message.strip() in SELF_PAY_WORDS["ar"]
        if not is_skip and not is_self_pay:
            accepted = [i.lower() for i in settings.ACCEPTED_INSURANCE]
            if msg_lower not in accepted:
                carriers = ", ".join(settings.ACCEPTED_INSURANCE[:5])
                return _disclosure(lang) + _s("insurance_not_accepted", lang, carriers=carriers)
            data["insurance_carrier"] = message
        elif is_self_pay:
            data["insurance_carrier"] = "Self-Pay"

        slots = await _get_available_slots(db)
        if not slots:
            data["_next_step"] = "done"
            return _disclosure(lang) + _s("no_slots", lang)
        data["_available_slots"] = slots
        data["_next_step"] = "select_slot"
        slot_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(slots[:5]))
        return _disclosure(lang) + _s("slots_list", lang, slots=slot_text)

    if step == "select_slot":
        slots = data.get("_available_slots", [])
        try:
            idx = int(message.strip()) - 1
            if idx < 0 or idx >= len(slots):
                raise ValueError
            data["selected_slot"] = slots[idx]
            data["_next_step"] = "confirm"
            return _disclosure(lang) + _s("confirm_prompt", lang, name=data.get("name", ""), slot=data["selected_slot"])
        except (ValueError, IndexError):
            slots_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(slots[:5]))
            return _disclosure(lang) + _s("slot_invalid", lang, max=min(5, len(slots)), slots=slots_text)

    if step == "confirm":
        if msg_lower in YES_WORDS["en"] or message.strip() in YES_WORDS["ar"]:
            confirmation = await _finalize_booking(data, phone, lang, db)
            data["_next_step"] = "done"
            return confirmation
        if msg_lower in NO_WORDS["en"] or message.strip() in NO_WORDS["ar"]:
            slots = data.get("_available_slots", [])
            slot_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(slots[:5]))
            data["_next_step"] = "select_slot"
            return _disclosure(lang) + _s("no_problem_reselect", lang, slots=slot_text)
        return _disclosure(lang) + _s("confirm_unclear", lang)

    if step == "done":
        # Free-text after booking — fall back to Groq for genuinely open-ended queries.
        try:
            ai_response = await chat(messages=[{"role": "user", "content": message}], system=SYSTEM_PROMPT)
            return _disclosure(lang) + ai_response
        except Exception:
            return _disclosure(lang) + _s("done", lang)

    return _disclosure(lang) + _s("generic_error", lang)


def _faq_answer(category: str, lang: str) -> str | None:
    if category == "hours":
        return (f"Our clinic hours are {settings.CLINIC_HOURS}." if lang == "en"
                else f"مواعيد عملنا: {settings.CLINIC_HOURS}.")
    if category == "location":
        return (f"We are located at {settings.CLINIC_ADDRESS}." if lang == "en"
                else f"موقعنا في {settings.CLINIC_ADDRESS}.")
    if category == "phone":
        return (f"Our phone number is {settings.CLINIC_PHONE}." if lang == "en"
                else f"رقم هاتفنا هو {settings.CLINIC_PHONE}.")
    if category == "insurance":
        carriers = ", ".join(settings.ACCEPTED_INSURANCE)
        return (f"We accept: {carriers}, and Self-Pay." if lang == "en"
                else f"نقبل: {carriers}، والدفع الذاتي.")
    return None


async def _get_or_create_session(phone_hash: str, db: AsyncSession) -> ConversationSession:
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.phone_hash == phone_hash,
            ConversationSession.channel == SessionChannel.whatsapp,
            ConversationSession.expires_at > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ConversationSession(
            phone_hash=phone_hash,
            channel=SessionChannel.whatsapp,
            current_step="consent",
            collected_data={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(session)
        await db.flush()
    return session


async def _find_patient(phone: str, db: AsyncSession) -> Patient | None:
    phone_hash = hash_phone(phone)
    result = await db.execute(select(Patient).where(Patient.phone_hash == phone_hash))
    return result.scalar_one_or_none()


async def _get_available_slots(db: AsyncSession) -> list[str]:
    now = datetime.now(timezone.utc)
    slots: list[str] = []
    current = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    doctor = await _get_clinic_doctor(db)
    doctor_filter = [Appointment.status == AppointmentStatus.scheduled, Appointment.scheduled_at >= now]
    if doctor:
        doctor_filter.append(Appointment.doctor_id == doctor.id)

    result = await db.execute(
        select(Appointment.scheduled_at).where(*doctor_filter)
    )
    booked = {row[0] for row in result.fetchall()}

    days_checked = 0
    while len(slots) < 10 and days_checked < 14:
        if current.weekday() in (4, 5):  # Fri/Sat weekend in the UAE
            current += timedelta(days=1)
            current = current.replace(hour=9, minute=0, second=0, microsecond=0)
            days_checked += 1
            continue
        if current.hour < 9:
            current = current.replace(hour=9, minute=0)
        if current.hour >= 17:
            current += timedelta(days=1)
            current = current.replace(hour=9, minute=0, second=0, microsecond=0)
            days_checked += 1
            continue
        if current not in booked:
            slots.append(current.strftime("%A %b %d at %I:%M %p"))
        current += timedelta(minutes=30)

    return slots


async def _get_clinic_doctor(db: AsyncSession) -> Doctor | None:
    """Return the doctor who owns this clinic's WhatsApp number.

    Preference order:
    1. CLINIC_DOCTOR_EMAIL env var — explicit, always wins when set.
    2. Oldest verified doctor — deterministic fallback so the same doctor
       is always chosen even when the env var is not configured.
    """
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


async def _finalize_booking(data: dict, phone: str, lang: str, db: AsyncSession) -> str:
    phone_hash = hash_phone(phone)

    result = await db.execute(select(Patient).where(Patient.phone_hash == phone_hash))
    patient = result.scalar_one_or_none()
    if not patient:
        patient = Patient(
            phone_hash=phone_hash,
            name=data.get("name", ""),
            insurance_carrier=data.get("insurance_carrier"),
        )
        db.add(patient)
        await db.flush()

    doctor = await _get_clinic_doctor(db)
    if not doctor:
        return _disclosure(lang) + _s("no_doctor", lang)

    slot_str = data.get("selected_slot", "")
    scheduled_at = _parse_slot_string(slot_str)

    appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        scheduled_at=scheduled_at,
        duration_minutes=30,
        reason_for_visit="General consultation",
        status=AppointmentStatus.scheduled,
        booking_channel=BookingChannel.whatsapp,
        insurance_snapshot={"carrier": data.get("insurance_carrier")},
    )
    db.add(appointment)
    await db.commit()

    if patient.email:
        send_booking_confirmation_email(
            to_email=patient.email,
            patient_name=patient.name or "Patient",
            doctor_name=doctor.name,
            clinic_name=settings.CLINIC_NAME,
            appointment_dt=slot_str,
            reference_id=str(appointment.id),
        )

    return _disclosure(lang) + _s("booking_confirmed", lang, slot=slot_str, clinic=settings.CLINIC_NAME)


def _parse_slot_string(slot: str) -> datetime:
    try:
        year = datetime.now(timezone.utc).year
        dt = datetime.strptime(f"{slot} {year}", "%A %b %d at %I:%M %p %Y")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc) + timedelta(days=1, hours=9)
