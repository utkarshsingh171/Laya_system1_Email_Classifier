import base64
import os
import uuid
import html
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from langgraph.types import Command

from email_ai_agent_latest import workflow

load_dotenv()

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key")
)

# GOOGLE OAUTH
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send"
        )
    }
)

def decode_gmail_data(data):
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_email_body(message):
    payload = message.get("payload", {})

    def find_parts(part):
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")

        if mime_type == "text/plain" and body_data:
            return decode_gmail_data(body_data), "text/plain"
        if mime_type == "text/html" and body_data:
            return decode_gmail_data(body_data), "text/html"

        for child in part.get("parts", []):
            result = find_parts(child)
            if result[0]:
                return result
        return "", ""

    body, mime_type = find_parts(payload)
    if not body:
        return ""

    if mime_type == "text/html":
        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(["script", "style", "head", "noscript"]):
            tag.decompose()
        body = soup.get_text(separator="\n", strip=True)

    body = html.unescape(body).replace("\r", "")
    return "\n".join(line.strip() for line in body.splitlines() if line.strip())

# HOME - DATE SELECTION DASHBOARD
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    today = datetime.now().strftime("%Y-%m-%d")
    is_logged_in = "access_token" in request.session

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Laya System 1 - Email Categorizer</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f5f7fb; margin: 0; padding: 60px 20px; }}
            .container {{ max-width: 800px; margin: auto; }}
            .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 5px 25px rgba(0,0,0,0.08); text-align: center; }}
            h1 {{ margin-bottom: 10px; color: #0f172a; }}
            .subtitle {{ color: #64748b; line-height: 1.6; margin-bottom: 30px; }}
            .login-btn {{ display: inline-block; padding: 13px 25px; background: #2563eb; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }}
            .date-form {{ display: flex; gap: 10px; justify-content: center; margin-top: 20px; }}
            input[type="date"] {{ padding: 10px 15px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 16px; }}
            button {{ padding: 11px 22px; background: #059669; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>⚡ Laya Email Assistant</h1>
                <p class="subtitle">Review all emails for a specific date categorized into 4 sub-categories powered by System 1 Laya model.</p>
                {"<a class='login-btn' href='/login'>Login with Google</a>" if not is_logged_in else f'''
                <form class="date-form" action="/review" method="get">
                    <input type="date" name="date" value="{today}" required />
                    <button type="submit">Review Emails for Date</button>
                </form>
                '''}
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/login")
async def login(request: Request):
    return await oauth.google.authorize_redirect(
        request,
        os.getenv("REDIRECT_URI"),
        prompt="consent select_account",
        access_type="offline"
    )

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    request.session["access_token"] = token["access_token"]
    return RedirectResponse(url="/")

# REVIEW ALL EMAILS FOR SPECIFIC DATE
@app.get("/review", response_class=HTMLResponse)
async def review_emails_for_date(request: Request, date: str = None):
    if "access_token" not in request.session:
        return RedirectResponse(url="/login")

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        next_day = dt + timedelta(days=1)
        query = f"after:{dt.strftime('%Y/%m/%d')} before:{next_day.strftime('%Y/%m/%d')}"
    except ValueError:
        return HTMLResponse("<h3>Invalid date format. Please use YYYY-MM-DD.</h3>")

    creds = Credentials(token=request.session["access_token"])
    gmail = build("gmail", "v1", credentials=creds)

    # Search all emails for target date
    res = gmail.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages_list = res.get("messages", [])

    categorized = {
        "action_required": [],
        "informational": [],
        "promotions_newsletters": [],
        "spam_junk": []
    }

    if not messages_list:
        return HTMLResponse(f"""
        <div style="font-family: Arial; text-align: center; padding: 60px;">
            <h2>No emails found for {html.escape(date)}.</h2>
            <a href="/" style="color: #2563eb;">← Select Another Date</a>
        </div>
        """)

    # Classify all emails using Laya workflow
    for msg_item in messages_list:
        msg_id = msg_item["id"]
        full_msg = gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()

        headers = full_msg.get("payload", {}).get("headers", [])
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)")
        body = extract_email_body(full_msg)

        graph_thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": graph_thread_id}}

        state = {
            "email_id": msg_id,
            "thread_id": full_msg.get("threadId", msg_id),
            "sender": sender,
            "subject": subject,
            "review": body,
            "category": "informational",
            "reply_needed": False,
            "generated_reply": "",
            "message": "",
            "human_approved": False
        }

        result = workflow.invoke(state, config=config)
        category = result.get("category", "informational")

        if "__interrupt__" in result:
            snapshot = workflow.get_state(config)
            saved_state = snapshot.values
            reply = saved_state.get("generated_reply", result.get("generated_reply", ""))
        else:
            reply = result.get("generated_reply", "")

        if category not in categorized:
            category = "informational"

        categorized[category].append({
            "id": msg_id,
            "thread_id": graph_thread_id,
            "sender": sender,
            "subject": subject,
            "body": body,
            "reply": reply
        })

    return render_batch_review_page(date, categorized)

@app.post("/approve/{thread_id}")
async def approve(thread_id: str, request: Request):
    config = {"configurable": {"thread_id": thread_id}}
    workflow.invoke(Command(resume={"approved": True}), config=config)
    state = workflow.get_state(config).values

    reply = state.get("generated_reply", "")
    sender = state.get("sender", "")
    subject = state.get("subject", "")

    creds = Credentials(token=request.session["access_token"])
    gmail = build("gmail", "v1", credentials=creds)

    email = MIMEText(reply)
    email["to"] = sender
    email["subject"] = subject if subject.lower().startswith("re:") else "Re: " + subject

    raw = base64.urlsafe_b64encode(email.as_bytes()).decode()
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()

    return HTMLResponse("""
        <body style="font-family: Arial; text-align: center; padding: 80px;">
            <h1 style="color: #16a34a;">✓ Approved & Sent via Gmail</h1>
            <a href="/" style="color: #2563eb; font-weight: bold;">Return to Home</a>
        </body>
    """)

@app.post("/reject/{thread_id}")
async def reject(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    workflow.invoke(Command(resume={"approved": False}), config=config)
    return HTMLResponse("""
        <body style="font-family: Arial; text-align: center; padding: 80px;">
            <h1 style="color: #dc2626;">✕ Reply Declined</h1>
            <a href="/" style="color: #2563eb; font-weight: bold;">Return to Home</a>
        </body>
    """)

def render_batch_review_page(date_str, categorized):
    def render_section(title, items, color_code):
        if not items:
            return f"<div style='margin-bottom: 25px;'><h2>{title} (0)</h2><p style='color:#888;'>No emails found.</p></div>"

        cards = ""
        for item in items:
            reply_box = ""
            if item["reply"]:
                reply_box = f"""
                <div style="background: #eff6ff; padding: 12px; border-radius: 8px; margin-top: 10px;">
                    <strong>Suggested Laya Reply:</strong>
                    <p style="white-space: pre-wrap; margin: 5px 0;">{html.escape(item['reply'])}</p>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <form method="post" action="/approve/{item['thread_id']}">
                            <button style="background: #16a34a; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">✓ Approve & Send</button>
                        </form>
                        <form method="post" action="/reject/{item['thread_id']}">
                            <button style="background: #dc2626; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">✕ Decline</button>
                        </form>
                    </div>
                </div>
                """

            cards += f"""
            <div style="background: white; border: 1px solid #cbd5e1; border-radius: 10px; padding: 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between;">
                    <strong>{html.escape(item['sender'])}</strong>
                    <span style="background: {color_code}; color: white; font-size: 12px; padding: 3px 8px; border-radius: 10px;">{title}</span>
                </div>
                <div style="font-weight: bold; margin-top: 5px;">{html.escape(item['subject'])}</div>
                <div style="color: #475569; font-size: 14px; margin-top: 8px; max-height: 80px; overflow-y: auto;">{html.escape(item['body'])}</div>
                {reply_box}
            </div>
            """
        return f"<h2>{title} ({len(items)})</h2>" + cards

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Review - {date_str}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f8fafc; padding: 30px 20px; }}
            .container {{ max-width: 900px; margin: auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .back-btn {{ color: #2563eb; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Emails for {date_str}</h1>
                <a class="back-btn" href="/">← Pick Another Date</a>
            </div>
            {render_section("🔴 Action Required", categorized["action_required"], "#dc2626")}
            {render_section("🔵 Informational", categorized["informational"], "#2563eb")}
            {render_section("🟡 Promotions & Newsletters", categorized["promotions_newsletters"], "#d97706")}
            {render_section("⚪ Spam & Junk", categorized["spam_junk"], "#64748b")}
        </div>
    </body>
    </html>
    """