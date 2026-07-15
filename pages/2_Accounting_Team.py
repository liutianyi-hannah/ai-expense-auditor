import io
import json
from datetime import datetime

import streamlit as st
from PIL import Image

from expense_logic import (
    build_final_result,
    create_history_item,
    safe_float,
    safe_int,
)


st.set_page_config(
    page_title="Accounting Team Dashboard",
    page_icon="📊",
    layout="wide",
)


if "submissions" not in st.session_state:
    st.session_state.submissions = []

if "history" not in st.session_state:
    st.session_state.history = []


st.title(
    "📊 Accounting Team Dashboard"
)

st.write(
    "Monitor expense submissions and review "
    "cases that require manual processing."
)


submissions = st.session_state.submissions


total_submitted = len(
    submissions
)

ai_approved = sum(
    1
    for item in submissions
    if item.get("ai_decision") == "Approve"
)

ai_rejected = sum(
    1
    for item in submissions
    if item.get("ai_decision") == "Reject"
)

ai_completed = (
    ai_approved
    + ai_rejected
)

pending_manual_review = [
    item
    for item in submissions
    if item.get("status")
    == "Pending Manual Review"
]


metric1, metric2, metric3, metric4, metric5 = (
    st.columns(5)
)

with metric1:
    st.metric(
        "Expenses Submitted",
        total_submitted,
    )

with metric2:
    st.metric(
        "AI Completed",
        ai_completed,
    )

with metric3:
    st.metric(
        "AI Approved",
        ai_approved,
    )

with metric4:
    st.metric(
        "AI Rejected",
        ai_rejected,
    )

with metric5:
    st.metric(
        "Manual Review",
        len(
            pending_manual_review
        ),
    )


st.divider()

st.subheader(
    "⚠️ Expenses Requiring Manual Review"
)


if not pending_manual_review:
    st.success(
        "There are currently no expenses "
        "waiting for manual review."
    )

