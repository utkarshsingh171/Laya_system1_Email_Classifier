import requests
from typing import TypedDict, Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from guardrails import (
    before_llm,
    human_approval,
    route_after_human
)

load_dotenv()

# =========================================================
# LAYA SYSTEM 1 CONFIGURATION
# =========================================================

LAYA_URL = "http://localhost:8000/v1/systemone"

# 4 Sub-Categories Schema for Laya Engine
LAYA_CLASSIFICATION_QUESTIONS = {
    "email_category": {
        "type": "choice",
        "instructions": "Which specific sub-category does this email belong to?",
        "criteria": {
            "action_required": "Personal emails, client queries, job offers requiring direct reply, human conversations, action requests",
            "informational": "Receipts, status updates, order confirmations, OTPs, verification emails, system notifications",
            "promotions_newsletters": "Marketing emails, advertisements, newsletters, automated job alerts, promotional digests",
            "spam_junk": "Unsolicited sales pitches, cold outreach, bulk junk, suspicious or spam emails"
        }
    }
}

# =========================================================
# GRAPH STATE
# =========================================================

class EmailState(TypedDict):
    email_id: str
    thread_id: str
    sender: str
    subject: str
    review: str  # Sanitized body
    category: Literal[
        "action_required",
        "informational",
        "promotions_newsletters",
        "spam_junk"
    ]
    reply_needed: bool
    generated_reply: str
    message: str
    human_approved: bool

# =========================================================
# CLASSIFY EMAIL USING LAYA SYSTEM 1
# =========================================================

def classify_email(state: EmailState):
    safe_email = before_llm(state["review"])

    # Prepare document payload for Laya
    email_doc = f"Sender: {state['sender']}\nSubject: {state['subject']}\nBody: {safe_email}"

    payload = {
        "state": {
            "documents": email_doc
        },
        "questions": LAYA_CLASSIFICATION_QUESTIONS
    }

    category = "informational"  # Fallback

    try:
        response = requests.post(LAYA_URL, json=payload, timeout=5)
        if response.status_code == 200:
            res = response.json()
            category = res.get("answers", {}).get("email_category", {}).get("choice", "informational")
    except Exception as e:
        print(f"Laya System 1 request failed: {e}")

    return {
        "category": category,
        "review": safe_email
    }

# =========================================================
# ROUTER
# =========================================================

def router(state: EmailState):
    if state["category"] == "action_required":
        return "generate_reply"
    return "no_reply_needed"

# =========================================================
# NO REPLY NEEDED
# =========================================================

def no_reply_needed(state: EmailState):
    cat = state.get("category", "informational")
    messages = {
        "informational": "Informational email - No reply required.",
        "promotions_newsletters": "Promotional / Newsletter - Categorized and skipped.",
        "spam_junk": "Spam / Junk email - Categorized and skipped."
    }
    return {
        "reply_needed": False,
        "generated_reply": "",
        "message": messages.get(cat, "No reply needed.")
    }

# =========================================================
# GENERATE REPLY
# =========================================================

def generate_reply(state: EmailState):
    safe_email = before_llm(state["review"])

    # Fast System 1 question schema for draft reply generation
    reply_payload = {
        "state": {
            "documents": f"From: {state['sender']}\nSubject: {state['subject']}\nEmail: {safe_email}"
        },
        "questions": {
            "draft_reply": {
                "type": "text",
                "instructions": "Write a short, natural, direct, and professional reply acknowledging the sender. Do not mention AI or make false promises."
            }
        }
    }

    generated_text = "Thank you for reaching out. I have received your email and will get back to you shortly."

    try:
        response = requests.post(LAYA_URL, json=reply_payload, timeout=8)
        if response.status_code == 200:
            res = response.json()
            reply = res.get("answers", {}).get("draft_reply", {}).get("text", "").strip()
            if reply:
                generated_text = reply
    except Exception as e:
        print(f"Laya System 1 generation error: {e}")

    return {
        "reply_needed": True,
        "generated_reply": generated_text,
        "message": "Action required - Reply draft generated."
    }

# =========================================================
# BUILD LANGGRAPH WORKFLOW
# =========================================================

graph = StateGraph(EmailState)

graph.add_node("classify_email", classify_email)
graph.add_node("generate_reply", generate_reply)
graph.add_node("no_reply_needed", no_reply_needed)
graph.add_node("human_approval", human_approval)

graph.add_edge(START, "classify_email")
graph.add_conditional_edges("classify_email", router)
graph.add_edge("generate_reply", "human_approval")
graph.add_edge("no_reply_needed", END)

graph.add_conditional_edges(
    "human_approval",
    route_after_human,
    {
        "approved": END,
        "rejected": END
    }
)

memory = MemorySaver()
workflow = graph.compile(checkpointer=memory)