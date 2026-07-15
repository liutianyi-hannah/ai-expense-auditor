import base64
import json
import os
from copy import deepcopy
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from prompt import EXPENSE_EXTRACTION_PROMPT


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CONFIDENCE_THRESHOLD = 75
MEAL_LIMIT = 80.00


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_bool(value) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "yes",
            "1",
            "y",
        }

    return bool(value)


def convert_image_to_data_url(
    file_bytes: bytes,
    mime_type: str,
) -> str:
    encoded_image = base64.b64encode(
        file_bytes
    ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded_image}"


def clean_json_response(response_text: str) -> str:
    cleaned = response_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


def analyze_receipt_with_ai(
    file_bytes: bytes,
    mime_type: str,
    employee_note: str,
) -> dict:
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY was not found. "
            "Please check your .env file."
        )

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    image_data_url = convert_image_to_data_url(
        file_bytes=file_bytes,
        mime_type=mime_type,
    )

    business_purpose = (
        employee_note.strip()
        if employee_note.strip()
        else "Not provided"
    )

    full_prompt = f"""
{EXPENSE_EXTRACTION_PROMPT}

Employee business purpose:
{business_purpose}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": full_prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                    },
                ],
            }
        ],
    )

    cleaned_response = clean_json_response(
        response.output_text
    )

    result = json.loads(
        cleaned_response
    )

    result["vendor"] = str(
        result.get("vendor", "Unknown")
    )

    result["amount"] = safe_float(
        result.get("amount", 0)
    )

    result["currency"] = str(
        result.get("currency", "Unknown")
    )

    result["date"] = str(
        result.get("date", "Unknown")
    )

    result["category"] = str(
        result.get("category", "Unknown")
    )

    result["contains_alcohol"] = safe_bool(
        result.get("contains_alcohol", False)
    )

    result["confidence"] = max(
        0,
        min(
            100,
            safe_int(
                result.get("confidence", 0)
            ),
        ),
    )

    result["extraction_notes"] = str(
        result.get(
            "extraction_notes",
            "No extraction notes provided.",
        )
    )

    result["employee_note"] = business_purpose

    return result


def apply_expense_rules(
    data: dict,
    ignore_confidence: bool = False,
) -> dict:
    amount = safe_float(
        data.get("amount", 0)
    )

    confidence = safe_int(
        data.get("confidence", 0)
    )

    category = str(
        data.get("category", "Unknown")
    ).strip().lower()

    vendor = str(
        data.get("vendor", "Unknown")
    ).strip()

    contains_alcohol = safe_bool(
        data.get("contains_alcohol", False)
    )

    if (
        not ignore_confidence
        and confidence < CONFIDENCE_THRESHOLD
    ):
        return {
            "decision": "Manual Review",
            "reason": (
                "The receipt could not be processed with "
                "enough confidence and requires Accounting review."
            ),
            "rule_triggered": "LOW_CONFIDENCE",
        }

    if vendor.lower() == "unknown" or amount <= 0:
        return {
            "decision": "Manual Review",
            "reason": (
                "Important receipt information could not "
                "be identified."
            ),
            "rule_triggered": "MISSING_INFORMATION",
        }

    if contains_alcohol or category == "alcohol":
        return {
            "decision": "Reject",
            "reason": (
                "This expense includes alcohol, "
                "which is not reimbursable."
            ),
            "rule_triggered": "ALCOHOL_NOT_ALLOWED",
        }

    if category == "meal":
        if amount > MEAL_LIMIT:
            return {
                "decision": "Reject",
                "reason": (
                    f"The meal expense of ${amount:.2f} "
                    f"exceeds the ${MEAL_LIMIT:.2f} limit."
                ),
                "rule_triggered": "MEAL_LIMIT_EXCEEDED",
            }

        return {
            "decision": "Approve",
            "reason": (
                f"The meal expense of ${amount:.2f} "
                f"is within the ${MEAL_LIMIT:.2f} limit."
            ),
            "rule_triggered": "MEAL_WITHIN_LIMIT",
        }

    if category == "transportation":
        return {
            "decision": "Approve",
            "reason": (
                "Business transportation is reimbursable "
                "under company policy."
            ),
            "rule_triggered": "TRANSPORTATION_ALLOWED",
        }

    if category == "hotel":
        return {
            "decision": "Approve",
            "reason": (
                "Hotel expenses are reimbursable "
                "under company policy."
            ),
            "rule_triggered": "HOTEL_ALLOWED",
        }

    return {
        "decision": "Manual Review",
        "reason": (
            "This expense category does not have "
            "an automatic approval rule."
        ),
        "rule_triggered": "CATEGORY_REVIEW_REQUIRED",
    }


def calculate_risk(result: dict) -> dict:
    amount = safe_float(
        result.get("amount", 0)
    )

    confidence = safe_int(
        result.get("confidence", 0)
    )

    category = str(
        result.get("category", "Unknown")
    ).strip().lower()

    contains_alcohol = safe_bool(
        result.get("contains_alcohol", False)
    )

    risk_score = 0
    risk_reasons = []

    if confidence < 60:
        risk_score += 50
        risk_reasons.append(
            "Very low AI confidence"
        )

    elif confidence < CONFIDENCE_THRESHOLD:
        risk_score += 30
        risk_reasons.append(
            "Confidence below automatic threshold"
        )

    if amount > 500:
        risk_score += 40
        risk_reasons.append(
            "High-value expense"
        )

    elif amount > 200:
        risk_score += 20
        risk_reasons.append(
            "Moderately high expense"
        )

    if contains_alcohol or category == "alcohol":
        risk_score += 40
        risk_reasons.append(
            "Alcohol detected"
        )

    if category in {"other", "unknown"}:
        risk_score += 20
        risk_reasons.append(
            "Unrecognized category"
        )

    if risk_score >= 50:
        risk_level = "High"

    elif risk_score >= 20:
        risk_level = "Medium"

    else:
        risk_level = "Low"

    if not risk_reasons:
        risk_reasons.append(
            "No significant risk indicators"
        )

    return {
        "risk_score": min(
            risk_score,
            100,
        ),
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }


def build_final_result(
    extracted_data: dict,
    ignore_confidence: bool = False,
) -> dict:
    final_result = deepcopy(
        extracted_data
    )

    final_result.update(
        apply_expense_rules(
            final_result,
            ignore_confidence=ignore_confidence,
        )
    )

    final_result.update(
        calculate_risk(
            final_result
        )
    )

    return final_result


def create_history_item(
    result: dict,
    event_type: str,
) -> dict:
    history_item = deepcopy(
        result
    )

    history_item["event_type"] = event_type

    history_item["processed_at"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return history_item