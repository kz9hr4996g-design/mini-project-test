"""WhatsApp notifications via the Twilio Messages API.

Sends a short summary of each CIO decision to one or more WhatsApp numbers.
Disabled (no-op) unless TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and WHATSAPP_TO
are all set.

Environment:
  TWILIO_ACCOUNT_SID    -- Twilio account SID (ACxxxxxxxx...).
  TWILIO_AUTH_TOKEN     -- Twilio auth token.
  TWILIO_WHATSAPP_FROM  -- Sender, e.g. ``whatsapp:+14155238886`` (Twilio sandbox).
  WHATSAPP_TO           -- Comma-separated recipients in E.164, e.g. ``+447700900123``.
  WHATSAPP_VERDICTS     -- Comma-separated verdicts to alert on (default ``INVEST,MONITOR``).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
DEFAULT_SANDBOX_FROM = "whatsapp:+14155238886"
MAX_BODY_CHARS = 1600  # Twilio WhatsApp body limit

VERDICT_EMOJI = {"INVEST": "🟢", "MONITOR": "🟡", "PASS": "🔴"}


def _whatsapp_address(number: str) -> str:
    number = number.strip()
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def get_recipients() -> list[str]:
    raw = os.environ.get("WHATSAPP_TO", "")
    return [_whatsapp_address(n) for n in raw.split(",") if n.strip()]


def is_enabled() -> bool:
    return bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and get_recipients()
    )


def should_notify(final_verdict: str) -> bool:
    raw = os.environ.get("WHATSAPP_VERDICTS", "INVEST,MONITOR")
    allowed = {v.strip().upper() for v in raw.split(",") if v.strip()}
    return final_verdict.upper() in allowed


def format_decision_message(ticker: str, decision: dict[str, Any]) -> str:
    """Build the WhatsApp text for a CIO decision dict (CIODecision.model_dump())."""
    verdict = decision.get("final_verdict", "?")
    lines = [
        f"{VERDICT_EMOJI.get(verdict, '⚪')} *{ticker}: {verdict}*",
        f"Conviction: {decision.get('conviction_score', '?')}/100",
        f"Allocation: {float(decision.get('suggested_allocation_pct') or 0):.1f}%",
        f"Risk: {decision.get('risk_rating', '?')} | Horizon: {decision.get('time_horizon', '?')}",
    ]

    catalysts = decision.get("key_catalysts") or []
    if catalysts:
        lines.append("")
        lines.append("*Catalysts*")
        lines.extend(f"• {c}" for c in catalysts[:3])

    kills = decision.get("kill_conditions") or []
    if kills:
        lines.append("")
        lines.append("*Kill conditions*")
        lines.extend(f"• {k}" for k in kills[:3])

    body = "\n".join(lines)
    if len(body) > MAX_BODY_CHARS:
        body = body[: MAX_BODY_CHARS - 1] + "…"
    return body


def send_whatsapp(body: str, recipients: list[str] | None = None) -> list[str]:
    """Send ``body`` to each recipient. Returns the Twilio message SIDs.

    Raises httpx.HTTPStatusError on a Twilio error so callers can retry.
    """
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    sender = _whatsapp_address(os.environ.get("TWILIO_WHATSAPP_FROM", DEFAULT_SANDBOX_FROM))
    recipients = recipients if recipients is not None else get_recipients()

    message_sids: list[str] = []
    with httpx.Client(auth=(sid, token), timeout=10.0) as client:
        for to in recipients:
            resp = client.post(
                TWILIO_API_URL.format(sid=sid),
                data={"From": sender, "To": to, "Body": body},
            )
            if resp.is_error:
                logger.error("Twilio WhatsApp send to %s failed: %s %s", to, resp.status_code, resp.text)
            resp.raise_for_status()
            message_sids.append(resp.json().get("sid", ""))
            logger.info("WhatsApp message sent to %s", to)
    return message_sids
