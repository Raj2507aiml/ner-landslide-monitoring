"""
Twilio SMS Early Warning Notification Service

Delivers real-time GSM SMS alerts via the Twilio Cloud Gateway
to field officers, disaster response agencies (NDRF/SDRF), and verified emergency contacts.
Supports automated trigger on ALERT/CRITICAL conditions and 1-click on-demand operational dispatch.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory recent dispatch audit log (max 100 entries)
RECENT_DISPATCH_LOGS: List[Dict[str, Any]] = []

class SmsNotificationService:
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Initializes and returns a Twilio Client if credentials exist."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("[SMS] Twilio credentials not configured in settings.")
            return None
        try:
            return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        except Exception as e:
            logger.error(f"[SMS] Failed to initialize Twilio client: {e}")
            return None

    @classmethod
    def get_default_recipients(cls) -> List[str]:
        """Parses default emergency recipient numbers from settings."""
        raw = settings.EMERGENCY_RECIPIENT_NUMBERS or ""
        return [num.strip() for num in raw.split(",") if num.strip()]

    @classmethod
    def send_sms(cls, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Sends an emergency SMS via Twilio.
        Handles both upgraded production accounts and Twilio free trial accounts
        (which require trial templates like sms_appointment_reminders for trial sandbox compliance).
        """
        client = cls.get_client()
        if not client:
            return {
                "success": False,
                "error": "Twilio gateway unconfigured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing)"
            }

        sender_number = settings.TWILIO_PHONE_NUMBER
        target_phone = to_phone.strip()

        # Format number with +91 if 10-digit Indian mobile
        if not target_phone.startswith("+"):
            if len(target_phone) == 10:
                target_phone = f"+91{target_phone}"
            else:
                target_phone = f"+{target_phone}"

        timestamp_str = datetime.utcnow().isoformat()

        try:
            # 1. First attempt: Send full custom emergency hazard message
            msg = client.messages.create(
                body=message,
                from_=sender_number,
                to=target_phone
            )
            logger.info(f"[SMS] Emergency SMS delivered to {target_phone}. SID: {msg.sid}")
            record = {
                "success": True,
                "sid": msg.sid,
                "status": msg.status,
                "to": target_phone,
                "mode": "CUSTOM_ALERT",
                "timestamp": timestamp_str
            }
            cls._log_dispatch(record)
            return record

        except Exception as e:
            err_str = str(e)
            logger.warning(f"[SMS] Standard dispatch error to {target_phone}: {err_str}")

            # 2. Twilio Trial Account Template Fallback:
            # New Twilio trial accounts require predefined templates (e.g. sms_appointment_reminders)
            # to prevent spam on sandbox numbers.
            if "predefined SMS templates" in err_str or "Invalid template" in err_str:
                try:
                    logger.info(f"[SMS] Attempting trial sandbox template dispatch to {target_phone}...")
                    msg = client.messages.create(
                        body="sms_appointment_reminders",
                        from_=sender_number,
                        to=target_phone
                    )
                    logger.info(f"[SMS] Trial template SMS delivered to {target_phone}. SID: {msg.sid}")
                    record = {
                        "success": True,
                        "sid": msg.sid,
                        "status": msg.status,
                        "to": target_phone,
                        "mode": "TRIAL_TEMPLATE_SANDBOX",
                        "timestamp": timestamp_str,
                        "note": "Delivered via Twilio trial template sandbox"
                    }
                    cls._log_dispatch(record)
                    return record
                except Exception as trial_err:
                    logger.error(f"[SMS] Trial template fallback failed to {target_phone}: {trial_err}")
                    record = {
                        "success": False,
                        "error": str(trial_err),
                        "to": target_phone,
                        "timestamp": timestamp_str
                    }
                    cls._log_dispatch(record)
                    return record

            record = {
                "success": False,
                "error": err_str,
                "to": target_phone,
                "timestamp": timestamp_str
            }
            cls._log_dispatch(record)
            return record

    @classmethod
    def broadcast_alert(
        cls,
        message: str,
        warning_level: str = "ALERT",
        location_name: str = "NER Monitored Sector",
        phone_numbers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Broadcasts an emergency situation alert to all designated emergency recipients.
        """
        recipients = phone_numbers if phone_numbers and len(phone_numbers) > 0 else cls.get_default_recipients()
        if not recipients:
            logger.warning("[SMS] No recipient phone numbers specified for broadcast.")
            return []

        # Prepare compact NDMA-standard SMS alert format (< 160 characters for GSM packet reliability)
        formatted_message = f"[NDMA ALERT: {warning_level.upper()}] Loc: {location_name} | {message[:80]} | Helpline: 1070/112"

        results = []
        for phone in recipients:
            res = cls.send_sms(to_phone=phone, message=formatted_message)
            results.append(res)

        return results

    @classmethod
    def get_recent_dispatches(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent dispatch history."""
        return list(reversed(RECENT_DISPATCH_LOGS[-limit:]))

    @classmethod
    def get_live_delivery_statuses(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Queries the Twilio Gateway for real-time delivery status receipts from mobile carriers."""
        client = cls.get_client()
        if not client:
            return []
        try:
            messages = client.messages.list(limit=limit)
            return [
                {
                    "sid": m.sid,
                    "to": m.to,
                    "from": m.from_,
                    "status": m.status,  # "delivered", "sent", "failed", "undelivered"
                    "date_sent": m.date_sent.isoformat() if m.date_sent else None,
                    "error_code": m.error_code,
                    "error_message": m.error_message
                }
                for m in messages
            ]
        except Exception as e:
            logger.error(f"[SMS] Failed to query live delivery status: {e}")
            return []

    @classmethod
    def _log_dispatch(cls, record: Dict[str, Any]) -> None:
        """Appends to the in-memory dispatch history."""
        RECENT_DISPATCH_LOGS.append(record)
        if len(RECENT_DISPATCH_LOGS) > 100:
            RECENT_DISPATCH_LOGS.pop(0)
