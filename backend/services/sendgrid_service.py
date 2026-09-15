from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from config.settings import settings


_PLACEHOLDER = "your-sendgrid-api-key"


def _send(to_email: str, subject: str, html_body: str) -> None:
    if not settings.SENDGRID_API_KEY or _PLACEHOLDER in settings.SENDGRID_API_KEY:
        print(f"[SendGrid SKIP — no real key] To: {to_email} | Subject: {subject}")
        return
    message = Mail(
        from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )
    try:
        client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        client.send(message)
    except Exception as exc:
        print(f"[SendGrid ERROR] {exc}")


def send_verification_email(to_email: str, token: str, doctor_name: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h2>Welcome to {settings.CLINIC_NAME}, {doctor_name}!</h2>
    <p>Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_url}">Verify Email</a></p>
    <p>This link expires in 24 hours.</p>
    <p>If you did not create an account, please ignore this email.</p>
    """
    _send(to_email, f"Verify your email — {settings.CLINIC_NAME}", html)


def send_password_reset_email(to_email: str, token: str, doctor_name: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h2>Password Reset Request</h2>
    <p>Hi {doctor_name},</p>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <p><a href="{reset_url}">Reset Password</a></p>
    <p>If you did not request a password reset, please ignore this email.</p>
    """
    _send(to_email, "Reset your password", html)


def send_booking_confirmation_email(
    to_email: str, patient_name: str, doctor_name: str,
    clinic_name: str, appointment_dt: str, reference_id: str,
) -> None:
    html = f"""
    <h2>Appointment Confirmed</h2>
    <p>Dear {patient_name},</p>
    <p>Your appointment has been scheduled:</p>
    <ul>
      <li><strong>Doctor:</strong> Dr. {doctor_name}</li>
      <li><strong>Clinic:</strong> {clinic_name}</li>
      <li><strong>Date/Time:</strong> {appointment_dt}</li>
      <li><strong>Reference ID:</strong> {reference_id}</li>
    </ul>
    <p>This appointment was booked by an AI assistant. If you need to cancel or reschedule, please call the clinic directly.</p>
    """
    _send(to_email, f"Appointment Confirmed — {clinic_name}", html)


def send_doctor_notification_email(
    to_email: str, doctor_name: str, patient_name: str,
    appointment_dt: str, booking_channel: str,
) -> None:
    html = f"""
    <h2>New Appointment Booked</h2>
    <p>Dr. {doctor_name},</p>
    <p>A new appointment has been scheduled:</p>
    <ul>
      <li><strong>Patient:</strong> {patient_name}</li>
      <li><strong>Date/Time:</strong> {appointment_dt}</li>
      <li><strong>Booked via:</strong> {booking_channel.upper()}</li>
    </ul>
    <p>Log in to your dashboard to view full details.</p>
    """
    _send(to_email, "New Appointment Booked", html)


def send_reminder_email(
    to_email: str, patient_name: str, doctor_name: str,
    clinic_name: str, appointment_dt: str,
) -> None:
    html = f"""
    <h2>Appointment Reminder</h2>
    <p>Dear {patient_name},</p>
    <p>This is a reminder of your upcoming appointment tomorrow:</p>
    <ul>
      <li><strong>Doctor:</strong> Dr. {doctor_name}</li>
      <li><strong>Clinic:</strong> {clinic_name}</li>
      <li><strong>Date/Time:</strong> {appointment_dt}</li>
    </ul>
    <p>To cancel or reschedule, please call the clinic at {clinic_name}.</p>
    """
    _send(to_email, f"Appointment Reminder — {clinic_name}", html)
