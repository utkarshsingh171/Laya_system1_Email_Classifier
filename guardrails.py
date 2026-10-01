import re

from langgraph.types import interrupt


# =========================================================
# BEFORE LLM GUARD
# =========================================================

def before_llm(text: str) -> str:

    if not text:
        return ""

    text = str(text)

    # -----------------------------------------------------
    # Remove extremely large whitespace
    # -----------------------------------------------------

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ \t]{3,}",
        " ",
        text
    )

    # -----------------------------------------------------
    # Redact common sensitive information
    # -----------------------------------------------------

    # API keys / secret-like tokens
    text = re.sub(
        r"(?i)(api[_ -]?key|secret|access[_ -]?token)"
        r"\s*[:=]\s*[A-Za-z0-9_\-\.]+",
        r"\1: [REDACTED]",
        text
    )

    # Credit/debit card-like numbers
    text = re.sub(
        r"\b(?:\d[ -]*?){13,19}\b",
        "[REDACTED CARD NUMBER]",
        text
    )

    # Indian phone numbers
    text = re.sub(
        r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
        "[REDACTED PHONE]",
        text
    )

    return text.strip()


# =========================================================
# HUMAN APPROVAL
# =========================================================

def human_approval(state):

    approval = interrupt(
        {
            "type": "human_approval",

            "subject": state.get(
                "subject",
                ""
            ),

            "sender": state.get(
                "sender",
                ""
            ),

            "reply": state.get(
                "generated_reply",
                ""
            )
        }
    )

    approved = False

    if isinstance(approval, dict):

        approved = (
            approval.get("approved") is True
        )

    return {
        "human_approved": approved
    }


# =========================================================
# ROUTE AFTER HUMAN
# =========================================================

def route_after_human(state):

    if state.get("human_approved") is True:
        return "approved"

    return "rejected"