else:
    st.caption(
        f"{len(pending_manual_review)} "
        "expense submission(s) require review."
    )

    for submission in pending_manual_review:
        submission_id = submission[
            "submission_id"
        ]

        result = submission[
            "result"
        ]

        vendor = result.get(
            "vendor",
            "Unknown",
        )

        amount = safe_float(
            result.get(
                "amount",
                0,
            )
        )

        currency = result.get(
            "currency",
            "Unknown",
        )

        submitted_at = submission.get(
            "submitted_at",
            "Unknown",
        )

        expander_title = (
            f"{submission_id} | "
            f"{vendor} | "
            f"{amount:.2f} {currency} | "
            f"{submitted_at}"
        )

        with st.expander(
            expander_title
        ):
            receipt_column, details_column = (
                st.columns(
                    [1, 2]
                )
            )

            with receipt_column:
                st.markdown(
                    "#### Receipt"
                )

                try:
                    receipt_image = Image.open(
                        io.BytesIO(
                            submission[
                                "receipt_bytes"
                            ]
                        )
                    )

                    st.image(
                        receipt_image,
                        caption=submission.get(
                            "receipt_name",
                            "Receipt",
                        ),
                        width=300,
                    )

                except Exception as error:
                    st.error(
                        "Unable to display "
                        f"receipt: {error}"
                    )

            with details_column:
                st.markdown(
                    "#### AI Extraction"
                )

                detail1, detail2 = (
                    st.columns(2)
                )

                with detail1:
                    st.write(
                        "**Vendor:** "
                        f"{result.get('vendor', 'Unknown')}"
                    )

                    st.write(
                        "**Amount:** "
                        f"{safe_float(result.get('amount', 0)):.2f} "
                        f"{result.get('currency', 'Unknown')}"
                    )

                    st.write(
                        "**Date:** "
                        f"{result.get('date', 'Unknown')}"
                    )

                with detail2:
                    st.write(
                        "**Category:** "
                        f"{result.get('category', 'Unknown')}"
                    )

                    st.write(
                        "**Alcohol detected:** "
                        f"{'Yes' if result.get('contains_alcohol') else 'No'}"
                    )

                    st.write(
                        "**AI confidence:** "
                        f"{safe_int(result.get('confidence', 0))}%"
                    )

                st.write(
                    "**Business purpose:** "
                    f"{result.get('employee_note', 'Not provided')}"
                )

                st.warning(
                    result.get(
                        "reason",
                        "Manual review required.",
                    )
                )

                if submission.get(
                    "employee_requested_review",
                    False,
                ):
                    st.info(
                        "🙋 This manual review was requested by the employee."
                    )

                    st.write(
                        "**Employee review request reason:**"
                    )

                    st.write(
                        submission.get(
                            "employee_review_note",
                            "No reason was provided.",
                        )
                    )

                    st.write(
                        "**Original AI decision:** "
                        f"{submission.get('original_ai_decision', 'Unknown')}"
                    )

                    st.write(
                        "**Original AI reason:** "
                        f"{submission.get('original_ai_reason', 'Unknown')}"
                    )

                    st.write(
                        "**Review requested at:** "
                        f"{submission.get('manual_review_requested_at', 'Unknown')}"
                    )

            st.divider()

            st.markdown(
                "#### Human Review and Correction"
            )

            category_options = [
                "Meal",
                "Alcohol",
                "Transportation",
                "Hotel",
                "Other",
                "Unknown",
            ]

            currency_options = [
                "CAD",
                "USD",
                "Unknown",
            ]

            existing_category = result.get(
                "category",
                "Unknown",
            )

            if existing_category not in category_options:
                existing_category = "Unknown"

            existing_currency = result.get(
                "currency",
                "Unknown",
            )

            if existing_currency not in currency_options:
                existing_currency = "Unknown"

            form_key = (
                "manual_review_form_"
                f"{submission_id}"
            )

            with st.form(
                form_key
            ):
                form_col1, form_col2 = (
                    st.columns(2)
                )

                with form_col1:
                    corrected_vendor = st.text_input(
                        "Vendor",
                        value=str(
                            result.get(
                                "vendor",
                                "Unknown",
                            )
                        ),
                        key=(
                            "vendor_"
                            f"{submission_id}"
                        ),
                    )

                    corrected_amount = st.number_input(
                        "Amount",
                        min_value=0.0,
                        value=safe_float(
                            result.get(
                                "amount",
                                0,
                            )
                        ),
                        step=0.01,
                        format="%.2f",
                        key=(
                            "amount_"
                            f"{submission_id}"
                        ),
                    )

                    corrected_currency = st.selectbox(
                        "Currency",
                        currency_options,
                        index=currency_options.index(
                            existing_currency
                        ),
                        key=(
                            "currency_"
                            f"{submission_id}"
                        ),
                    )

                    corrected_date = st.text_input(
                        "Date",
                        value=str(
                            result.get(
                                "date",
                                "Unknown",
                            )
                        ),
                        key=(
                            "date_"
                            f"{submission_id}"
                        ),
                    )

                with form_col2:
                    corrected_category = st.selectbox(
                        "Category",
                        category_options,
                        index=category_options.index(
                            existing_category
                        ),
                        key=(
                            "category_"
                            f"{submission_id}"
                        ),
                    )

                    corrected_alcohol = st.checkbox(
                        "Receipt contains alcohol",
                        value=bool(
                            result.get(
                                "contains_alcohol",
                                False,
                            )
                        ),
                        key=(
                            "alcohol_"
                            f"{submission_id}"
                        ),
                    )

                    corrected_business_note = st.text_area(
                        "Business purpose",
                        value=str(
                            result.get(
                                "employee_note",
                                "Not provided",
                            )
                        ),
                        key=(
                            "business_note_"
                            f"{submission_id}"
                        ),
                    )

                reviewer_note = st.text_area(
                    "Accounting reviewer note",
                    placeholder=(
                        "Example: Receipt amount and "
                        "category were manually verified."
                    ),
                    key=(
                        "reviewer_note_"
                        f"{submission_id}"
                    ),
                )

                decision_method = st.radio(
                    "Final decision",
                    [
                        "Use company policy rules",
                        "Approve",
                        "Reject",
                    ],
                    horizontal=True,
                    key=(
                        "decision_"
                        f"{submission_id}"
                    ),
                )

                submit_review = (
                    st.form_submit_button(
                        "Complete Human Review",
                        type="primary",
                        use_container_width=True,
                    )
                )

            if submit_review:
                corrected_data = {
                    "vendor": (
                        corrected_vendor.strip()
                        or "Unknown"
                    ),
                    "amount": corrected_amount,
                    "currency": corrected_currency,
                    "date": (
                        corrected_date.strip()
                        or "Unknown"
                    ),
                    "category": corrected_category,
                    "contains_alcohol": (
                        corrected_alcohol
                    ),
                    "confidence": result.get(
                        "confidence",
                        0,
                    ),
                    "employee_note": (
                        corrected_business_note.strip()
                        or "Not provided"
                    ),
                    "extraction_notes": (
                        "Receipt information was "
                        "reviewed by Accounting."
                    ),
                    "human_reviewed": True,
                    "reviewer_note": (
                        reviewer_note.strip()
                        or "No reviewer note provided"
                    ),
                }

                corrected_result = (
                    build_final_result(
                        corrected_data,
                        ignore_confidence=True,
                    )
                )

                if decision_method == "Approve":
                    corrected_result[
                        "decision"
                    ] = "Approve"

                    corrected_result[
                        "reason"
                    ] = (
                        "The expense was manually "
                        "approved by Accounting."
                    )

                    corrected_result[
                        "rule_triggered"
                    ] = "HUMAN_APPROVAL"

                elif decision_method == "Reject":
                    corrected_result[
                        "decision"
                    ] = "Reject"

                    corrected_result[
                        "reason"
                    ] = (
                        "The expense was manually "
                        "rejected by Accounting."
                    )

                    corrected_result[
                        "rule_triggered"
                    ] = "HUMAN_REJECTION"

                corrected_result[
                    "human_reviewed"
                ] = True

                corrected_result[
                    "reviewer_note"
                ] = (
                    reviewer_note.strip()
                    or "No reviewer note provided"
                )

                submission["result"] = (
                    corrected_result
                )

                submission["status"] = (
                    "Human Review Completed"
                )

                submission["reviewed_at"] = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                history_data = {
                    **corrected_result,
                    "submission_id": submission_id,
                }

                history_item = (
                    create_history_item(
                        history_data,
                        event_type=(
                            "Accounting Human Review"
                        ),
                    )
                )

                st.session_state.history.append(
                    history_item
                )

                st.rerun()


