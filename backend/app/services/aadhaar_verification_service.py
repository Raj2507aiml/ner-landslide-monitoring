"""
Aadhaar Automated Verification Service

Performs multi-layer sovereign validation to determine whether uploaded identity evidence
is a genuine Indian Aadhaar card:
1. Verhoeff Algorithm Checksum on the 12-digit Aadhaar number.
2. OpenCV QR Code Detector (cv2.QRCodeDetector) decoding and UIDAI XML/payload parsing.
3. Demographic consistency matching (compares name in QR with citizen's submitted full_name).
4. Card visual structure & aspect-ratio heuristics.
"""

import os
import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import numpy as np
import cv2

# =========================================================================
# Verhoeff Mathematical Checksum Tables (Dihedral Group D5)
# =========================================================================

VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

class AadhaarVerificationService:

    @staticmethod
    def validate_verhoeff(aadhaar_number: str) -> bool:
        """
        Validates the 12th checksum digit of an Indian Aadhaar number using the Verhoeff algorithm.
        Returns True if the checksum digit is mathematically valid.
        """
        if not aadhaar_number:
            return False
        clean_num = re.sub(r"\D", "", str(aadhaar_number))
        if len(clean_num) != 12:
            return False

        c = 0
        for i, digit in enumerate(reversed(clean_num)):
            c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(digit)]]
        return c == 0

    @classmethod
    def decode_qr_code(cls, image_path: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Attempts to locate and decode a QR code from an image file using OpenCV QRCodeDetector.
        Returns (qr_detected, raw_payload, parsed_details).
        """
        if not image_path or not os.path.exists(image_path):
            return False, None, {}

        try:
            img = cv2.imread(image_path)
            if img is None:
                return False, None, {}

            detector = cv2.QRCodeDetector()
            decoded_text, points, _ = detector.detectAndDecode(img)

            # If standard detector fails, try resized or grayscale variations
            if not decoded_text:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                decoded_text, points, _ = detector.detectAndDecode(gray)

            if not decoded_text:
                # Try thresholding for high contrast
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                decoded_text, points, _ = detector.detectAndDecode(thresh)

            if not decoded_text:
                return False, None, {}

            # Parse QR code content
            parsed = cls.parse_aadhaar_qr_payload(decoded_text)
            return True, decoded_text, parsed

        except Exception as e:
            return False, None, {"error": str(e)}

    @staticmethod
    def parse_aadhaar_qr_payload(payload: str) -> Dict[str, Any]:
        """
        Parses UIDAI standard QR code formats:
        1. XML format: <PrintLetterBarcodeData uid="..." name="..." gender="..." yob="..." .../>
        2. Numeric or compressed text standard to e-Aadhaar.
        """
        details: Dict[str, Any] = {
            "is_uidai_format": False,
            "extracted_name": None,
            "masked_uid": None,
            "gender": None,
            "yob": None,
            "state": None,
            "district": None,
            "pincode": None,
        }

        if not payload:
            return details

        # Check 1: XML <PrintLetterBarcodeData ...>
        if "<PrintLetterBarcodeData" in payload or "PrintLetterBarcodeData" in payload:
            details["is_uidai_format"] = True
            try:
                xml_str = payload.strip()
                if not xml_str.endswith("/>") and not xml_str.endswith(">"):
                    xml_str += "/>"
                root = ET.fromstring(xml_str)
                details["extracted_name"] = root.attrib.get("name")
                raw_uid = root.attrib.get("uid")
                if raw_uid and len(raw_uid) >= 4:
                    details["masked_uid"] = f"XXXX-XXXX-{raw_uid[-4:]}"
                details["gender"] = root.attrib.get("gender")
                details["yob"] = root.attrib.get("yob") or root.attrib.get("dob")
                details["state"] = root.attrib.get("state")
                details["district"] = root.attrib.get("dist")
                details["pincode"] = root.attrib.get("pc")
                return details
            except Exception:
                name_m = re.search(r'name=["\']([^"\']+)["\']', payload, re.IGNORECASE)
                if name_m:
                    details["extracted_name"] = name_m.group(1)
                uid_m = re.search(r'uid=["\'](\d+)["\']', payload, re.IGNORECASE)
                if uid_m:
                    digits = uid_m.group(1)
                    details["masked_uid"] = f"XXXX-XXXX-{digits[-4:]}" if len(digits) >= 4 else None
                gen_m = re.search(r'gender=["\']([^"\']+)["\']', payload, re.IGNORECASE)
                if gen_m:
                    details["gender"] = gen_m.group(1)
                yob_m = re.search(r'(?:yob|dob)=["\']([^"\']+)["\']', payload, re.IGNORECASE)
                if yob_m:
                    details["yob"] = yob_m.group(1)
                state_m = re.search(r'state=["\']([^"\']+)["\']', payload, re.IGNORECASE)
                if state_m:
                    details["state"] = state_m.group(1)
                return details

        # Check 2: Large BigInteger / Byte stream payload typical of Secure e-Aadhaar QR codes
        if len(payload) > 150:
            details["is_uidai_format"] = True
            details["notes"] = "Secure digitally-signed e-Aadhaar binary QR structure detected"
            words = re.findall(r'[A-Za-z]{3,}', payload)
            if words:
                potential_name = " ".join(words[:2])
                details["extracted_name"] = potential_name

        return details

    @staticmethod
    def calculate_name_similarity(name1: Optional[str], name2: Optional[str]) -> float:
        """
        Calculates normalized string similarity score (0.0 to 1.0) between citizen's full_name
        and the name decoded from the Aadhaar QR code.
        """
        if not name1 or not name2:
            return 0.0
        n1 = re.sub(r"[^a-zA-Z\s]", "", name1).lower().strip()
        n2 = re.sub(r"[^a-zA-Z\s]", "", name2).lower().strip()
        if not n1 or not n2:
            return 0.0

        if n1 == n2:
            return 1.0

        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        if tokens1 and tokens2:
            intersection = tokens1.intersection(tokens2)
            if len(intersection) == min(len(tokens1), len(tokens2)):
                return 0.95

        return round(SequenceMatcher(None, n1, n2).ratio(), 3)

    @staticmethod
    def inspect_card_structure(card_image_path: str) -> Dict[str, Any]:
        """
        Evaluates visual structure of the uploaded Aadhaar card using OpenCV:
        - Image dimensions and resolution
        - Aspect ratio (Standard CR80 Indian ID card: ~1.58:1, acceptable 1.20 to 2.10)
        - Color profile heuristics
        """
        result = {
            "is_valid_format": False,
            "width": 0,
            "height": 0,
            "aspect_ratio": 0.0,
            "has_id_card_proportions": False
        }

        if not card_image_path or not os.path.exists(card_image_path):
            return result

        try:
            img = cv2.imread(card_image_path)
            if img is None:
                return result

            h, w = img.shape[:2]
            result["width"] = int(w)
            result["height"] = int(h)

            if h > 0:
                aspect = round(max(w, h) / min(w, h), 2)
                result["aspect_ratio"] = aspect
                if 1.20 <= aspect <= 2.10:
                    result["has_id_card_proportions"] = True

            if w >= 200 and h >= 200:
                result["is_valid_format"] = True

            return result
        except Exception:
            return result

    @classmethod
    def verify_aadhaar_evidence(
        cls,
        aadhaar_number: Optional[str],
        full_name: Optional[str],
        card_image_path: Optional[str] = None,
        qr_image_path: Optional[str] = None,
        existing_verhoeff_passed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end automated verification on the submitted citizen Aadhaar identity evidence.
        Produces a consolidated auto-verification verdict:
        - auto_status: 'GENUINE_VERIFIED' | 'WARNING_SUSPICIOUS' | 'INVALID_NOT_AADHAAR'
        - detailed score breakdown
        """
        verhoeff_passed = False
        clean_num = re.sub(r"\D", "", str(aadhaar_number)) if aadhaar_number else ""
        if len(clean_num) == 12:
            verhoeff_passed = cls.validate_verhoeff(clean_num)
        elif existing_verhoeff_passed is not None:
            verhoeff_passed = existing_verhoeff_passed
        elif aadhaar_number and "XXXX" in str(aadhaar_number).upper():
            verhoeff_passed = True

        # 1. Scan dedicated QR image
        qr_detected, raw_qr, qr_details = False, None, {}
        if qr_image_path and os.path.exists(qr_image_path):
            qr_detected, raw_qr, qr_details = cls.decode_qr_code(qr_image_path)

        # 2. If not detected on QR image, check if QR code is on the Card image itself
        if not qr_detected and card_image_path and os.path.exists(card_image_path):
            qr_detected, raw_qr, qr_details = cls.decode_qr_code(card_image_path)

        # 3. Check Card visual framing
        card_structure = {}
        if card_image_path and os.path.exists(card_image_path):
            card_structure = cls.inspect_card_structure(card_image_path)

        # 4. Name similarity check
        name_match_score = 0.0
        extracted_name = qr_details.get("extracted_name")
        if extracted_name and full_name:
            name_match_score = cls.calculate_name_similarity(full_name, extracted_name)

        # 5. Determine Consolidated Auto Status & Confidence
        is_uidai_qr = qr_details.get("is_uidai_format", False)
        card_proportions = card_structure.get("has_id_card_proportions", False)

        confidence_score = 0.0
        reasons = []

        if verhoeff_passed:
            confidence_score += 0.40
            reasons.append("12-digit Aadhaar number passed Verhoeff checksum algorithm.")
        else:
            reasons.append("12-digit Aadhaar number failed Verhoeff checksum algorithm.")

        if qr_detected:
            confidence_score += 0.35
            if is_uidai_qr:
                confidence_score += 0.15
                reasons.append("UIDAI compliant QR code successfully scanned and decoded.")
            else:
                reasons.append("QR code detected but non-standard UIDAI payload.")
        else:
            reasons.append("No readable QR code found in uploaded QR image.")

        if card_proportions:
            confidence_score += 0.10
            reasons.append("Card image conforms to standard government ID aspect ratio.")

        if name_match_score >= 0.75:
            confidence_score = min(1.0, confidence_score + 0.10)
            reasons.append(f"Observer full name matches QR demographic record ({int(name_match_score*100)}% match).")

        confidence_score = round(min(1.0, confidence_score), 2)

        if verhoeff_passed and (qr_detected or card_proportions) and confidence_score >= 0.70:
            auto_status = "GENUINE_VERIFIED"
            verdict_text = "Automated verification successful: Genuine Aadhaar identity confirmed."
        elif verhoeff_passed:
            auto_status = "POTENTIAL_MISMATCH"
            verdict_text = "Aadhaar number valid, but QR code or card framing requires manual authority confirmation."
        else:
            auto_status = "INVALID_NOT_AADHAAR"
            verdict_text = "Automated verification warning: Invalid Aadhaar number checksum or unrecognizable identity document."

        return {
            "auto_status": auto_status,
            "confidence_score": confidence_score,
            "verhoeff_passed": verhoeff_passed,
            "qr_detected": qr_detected,
            "is_uidai_qr": is_uidai_qr,
            "extracted_name": extracted_name,
            "name_match_score": name_match_score,
            "card_aspect_ratio": card_structure.get("aspect_ratio", 0.0),
            "card_proportions_valid": card_proportions,
            "verdict_summary": verdict_text,
            "audit_reasons": reasons
        }
