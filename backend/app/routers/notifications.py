"""WhatsApp notification endpoints.

POST /api/v1/notifications/whatsapp/test -- send a sample decision message to
the configured recipients to verify the Twilio setup.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.notifications import whatsapp

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

SAMPLE_DECISION = {
    "final_verdict": "INVEST",
    "conviction_score": 72,
    "suggested_allocation_pct": 5.0,
    "risk_rating": "MEDIUM",
    "time_horizon": "6-12 months",
    "key_catalysts": ["Test message from HedgeFund V2 — WhatsApp is connected"],
    "kill_conditions": [],
}


@router.get("/whatsapp/status")
async def whatsapp_status() -> dict:
    return {
        "enabled": whatsapp.is_enabled(),
        "recipients": len(whatsapp.get_recipients()),
    }


@router.post("/whatsapp/test")
async def whatsapp_test() -> dict:
    if not whatsapp.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="WhatsApp not configured: set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and WHATSAPP_TO",
        )
    body = whatsapp.format_decision_message("TEST", SAMPLE_DECISION)
    try:
        sids = await run_in_threadpool(whatsapp.send_whatsapp, body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Twilio send failed: {exc}") from exc
    return {"sent": len(sids), "message_sids": sids}
