import httpx
import os
from datetime import date

# IMPORTANT: set RESEND_API_KEY as a real environment variable on your host
# (Render/Railway dashboard -> Environment). There is intentionally no hardcoded
# fallback key here anymore — a placeholder key baked into source code either
# doesn't work (so emails silently fail) or is a leaked credential. If this is
# unset, _send() below will log a clear warning instead of pretending to work.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_URL = "https://api.resend.com/emails"

# Your verified sender — must be from a domain you've verified in Resend
FROM_EMAIL = "Sarvpratham Edu Consultants <noreply@sarvprathameduconsultants.com>"
ADMIN_EMAIL = "edu.sarvprathampaath@gmail.com"


def _send(to: list[str], subject: str, html: str) -> bool:
    """Low-level helper — fire and forget, never raises."""
    if not RESEND_API_KEY:
        print(f"[email] RESEND_API_KEY is not set — skipping email to {to}. "
              f"Set it as an environment variable on your host.")
        return False
    try:
        resp = httpx.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"from": FROM_EMAIL, "to": to, "subject": subject, "html": html},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        # Log but don't crash the API — email failure should never break a booking
        print(f"[email] Failed to send to {to}: {e}")
        return False


# ─────────────────────────────────────────────
#  ENQUIRY EMAILS
# ─────────────────────────────────────────────

def send_enquiry_confirmation_to_user(
    name: str,
    phone: str,
    email: str | None,
    student_class: str | None,
    stream: str | None,
    course: str | None,
    city: str | None,
    message: str | None,
) -> None:
    if not email:
        return  # Can't email without address

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#222;">
      <div style="background:#1a3c5e;padding:24px 32px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:22px;">Sarvpratham Education Consultants</h1>
        <p style="color:#a8c7e8;margin:4px 0 0;">College Admissions &amp; Career Guidance</p>
      </div>
      <div style="background:#f9fafb;padding:32px;border:1px solid #e5e7eb;border-top:none;">
        <h2 style="color:#1a3c5e;margin-top:0;">We've received your enquiry, {name}! ✅</h2>
        <p style="font-size:15px;line-height:1.6;">
          Thank you for reaching out. Our counsellors will call you at <strong>{phone}</strong> within <strong>24 hours</strong>.
        </p>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin:20px 0;">
          <h3 style="margin-top:0;color:#374151;font-size:14px;text-transform:uppercase;letter-spacing:.05em;">Your Enquiry Details</h3>
          <table style="width:100%;border-collapse:collapse;font-size:14px;">
            {"<tr><td style='padding:6px 0;color:#6b7280;width:40%'>Class</td><td style='padding:6px 0;font-weight:600'>" + (student_class or "—") + "</td></tr>" if student_class else ""}
            {"<tr><td style='padding:6px 0;color:#6b7280'>Stream</td><td style='padding:6px 0;font-weight:600'>" + stream + "</td></tr>" if stream else ""}
            {"<tr><td style='padding:6px 0;color:#6b7280'>Course Interest</td><td style='padding:6px 0;font-weight:600'>" + course + "</td></tr>" if course else ""}
            {"<tr><td style='padding:6px 0;color:#6b7280'>City</td><td style='padding:6px 0;font-weight:600'>" + city + "</td></tr>" if city else ""}
          </table>
        </div>
        <p style="font-size:14px;color:#6b7280;">
          Need instant help? WhatsApp us at 
          <a href="https://wa.me/919540000270" style="color:#1a3c5e;">9540000270</a>
        </p>
      </div>
      <div style="background:#1a3c5e;padding:16px 32px;border-radius:0 0 8px 8px;text-align:center;">
        <p style="color:#a8c7e8;font-size:12px;margin:0;">
          © 2025 Sarvpratham Education Consultants · New Delhi · 
          <a href="https://sarvprathameduconsultants.com" style="color:#fff;">sarvprathameduconsultants.com</a>
        </p>
      </div>
    </div>
    """

    _send(
        to=[email],
        subject="✅ Enquiry Received — Sarvpratham Education Consultants",
        html=html,
    )


def send_enquiry_alert_to_admin(
    name: str,
    phone: str,
    email: str | None,
    student_class: str | None,
    stream: str | None,
    course: str | None,
    city: str | None,
    message: str | None,
) -> None:
    rows = [
        ("Name", name),
        ("Phone", phone),
        ("Email", email or "—"),
        ("Class", student_class or "—"),
        ("Stream", stream or "—"),
        ("Course Interest", course or "—"),
        ("City", city or "—"),
        ("Message", message or "—"),
    ]
    table_rows = "".join(
        f"<tr><td style='padding:8px 12px;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;width:35%'>{k}</td>"
        f"<td style='padding:8px 12px;border:1px solid #e5e7eb;font-weight:600'>{v}</td></tr>"
        for k, v in rows
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#222;">
      <div style="background:#1a3c5e;padding:24px 32px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">🔔 New Enquiry Received</h1>
      </div>
      <div style="padding:24px 32px;border:1px solid #e5e7eb;border-top:none;">
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          {table_rows}
        </table>
        <div style="margin-top:20px;text-align:center;">
          <a href="https://sarvprathameduconsultants.com/admin.html"
             style="background:#1a3c5e;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:14px;">
            Open Admin Dashboard →
          </a>
        </div>
      </div>
    </div>
    """

    _send(
        to=[ADMIN_EMAIL],
        subject=f"🔔 New Enquiry — {name} ({phone})",
        html=html,
    )


# ─────────────────────────────────────────────
#  BOOKING EMAILS
# ─────────────────────────────────────────────

def send_booking_confirmation_to_user(
    name: str,
    phone: str,
    slot_date: date,
    slot_time: str,
    session_type: str,
    stream: str | None,
    course: str | None,
) -> None:
    """
    Bookings don't collect email — we send confirmation via WhatsApp conceptually,
    but if you later add email to the booking form, wire it up here.
    For now, only admin gets notified.
    """
    pass  # No email field on booking form — see send_booking_alert_to_admin below


def send_booking_alert_to_admin(
    name: str,
    phone: str,
    slot_date: date,
    slot_time: str,
    session_type: str,
    stream: str | None,
    course: str | None,
) -> None:
    formatted_date = slot_date.strftime("%A, %d %B %Y")  # e.g. Monday, 23 June 2025
    rows = [
        ("Name", name),
        ("Phone", phone),
        ("Date", formatted_date),
        ("Time", slot_time),
        ("Session Type", session_type),
        ("Stream", stream or "—"),
        ("Course Interest", course or "—"),
    ]
    table_rows = "".join(
        f"<tr><td style='padding:8px 12px;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;width:35%'>{k}</td>"
        f"<td style='padding:8px 12px;border:1px solid #e5e7eb;font-weight:600'>{v}</td></tr>"
        for k, v in rows
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#222;">
      <div style="background:#0f5132;padding:24px 32px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">📅 New Call Booked</h1>
      </div>
      <div style="padding:24px 32px;border:1px solid #e5e7eb;border-top:none;">
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          {table_rows}
        </table>
        <div style="margin-top:20px;text-align:center;">
          <a href="https://sarvprathameduconsultants.com/admin.html"
             style="background:#0f5132;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:14px;">
            View Bookings Dashboard →
          </a>
        </div>
      </div>
    </div>
    """

    _send(
        to=[ADMIN_EMAIL],
        subject=f"📅 New Booking — {name} · {formatted_date} {slot_time}",
        html=html,
    )
