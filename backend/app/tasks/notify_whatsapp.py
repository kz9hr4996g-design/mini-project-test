"""Celery task: push CIO decisions to WhatsApp.

Dispatched by run_committee after the decision is persisted. Runs as its own
task so a Twilio outage never blocks or fails the analysis pipeline.
"""

from __future__ import annotations

import logging

from app.notifications import whatsapp
from app.tasks.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="app.tasks.notify_whatsapp.send_decision",
    bind=True,
    max_retries=3,
)
def send_decision(self, ticker: str, decision: dict) -> None:
    """Send a CIO decision summary to the configured WhatsApp recipients.

    Args:
        ticker: Ticker symbol the decision is for.
        decision: CIODecision.model_dump() dict.
    """
    if not whatsapp.is_enabled():
        logger.debug("WhatsApp notifications not configured — skipping %s", ticker)
        return

    verdict = decision.get("final_verdict", "")
    if not whatsapp.should_notify(verdict):
        logger.info("WhatsApp: %s verdict %s filtered by WHATSAPP_VERDICTS", ticker, verdict)
        return

    try:
        whatsapp.send_whatsapp(whatsapp.format_decision_message(ticker, decision))
    except Exception as exc:
        logger.exception("WhatsApp send failed for %s — retrying", ticker)
        raise self.retry(exc=exc, countdown=60)
