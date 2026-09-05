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
try:
    from twilio.rest import Client
except ImportError:
    Client = None

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory recent dispatch audit log (max 100 entries)
RECENT_DISPATCH_LOGS: List[Dict[str, Any]] = []

class SmsNotificationService:
    @classmethod
    def get_client(cls) -> Optional[Any]:
        """Initializes and returns a Twilio Client if credentials exist."""
        if Client is None:
            logger.warning("[SMS] twilio Python package is not installed.")
            return None

        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN

        if not sid or not token:
            logger.warning("[SMS] Twilio credentials not configured in settings.")
            return None
        try:
            return Client(sid, token)
        except Exception as e:
            logger.error(f"[SMS] Failed to initialize Twilio client: {e}")
            return None

    @classmethod
    def get_default_recipients(cls) -> List[str]:
        """Parses default emergency recipient numbers from settings."""
        raw = settings.EMERGENCY_RECIPIENT_NUMBERS or "+917786898038"
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

        sender_number = settings.TWILIO_PHONE_NUMBER or "+17372212163"
        # Sanitize and format number (strip spaces, hyphens, ensure +91 or +)
        clean_num = "".join(c for c in to_phone if c.isdigit() or c == '+').strip()
        if not clean_num.startswith("+"):
            if len(clean_num) == 10:
                clean_num = f"+91{clean_num}"
            elif len(clean_num) == 12 and clean_num.startswith("91"):
                clean_num = f"+{clean_num}"
            else:
                clean_num = f"+{clean_num}"
        target_phone = clean_num

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
    def format_report_alert_sms(
        cls,
        report: Any,
        state_name: str,
        custom_template: Optional[str] = None
    ) -> str:
        """
        Formats an SMS notification for an approved/verified hazard report.
        Allows customization via settings.SMS_ALERT_TEMPLATE or custom_template.
        Placeholders supported:
          {state_name}, {report_type}, {severity}, {latitude}, {longitude}, {description}, {id}
        """
        template = custom_template or settings.SMS_ALERT_TEMPLATE or (
            "[NDMA ALERT] {severity} {report_type} in {state_name} ({latitude:.3f}N, {longitude:.3f}E): {description}. Helpline: 1070/112"
        )
        
        # Clean and truncate description to fit standard GSM SMS packet
        raw_desc = getattr(report, "description", "") or ""
        short_desc = raw_desc.replace("\n", " ").strip()
        if len(short_desc) > 60:
            short_desc = short_desc[:57] + "..."

        rep_type = getattr(report, "report_type", "HAZARD")
        if hasattr(rep_type, "value"):
            rep_type = rep_type.value
        rep_type_formatted = str(rep_type).replace("_", " ").title()

        sev = getattr(report, "severity", "ALERT")
        if hasattr(sev, "value"):
            sev = sev.value
        sev_formatted = str(sev).upper()

        lat = float(getattr(report, "latitude", 0.0))
        lng = float(getattr(report, "longitude", 0.0))
        rep_id = getattr(report, "id", 0)

        try:
            return template.format(
                state_name=state_name,
                state=state_name,
                report_type=rep_type_formatted,
                type=rep_type_formatted,
                severity=sev_formatted,
                latitude=lat,
                lat=lat,
                longitude=lng,
                lng=lng,
                description=short_desc,
                desc=short_desc,
                id=rep_id,
                report_id=rep_id
            )
        except Exception as e:
            logger.warning(f"[SMS] Template formatting failed ({e}), using safe fallback.")
            return f"[NDMA ALERT] {sev_formatted} {rep_type_formatted} in {state_name} ({lat:.3f}N, {lng:.3f}E): {short_desc}. Helpline: 1070/112"

    @classmethod
    def get_recipients_for_region(cls, db: Any, state_name: Optional[str]) -> List[str]:
        """
        Queries all registered users belonging to the given NER state/region.
        Includes configured emergency recipient numbers as guaranteed fallback/safeguard.
        """
        phones: List[str] = []

        if db and state_name:
            try:
                from app.models.user import User
                clean_state = state_name.strip()
                # Query users matching state name or broad NER keywords
                users = db.query(User).filter(
                    User.phone.isnot(None),
                    User.phone != "",
                    (
                        User.state.ilike(f"%{clean_state}%") |
                        User.state.ilike("%North East%") |
                        User.state.ilike("%NER%")
                    )
                ).all()
                for u in users:
                    if u.phone and u.phone.strip():
                        phones.append(u.phone.strip())
            except Exception as e:
                logger.error(f"[SMS] Failed to query regional users for state {state_name}: {e}")

        # Always incorporate default emergency numbers (e.g. from settings / .env)
        default_recipients = cls.get_default_recipients()

        # Deduplicate while preserving clean order
        unique_phones: List[str] = []
        for p in phones + default_recipients:
            p_clean = "".join(c for c in p if c.isdigit() or c == '+')
            if p_clean and p_clean not in unique_phones:
                unique_phones.append(p_clean)

        return unique_phones

    @classmethod
    def broadcast_regional_alert(
        cls,
        message: str,
        recipients: List[str],
        state_name: str = "NER",
        severity: str = "ALERT"
    ) -> List[Dict[str, Any]]:
        """
        Broadcasts a regional emergency alert to all target recipients in the affected state.
        """
        logger.info(f"[SMS] Broadcasting regional alert in {state_name} ({severity}) to {len(recipients)} recipients...")
        results = []
        for phone in recipients:
            res = cls.send_sms(to_phone=phone, message=message)
            results.append(res)
        return results

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
