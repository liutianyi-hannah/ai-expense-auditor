import html
import io
import json
from datetime import datetime
from uuid import uuid4

import streamlit as st
from PIL import Image

from expense_logic import (
    CONFIDENCE_THRESHOLD,
    MEAL_LIMIT,
    analyze_receipt_with_ai,
    build_final_result,
    create_history_item,
    safe_float,
    safe_int,
)


st.set_page_config(
    page_title="Employee Expense Portal",
    page_icon="🧾",
    layout="centered",
)


st.markdown(
    """
    <style>
    .result-card {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px;
        min-height: 125px;
        background-color: #ffffff;
        margin-bottom: 8px;
    }

    .result-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin-bottom: 10px;
    }

    .result-value {
        font-size: 1.45rem;
        font-weight: 600;
        line-height: 1.3;
        overflow-wrap: anywhere;
        word-break: break-word;
        white-space: normal;
    }

    .result-reference {
        font-size: 1.25rem;
        font-weight: 600;
        line-height: 1.3;
        overflow-wrap: anywhere;
        word-break: break-word;
        white-space: normal;
    }

    .status-description {
        font-size: 1rem;
        line-height: 1.6;
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "submissions" not in st.session_state:
    st.session_state.submissions = []

if "history" not in st.session_state:
    st.session_state.history = []

if "last_submission_id" not in st.session_state:
    st.session_state.last_submission_id = None


st.title("🧾 Employee Expense Portal")

st.write(
    "Upload your receipt and submit your expense "
    "for reimbursement."
)


with st.expander("View reimbursement policy"):
    st.markdown(
        f"""
        - Meals of **${MEAL_LIMIT:.2f} CAD or less**
          are reimbursable.
        - Meals above **${MEAL_LIMIT:.2f} CAD**
          are not reimbursable.
        - Alcohol is not reimbursable.
        - Business transportation is reimbursable.
        - Hotel expenses are reimbursable.
        - Receipts that cannot be processed confidently
          are sent to Accounting for manual review.
        """
    )


employee_note = st.text_area(
    "Business purpose",
    placeholder=(
        "Example: Client lunch following "
        "the project kickoff meeting"
    ),
)


uploaded_file = st.file_uploader(
    "Upload your receipt",
    type=[
        "jpg",
        "jpeg",
        "png",
    ],
)


if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    mime_type = (
        uploaded_file.type
        or "image/jpeg"
    )

    try:
        receipt_image = Image.open(
            io.BytesIO(
                file_bytes
            )
        )

        st.subheader(
            "Receipt Preview"
        )

        st.image(
            receipt_image,
            caption=uploaded_file.name,
            width=280,
        )

    except Exception as error:
        st.error(
            f"Unable to open the image: {error}"
        )
        st.stop()

    if st.button(
        "Submit Expense",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner(
                "Reviewing your receipt..."
            ):
                extracted_result = (
                    analyze_receipt_with_ai(
                        file_bytes=file_bytes,
                        mime_type=mime_type,
                        employee_note=employee_note,
                    )
                )

                final_result = (
                    build_final_result(
                        extracted_result
                    )
                )

            submission_id = (
                uuid4()
                .hex[:8]
                .upper()
            )

            ai_decision = (
                final_result.get(
                    "decision",
                    "Manual Review",
                )
            )

            if ai_decision == "Manual Review":
                submission_status = (
                    "Pending Manual Review"
                )

            else:
                submission_status = (
                    "AI Completed"
                )

            submission = {
                "submission_id": submission_id,
                "submitted_at": (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
                "receipt_name": uploaded_file.name,
                "receipt_mime": mime_type,
                "receipt_bytes": file_bytes,
                "status": submission_status,
                "ai_decision": ai_decision,
                "ai_confidence": (
                    final_result.get(
                        "confidence",
                        0,
                    )
                ),
                "employee_requested_review": False,
                "result": final_result,
            }

            st.session_state.submissions.append(
                submission
            )

            st.session_state.last_submission_id = (
                submission_id
            )

            history_data = {
                **final_result,
                "submission_id": submission_id,
            }

            history_item = (
                create_history_item(
                    history_data,
                    event_type="Employee Submission",
                )
            )

            st.session_state.history.append(
                history_item
            )

            st.success(
                "Expense submitted successfully."
            )

        except json.JSONDecodeError:
            st.error(
                "The receipt could not be analyzed. "
                "Please try again."
            )

        except Exception as error:
            st.error(
                f"Submission failed: {error}"
            )


if st.session_state.last_submission_id:
    latest_submission = next(
        (
            item
            for item in st.session_state.submissions
            if item["submission_id"]
            == st.session_state.last_submission_id
        ),
        None,
    )

    if latest_submission:
        result = latest_submission["result"]

        st.divider()

        st.subheader(
            "Reimbursement Result"
        )

        vendor_display = html.escape(
            str(
                result.get(
                    "vendor",
                    "Unknown",
                )
            )
        )

        currency_display = html.escape(
            str(
                result.get(
                    "currency",
                    "Unknown",
                )
            )
        )

        amount_display = (
            f"{safe_float(result.get('amount', 0)):.2f} "
            f"{currency_display}"
        )

        reference_display = html.escape(
            str(
                latest_submission[
                    "submission_id"
                ]
            )
        )

        col1, col2, col3 = st.columns(
            [1.5, 1, 1]
        )

        with col1:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Vendor
                    </div>
                    <div class="result-value">
                        {vendor_display}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Amount
                    </div>
                    <div class="result-value">
                        {amount_display}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-label">
                        Reference
                    </div>
                    <div class="result-reference">
                        {reference_display}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        confidence = safe_int(
            result.get(
                "confidence",
                0,
            )
        )

        decision = str(
            result.get(
                "decision",
                "Manual Review",
            )
        ).lower()

        current_status = (
            latest_submission.get(
                "status",
                "Unknown",
            )
        )

        if current_status == "Pending Manual Review":
            st.warning(
                "⚠️ Your expense has been sent "
                "for manual review."
            )

            st.markdown(
                """
                <div class="status-description">
                The Accounting Team will review your receipt
                and provide the final reimbursement decision.
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif current_status == "Human Review Completed":
            final_decision = str(
                result.get(
                    "decision",
                    "Manual Review",
                )
            ).lower()

            if final_decision == "approve":
                st.success(
                    "✅ Accounting approved your expense."
                )

            elif final_decision == "reject":
                st.error(
                    "❌ Accounting rejected your expense."
                )

            else:
                st.warning(
                    "⚠️ Accounting review has been completed."
                )

            st.markdown(
                "#### Decision explanation"
            )

            st.write(
                result.get(
                    "reason",
                    "No explanation is available.",
                )
            )

        elif (
            confidence < CONFIDENCE_THRESHOLD
            or decision == "manual review"
        ):
            st.warning(
                "⚠️ Your expense has been sent "
                "for manual review."
            )

            st.write(
                "The Accounting Team will review "
                "your submission."
            )

        elif decision == "approve":
            st.success(
                "✅ Your expense has been approved."
            )

            st.markdown(
                "#### Decision explanation"
            )

            st.write(
                result.get(
                    "reason",
                    "The expense meets company policy.",
                )
            )

        elif decision == "reject":
            st.error(
                "❌ Your expense is not eligible "
                "for reimbursement."
            )

            st.markdown(
                "#### Decision explanation"
            )

            st.write(
                result.get(
                    "reason",
                    "The expense does not meet "
                    "company policy.",
                )
            )

        else:
            st.warning(
                "⚠️ Your expense has been sent "
                "for manual review."
            )

        st.caption(
            f"Category: "
            f"{result.get('category', 'Unknown')} "
            f"· Date: "
            f"{result.get('date', 'Unknown')}"
        )

        st.divider()

        employee_requested_review = (
            latest_submission.get(
                "employee_requested_review",
                False,
            )
        )

        if current_status == "Pending Manual Review":
            st.info(
                "This expense is currently waiting "
                "for Accounting review."
            )

        elif current_status == "Human Review Completed":
            st.success(
                "The Accounting Team has completed "
                "the manual review."
            )

        elif not employee_requested_review:
            st.write(
                "Do you disagree with the automatic result "
                "or want the Accounting Team to review it?"
            )

            manual_review_note = st.text_area(
                "Reason for requesting manual review",
                placeholder=(
                    "Example: This was a client dinner and the receipt "
                    "includes both reimbursable and non-reimbursable items."
                ),
                key=(
                    "manual_review_note_"
                    f"{latest_submission['submission_id']}"
                ),
                help=(
                    "Explain why you believe the automatic decision "
                    "should be reviewed by Accounting."
                ),
            )

            request_review = st.button(
                "Request Manual Review",
                key=(
                    "request_manual_review_"
                    f"{latest_submission['submission_id']}"
                ),
                use_container_width=True,
            )

            if request_review:
                if not manual_review_note.strip():
                    st.warning(
                        "Please provide a reason before requesting manual review."
                    )

                else:
                    latest_submission[
                        "original_ai_decision"
                    ] = latest_submission.get(
                        "ai_decision",
                        result.get(
                            "decision",
                            "Unknown",
                        ),
                    )

                    latest_submission[
                        "original_ai_reason"
                    ] = result.get(
                        "reason",
                        "Unknown",
                    )

                    latest_submission["status"] = (
                        "Pending Manual Review"
                    )

                    latest_submission[
                        "employee_requested_review"
                    ] = True

                    latest_submission[
                        "employee_review_note"
                    ] = manual_review_note.strip()

                    latest_submission[
                        "manual_review_requested_at"
                    ] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    latest_submission["result"][
                        "decision"
                    ] = "Manual Review"

                    latest_submission["result"][
                        "reason"
                    ] = (
                        "The employee requested a manual review "
                        "of the automatic reimbursement result."
                    )

                    latest_submission["result"][
                        "rule_triggered"
                    ] = "EMPLOYEE_REQUESTED_REVIEW"

                    latest_submission["result"][
                        "employee_review_note"
                    ] = manual_review_note.strip()

                    history_data = {
                        **latest_submission["result"],
                        "submission_id": (
                            latest_submission[
                                "submission_id"
                            ]
                        ),
                    }

                    history_item = (
                        create_history_item(
                            history_data,
                            event_type=(
                                "Employee Requested "
                                "Manual Review"
                            ),
                        )
                    )

                    st.session_state.history.append(
                        history_item
                    )

                    st.rerun()