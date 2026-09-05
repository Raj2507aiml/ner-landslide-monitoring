"""
Notifications & Emergency SMS Dispatch API Routes

Exposes endpoints for dispatching automated and on-demand SMS alerts
via the Twilio Cloud Gateway to designated emergency contacts.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.services.sms_service import SmsNotificationService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class SmsAlertRequest(BaseModel):
    warning_level: str = Field("ALERT", description="Severity tier: WATCH, ALERT, or CRITICAL")
    location_name: str = Field("NER Monitored Sector", description="Target hazard sector or corridor name")
    message: str = Field(..., description="Operational alert details or advisory text")
    recipients: Optional[List[str]] = Field(default=None, description="Optional custom recipient phone numbers (+91...)")

class SmsAlertResponse(BaseModel):
    status: str = Field(..., description="Dispatch queuing status: QUEUED or ERROR")
    warning_level: str
    location_name: str
    target_recipients: List[str]
    detail: str

@router.post("/send-sms", response_model=SmsAlertResponse)
def send_alert_sms(payload: SmsAlertRequest, background_tasks: BackgroundTasks):
    """
    Dispatches an emergency early warning SMS to disaster response officers
    and verified contacts via the Twilio Cloud Gateway.
    Executes asynchronously via BackgroundTasks for sub-second UI response times.
    """
    recipients = payload.recipients if payload.recipients and len(payload.recipients) > 0 else SmsNotificationService.get_default_recipients()
    
    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No emergency phone numbers specified or configured in EMERGENCY_RECIPIENT_NUMBERS."
        )

    # Queue broadcast in background
    background_tasks.add_task(
        SmsNotificationService.broadcast_alert,
        message=payload.message,
        warning_level=payload.warning_level,
        location_name=payload.location_name,
        phone_numbers=recipients
    )

    logger.info(f"[Notifications] Queued SMS alert for {payload.location_name} to {len(recipients)} recipients.")

    return SmsAlertResponse(
        status="QUEUED",
        warning_level=payload.warning_level,
        location_name=payload.location_name,
        target_recipients=recipients,
        detail="Emergency SMS broadcast queued and dispatching via Twilio Gateway."
    )

@router.post("/test-sms")
def test_sms_gateway():
    """
    Sends an immediate verification ping to the primary verified emergency contact.
    """
    recipients = SmsNotificationService.get_default_recipients()
    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No EMERGENCY_RECIPIENT_NUMBERS configured."
        )

    primary_number = recipients[0]
    result = SmsNotificationService.send_sms(
        to_phone=primary_number,
        message="[NDMA NER TEST] Twilio Early Warning Gateway connectivity verified."
    )

    return {
        "gateway_status": "ONLINE" if result.get("success") else "FAILED",
        "result": result
    }

@router.get("/history")
def get_sms_dispatch_history():
    """
    Retrieves the recent SMS dispatch audit log.
    """
    return {
        "total_logged": len(SmsNotificationService.get_recent_dispatches()),
        "dispatches": SmsNotificationService.get_recent_dispatches()
    }
