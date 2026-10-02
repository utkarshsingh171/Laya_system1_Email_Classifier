import requests
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, START, END


LAYA_URL = "http://localhost:8000/v1/systemone"


LAYA_CLASSIFICATION_QUESTIONS = {
    "email_category": {
        "type": "choice",
        "instructions": "Which specific sub-category does this email belong to?",
        "criteria": {
            "action_required": (
                "Personal emails, client queries, job offers requiring "
                "direct reply, human conversations, action requests"
            ),
            "informational": (
                "Receipts, status updates, order confirmations, OTPs, "
                "verification emails, system notifications"
            ),
            "promotions_newsletters": (
                "Marketing emails, advertisements, newsletters, "
                "automated job alerts, promotional digests"
            ),
            "spam_junk": (
                "Unsolicited sales pitches, cold outreach, bulk junk, "
                "suspicious or spam emails"
            )
        }
    }
}


class EmailState(TypedDict):
    email_id: str
    thread_id: str
    sender: str
    subject: str
    review: str
    category: Literal[
        "action_required",
        "informational",
        "promotions_newsletters",
        "spam_junk"
    ]


def classify_email(state: EmailState):

    email_doc = (
        f"Sender: {state['sender']}\n"
        f"Subject: {state['subject']}\n"
        f"Body: {state['review']}"
    )

    payload = {
        "state": {
            "documents": email_doc
        },
        "questions": LAYA_CLASSIFICATION_QUESTIONS
    }

    try:

        response = requests.post(
            LAYA_URL,
            json=payload,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        category = (
            result
            .get("answers", {})
            .get("email_category", {})
            .get("choice", "informational")
        )

    except Exception as e:

        print("Laya classification error:", e)

        category = "informational"

    valid_categories = {
        "action_required",
        "informational",
        "promotions_newsletters",
        "spam_junk"
    }

    if category not in valid_categories:
        category = "informational"

    print(
        f"Email classified as: {category}"
    )

    return {
        "category": category
    }


graph = StateGraph(EmailState)

graph.add_node(
    "classify_email",
    classify_email
)

graph.add_edge(
    START,
    "classify_email"
)

graph.add_edge(
    "classify_email",
    END
)

workflow = graph.compile()