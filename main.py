import base64
import html
import os
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from email_ai_agent_latest import workflow
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.middleware.sessions import SessionMiddleware

from authlib.integrations.starlette_client import OAuth

load_dotenv()

app = FastAPI()

app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret-key")
)

# ============================================================
# SHARED CSS STYLES
# ============================================================

COMMON_CSS = """
<style>
    :root {
        --primary-color: #2563eb;
        --primary-hover: #1d4ed8;
        --bg-color: #f8fafc;
        --card-bg: #ffffff;
        --text-main: #0f172a;
        --text-muted: #64748b;
        --border-color: #e2e8f0;
        --radius: 12px;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--bg-color);
        color: var(--text-main);
        line-height: 1.5;
        padding: 40px 20px;
    }

    .container {
        max-width: 800px;
        margin: 0 auto;
    }

    .card-panel {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--radius);
        padding: 32px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        text-align: center;
    }

    h1 {
        font-size: 1.875rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 8px;
        letter-spacing: -0.025em;
    }

    p {
        color: var(--text-muted);
        margin-bottom: 24px;
        font-size: 1rem;
    }

    .btn {
        display: inline-block;
        background-color: var(--primary-color);
        color: #ffffff;
        font-weight: 600;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        transition: background-color 0.2s ease, transform 0.1s ease;
        border: none;
        cursor: pointer;
        font-size: 0.95rem;
    }

    .btn:hover {
        background-color: var(--primary-hover);
    }

    .btn:active {
        transform: scale(0.98);
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 16px;
        max-width: 320px;
        margin: 0 auto;
    }

    input[type="date"] {
        padding: 10px 14px;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        font-size: 1rem;
        color: var(--text-main);
        outline: none;
        transition: border-color 0.2s ease;
    }

    input[type="date"]:focus {
        border-color: var(--primary-color);
    }

    /* Classification Dashboard CSS */
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 32px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-color);
    }

    .header-title h1 {
        margin-bottom: 4px;
    }

    .category-section {
        margin-bottom: 32px;
    }

    .category-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
        text-transform: uppercase;
    }

    /* Category Specific Colors */
    .cat-action_required { color: #dc2626; }
    .cat-action_required .badge { background: #fee2e2; color: #dc2626; }

    .cat-informational { color: #2563eb; }
    .cat-informational .badge { background: #dbeafe; color: #2563eb; }

    .cat-promotions_newsletters { color: #d97706; }
    .cat-promotions_newsletters .badge { background: #fef3c7; color: #d97706; }

    .cat-spam_junk { color: #4b5563; }
    .cat-spam_junk .badge { background: #f3f4f6; color: #4b5563; }

    .email-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: var(--radius);
        padding: 20px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }

    .email-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
    }

    .email-sender {
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--text-main);
        margin-bottom: 4px;
    }

    .email-subject {
        font-weight: 600;
        font-size: 1.05rem;
        color: var(--text-main);
        margin-bottom: 8px;
    }

    .email-body {
        color: var(--text-muted);
        font-size: 0.9rem;
        white-space: pre-wrap;
        max-height: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
    }

    .empty-state {
        color: var(--text-muted);
        font-style: italic;
        font-size: 0.9rem;
        padding: 12px;
        background: #ffffff;
        border: 1px dashed var(--border-color);
        border-radius: 8px;
    }
</style>
"""


# ============================================================
# GOOGLE OAUTH
# ============================================================

oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": (
            "openid email profile https://www.googleapis.com/auth/gmail.readonly"
        )
    },
)


# ============================================================
# GMAIL EMAIL BODY EXTRACTION
# ============================================================


def decode_gmail_data(data):
    if not data:
        return ""

    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", errors="ignore"
        )

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

    # Convert HTML email into plain text
    if mime_type == "text/html":

        soup = BeautifulSoup(body, "html.parser")

        for tag in soup(["script", "style", "head", "noscript"]):
            tag.decompose()

        body = soup.get_text(separator="\n", strip=True)

    body = html.unescape(body).replace("\r", "")

    return "\n".join(
        line.strip() for line in body.splitlines() if line.strip()
    )


# ============================================================
# HOME
# ============================================================


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    today = datetime.now().strftime("%Y-%m-%d")

    is_logged_in = "access_token" in request.session

    if not is_logged_in:

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Laya Email Classifier</title>
            {COMMON_CSS}
        </head>

        <body>
            <div class="container">
                <div class="card-panel">
                    <h1>Laya System 1</h1>
                    <p>Login with Google to classify and prioritize your Gmail inbox.</p>
                    <a href="/login" class="btn">Login with Google</a>
                </div>
            </div>
        </body>
        </html>
        """

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Laya Email Classifier</title>
        {COMMON_CSS}
    </head>

    <body>
        <div class="container">
            <div class="card-panel">
                <h1>Laya System 1</h1>
                <p>Select a date to organize and classify your emails.</p>

                <form action="/review" method="get">
                    <input
                        type="date"
                        name="date"
                        value="{today}"
                        required
                    />

                    <button type="submit" class="btn">
                        Classify Emails
                    </button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """


# ============================================================
# LOGIN
# ============================================================


@app.get("/login")
async def login(request: Request):

    return await oauth.google.authorize_redirect(
        request,
        os.getenv("REDIRECT_URI"),
        prompt="consent select_account",
        access_type="offline",
    )


