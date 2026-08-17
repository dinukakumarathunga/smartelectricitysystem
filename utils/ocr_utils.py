# ============================================================
#  utils/ocr_utils.py
#  Extracts units_consumed / bill_amount_lkr / billing_period
#  from an uploaded bill photo or SMS screenshot.
#
#  This is a server-side port of the same best-effort approach
#  the frontend prototype used with Tesseract.js (see the
#  extractFromImage/parseBillText functions that used to live in
#  app-data.js) — regex over raw OCR text, not a trained field
#  extractor. Real bill layouts vary a lot (see the CEB
#  net-metering sample this project was tested against), so this
#  is a starting point the user always reviews/edits on
#  06_upload_confirm.html, never something saved unconfirmed.
# ============================================================

import re

import pytesseract
from flask import current_app
from PIL import Image


def configure_tesseract():
    """Point pytesseract at a specific binary if TESSERACT_CMD is set (e.g. on Windows)."""
    cmd = current_app.config.get('TESSERACT_CMD')
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def extract_text_with_confidence(image_path):
    """
    Returns (raw_text, average_word_confidence). average_word_confidence
    is pytesseract's own per-word confidence score (0-100), averaged
    across recognised words — used to decide High/Medium/Low below.
    """
    configure_tesseract()
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = [w for w in data.get('text', []) if w.strip()]
    text = ' '.join(words)

    confidences = [int(c) for c in data.get('conf', []) if str(c).lstrip('-').isdigit() and int(c) >= 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return text, avg_confidence


def _safe_float(raw_text):
    """Converts OCR-matched text to a number, or None if it isn't
    actually a usable number (e.g. just a stray comma)."""
    if not raw_text:
        return None
    cleaned = raw_text.replace(',', '').strip()
    if not cleaned or not any(ch.isdigit() for ch in cleaned):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_bill_text(text):
    """
    Same regex patterns as the old client-side parseBillText():
      - "<number> kWh"                         → units_consumed
      - "LKR <number>" or "Rs <number>"         → bill_amount_lkr
      - "<date> - <date>" / "<date> to <date>"  → billing_period
    """
    kwh_match = re.search(r'([\d,]+(?:\.\d+)?)\s*k\s*wh', text, re.IGNORECASE)
    lkr_match = re.search(r'(?:LKR|Rs\.?)\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
    period_match = re.search(
        r'(\d{1,2}\s+\w+\s+\d{4})\s*[-–to]+\s*(\d{1,2}\s+\w+\s+\d{4})', text, re.IGNORECASE
    )

    return {
        'units_consumed':  _safe_float(kwh_match.group(1)) if kwh_match else None,
        'bill_amount_lkr': _safe_float(lkr_match.group(1)) if lkr_match else None,
        'billing_period':  f'{period_match.group(1)} - {period_match.group(2)}' if period_match else None,
    }


def determine_confidence(text, avg_word_confidence, extracted, threshold):
    if not text.strip():
        return 'Low'
    if extracted['units_consumed'] is None:
        # Couldn't find the one field that actually matters — low
        # confidence regardless of how clean the OCR text otherwise was.
        return 'Low'
    return 'High' if avg_word_confidence >= threshold else 'Medium'


def extract_bill_data(image_path):
    """
    Top-level entry point used by routes/bill_routes.py. Never
    raises — OCR failures degrade to an empty result with 'Low'
    confidence so the user can fill in the fields by hand on the
    confirm screen rather than the upload failing outright.
    """
    empty_result = {
        'extracted': {'units_consumed': None, 'bill_amount_lkr': None, 'billing_period': None},
        'ocr_confidence': 'Low',
    }

    try:
        text, avg_confidence = extract_text_with_confidence(image_path)
    except Exception as exc:
        current_app.logger.warning(f'OCR failed for {image_path}: {exc}')
        return empty_result

    extracted = parse_bill_text(text)
    threshold = current_app.config.get('OCR_LOW_CONFIDENCE_THRESHOLD', 60)
    confidence = determine_confidence(text, avg_confidence, extracted, threshold)

    return {'extracted': extracted, 'ocr_confidence': confidence}