st.divider()

st.subheader(
    "📋 Approval History"
)


history_records = (
    st.session_state.history
)


if history_records:
    history_json = json.dumps(
        history_records,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    st.download_button(
        label="⬇️ Download Approval History",
        data=history_json,
        file_name=(
            "expense_approval_history.json"
        ),
        mime="application/json",
        use_container_width=True,
    )


if not history_records:
    st.caption(
        "No expense approval history "
        "is available."
    )

else:
    for index, history_item in enumerate(
        reversed(
            history_records
        ),
        start=1,
    ):
        submission_id = history_item.get(
            "submission_id",
            "Unknown",
        )

        vendor = history_item.get(
            "vendor",
            "Unknown",
        )

        decision = history_item.get(
            "decision",
            "Manual Review",
        )

        event_type = history_item.get(
            "event_type",
            "Unknown Event",
        )

        processed_at = history_item.get(
            "processed_at",
            "Unknown Time",
        )

        history_title = (
            f"{index}. {submission_id} | "
            f"{vendor} | "
            f"{decision} | "
            f"{event_type}"
        )

        with st.expander(
            history_title
        ):
            history_col1, history_col2 = (
                st.columns(2)
            )

            with history_col1:
                st.write(
                    "**Processed at:** "
                    f"{processed_at}"
                )

                st.write(
                    "**Amount:** "
                    f"{safe_float(history_item.get('amount', 0)):.2f} "
                    f"{history_item.get('currency', 'Unknown')}"
                )

                st.write(
                    "**Category:** "
                    f"{history_item.get('category', 'Unknown')}"
                )

            with history_col2:
                st.write(
                    "**Decision:** "
                    f"{history_item.get('decision', 'Unknown')}"
                )

                st.write(
                    "**Rule:** "
                    f"{history_item.get('rule_triggered', 'Unknown')}"
                )

                st.write(
                    "**Reviewer note:** "
                    f"{history_item.get('reviewer_note', 'Not reviewed')}"
                )
                if history_item.get("employee_review_note"):
                    st.write(
                        "**Employee manual review reason:** "
                        f"{history_item.get('employee_review_note')}"
                    )

            st.write(
                "**Decision reason:** "
                f"{history_item.get('reason', 'Unknown')}"
            )

            with st.expander(
                "View raw record"
            ):
                st.json(
                    history_item
                )