# ============================================================
# GOOGLE OAUTH CALLBACK
# ============================================================


@app.get("/auth/google/callback")
async def google_callback(request: Request):

    token = await oauth.google.authorize_access_token(request)

    request.session["access_token"] = token["access_token"]

    return RedirectResponse(url="/")


# ============================================================
# CLASSIFY EMAILS
# ============================================================


@app.get("/review", response_class=HTMLResponse)
async def review_emails_for_date(request: Request, date: str = None):

    # User must be logged in
    if "access_token" not in request.session:
        return RedirectResponse(url="/login")

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # --------------------------------------------------------
    # Create Gmail query for selected date
    # --------------------------------------------------------

    try:

        dt = datetime.strptime(date, "%Y-%m-%d")

        next_day = dt + timedelta(days=1)

        query = (
            f"after:{dt.strftime('%Y/%m/%d')} "
            f"before:{next_day.strftime('%Y/%m/%d')}"
        )

    except ValueError:

        return HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html>
            <head>{COMMON_CSS}</head>
            <body>
                <div class="container">
                    <div class="card-panel">
                        <h2>Invalid Date Format</h2>
                        <p>Please return back and select a valid date.</p>
                        <a href="/" class="btn">Back to Home</a>
                    </div>
                </div>
            </body>
            </html>
            """
        )

    # --------------------------------------------------------
    # Connect to Gmail
    # --------------------------------------------------------

    creds = Credentials(token=request.session["access_token"])

    gmail = build("gmail", "v1", credentials=creds)

    # --------------------------------------------------------
    # Get emails
    # --------------------------------------------------------

    response = (
        gmail.users()
        .messages()
        .list(userId="me", q=query, maxResults=50)
        .execute()
    )

    messages = response.get("messages", [])

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    categorized = {
        "action_required": [],
        "informational": [],
        "promotions_newsletters": [],
        "spam_junk": [],
    }

    if not messages:

        return HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html>
            <head>{COMMON_CSS}</head>
            <body>
                <div class="container">
                    <div class="card-panel">
                        <h2>No emails found</h2>
                        <p>No messages located for date <strong>{html.escape(date)}</strong>.</p>
                        <a href="/" class="btn">Select Another Date</a>
                    </div>
                </div>
            </body>
            </html>
            """
        )

    # ========================================================
    # CLASSIFY EACH EMAIL USING LAYA SYSTEM 1
    # ========================================================

    for msg_item in messages:

        msg_id = msg_item["id"]

        full_msg = (
            gmail.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        # ----------------------------------------------------
        # Extract headers
        # ----------------------------------------------------

        headers = full_msg.get("payload", {}).get("headers", [])

        sender = next(
            (
                h["value"]
                for h in headers
                if h["name"].lower() == "from"
            ),
            "Unknown",
        )

        subject = next(
            (
                h["value"]
                for h in headers
                if h["name"].lower() == "subject"
            ),
            "(No Subject)",
        )

        # ----------------------------------------------------
        # Extract body
        # ----------------------------------------------------

        body = extract_email_body(full_msg)

        # ----------------------------------------------------
        # Create state for Laya classifier
        # ----------------------------------------------------

        state = {
            "email_id": msg_id,
            "thread_id": full_msg.get("threadId", msg_id),
            "sender": sender,
            "subject": subject,
            "review": body,
            "category": "informational",
        }

        # ----------------------------------------------------
        # Run Laya System 1 classification
        # ----------------------------------------------------

        result = workflow.invoke(state)

        category = result.get("category", "informational")

        # Safety fallback
        if category not in categorized:
            category = "informational"

        categorized[category].append(
            {
                "sender": sender,
                "subject": subject,
                "body": body,
                "category": category,
            }
        )

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    return render_results(date, categorized)


# ============================================================
# DISPLAY CLASSIFICATION RESULTS
# ============================================================


def render_results(date_str, categorized):

    sections = ""

    category_titles = {
        "action_required": "Action Required",
        "informational": "Informational",
        "promotions_newsletters": "Promotions & Newsletters",
        "spam_junk": "Spam & Junk",
    }

    for category, emails in categorized.items():

        title = category_titles[category]

        cards = ""

        for email in emails:

            cards += f"""
            <div class="email-card">
                <div class="email-sender">
                    {html.escape(email["sender"])}
                </div>

                <div class="email-subject">
                    {html.escape(email["subject"])}
                </div>

                <p class="email-body">{html.escape(email["body"][:1000])}</p>
            </div>
            """

        sections += f"""
        <section class="category-section cat-{category}">
            <h2 class="category-title">
                <span>{title}</span>
                <span class="badge">{len(emails)}</span>
            </h2>

            {cards if cards else '<p class="empty-state">No emails in this category.</p>'}
        </section>
        """

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Email Classification - {html.escape(date_str)}</title>
        {COMMON_CSS}
    </head>

    <body>
        <div class="container">
            <div class="header-bar">
                <div class="header-title">
                    <h1>Laya System 1</h1>
                    <p style="margin-bottom:0;">Email Classification — <strong>{html.escape(date_str)}</strong></p>
                </div>

                <a href="/" class="btn" style="background:#e2e8f0; color:#0f172a;">
                    Change Date
                </a>
            </div>

            {sections}
        </div>
    </body>
    </html>
    """