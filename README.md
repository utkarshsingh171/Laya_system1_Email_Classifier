# Laya System 1 — Email Classifier

**Laya System 1** is a local AI-powered email classification system built with **FastAPI, Gmail API, Google OAuth 2.0, and Laya**.

The application securely connects to a user's Gmail account, retrieves emails for a selected date, processes their content, and uses **Laya running locally** to classify each email into one of four categories.

### Categories

* **Action Required**
* **Informational**
* **Promotions & Newsletters**
* **Spam & Junk**

The goal is to turn a large inbox into a simple, organized view of what actually needs attention.

---

## ✨ Features

* 🔐 **Google OAuth 2.0** — Secure Gmail authentication with read-only access.
* 📅 **Date-Based Email Fetching** — Retrieve emails for a specific date.
* 📧 **Email Parsing** — Handles multipart MIME messages and HTML emails.
* 🤖 **Laya AI Classification** — Uses Laya locally to classify emails.
* 🗂️ **Automatic Categorization** — Groups emails into four useful categories.
* 🎨 **Web Dashboard** — Simple responsive interface for reviewing classified emails.
* 🔒 **Local AI Processing** — The classification workflow runs through the local Laya setup.

---

## 🏗️ How It Works

```text
                    User
                     │
                     ▼
              Google OAuth 2.0
                     │
                     ▼
                Gmail API
                     │
                     ▼
             Fetch Selected Date
                     │
                     ▼
             Email Parsing
          MIME + HTML → Text
                     │
                     ▼
              Local Laya
          AI Classification
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Action   Informational  Promotions
       Required               & Newsletters
                     │
                     ▼
                Spam & Junk
                     │
                     ▼
              Review Dashboard
```

---

## 📁 Project Structure

```text
Laya_system1_Email_Classifier/
│
├── email_ai_agent_latest.py   # Email classification workflow using Laya
├── laya_server.py             # FastAPI server, Gmail API and OAuth
├── main.py                    # Application entry point
├── requirements.txt            # Python dependencies
└── .gitignore                 # Git ignore rules
```

### `email_ai_agent_latest.py`

Contains the email classification workflow. Email information is passed to the local Laya system, which determines the appropriate category.

### `laya_server.py`

Handles the main application logic, including:

* FastAPI routes
* Google OAuth 2.0
* Gmail API communication
* Email fetching
* MIME/HTML parsing
* Dashboard rendering

### `main.py`

Entry point used to start the FastAPI application.

---

# 🛠️ Tech Stack

* **Python**
* **FastAPI**
* **Laya — Local AI Runtime**
* **Google OAuth 2.0**
* **Gmail API**
* **BeautifulSoup**
* **Jinja2**
* **Uvicorn**
* **HTML/CSS**

---

# 🔐 Prerequisites

Before running the project, install:

* Python **3.8+**
* Laya configured and available locally
* A Google Cloud project
* Gmail API enabled
* Google OAuth 2.0 Client ID and Client Secret

Configure the following redirect URI in Google Cloud:

```text
http://localhost:8000/auth/google/callback
```

---

# ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/utkarshsingh171/Laya_system1_Email_Classifier.git
cd laya_game
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-custom-session-secret-key
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
REDIRECT_URI=http://localhost:8000/auth/google/callback
```

> **Never commit your `.env` file or OAuth credentials to GitHub.**

---

# ▶️ Running Laya Locally

Make sure your **local Laya environment is running and ready to process requests**.

Then start the FastAPI application:

```bash
python laya_server.py
```

And run using Uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

---

# 🔄 Workflow

### 1. Login

Open the application and select the Google login option.

The application uses **Google OAuth 2.0** to obtain permission to access Gmail using the configured read-only scope.

### 2. Select a Date

After authentication, select the date for which you want to analyze emails.

The application creates a Gmail query similar to:

```text
after:2026/10/01 before:2026/10/02
```

### 3. Fetch Emails

The Gmail API retrieves the messages matching the selected date.

Relevant information such as the sender, subject, and email body is extracted.

### 4. Parse Email Content

Emails may contain plain text, HTML, or multipart MIME content.

The application processes these formats and converts the relevant content into clean text before classification.

```text
Gmail Email
     │
     ▼
MIME Parsing
     │
     ▼
HTML Cleaning
     │
     ▼
Clean Email Text
```

### 5. Classify Using Local Laya

The processed email is passed to the classification workflow in:

```text
email_ai_agent_latest.py
```

The workflow uses **Laya locally** to determine the category of the email.

```text
Email
  │
  ▼
Local Laya
  │
  ├── Action Required
  ├── Informational
  ├── Promotions & Newsletters
  └── Spam & Junk
```

### 6. Review

The classified emails are displayed on the review dashboard:

```text
/review
```

Emails are grouped by category, allowing the user to quickly identify messages that require attention.

---

# 🧠 Why Local Laya?

Laya is used as the local AI layer for the classification process.

Instead of building the application around a remote AI API, the project uses the **locally running Laya system** to perform the classification workflow.

This makes Laya System 1 a practical example of combining:

```text
Local AI
   +
FastAPI
   +
Gmail API
   +
OAuth 2.0
   =
AI Email Classifier
```

---

# 🔒 Security

The application uses Google OAuth rather than asking users for their Gmail password.

Key security considerations:

* Google OAuth 2.0 authentication
* Gmail read-only access
* Secrets stored in environment variables
* `.env` excluded through `.gitignore`
* Local AI processing through Laya

For production deployment, HTTPS, secure session configuration, proper secret management, and restricted OAuth credentials should be configured.

---

# 🚀 Future Improvements

Possible improvements include:

* Email priority scoring
* Classification confidence scores
* Custom user-defined categories
* Search and filtering
* Classification history
* Human-in-the-loop review
* Batch email processing
* Support for additional email providers
* Production deployment

---

## 📌 Project Summary

**Laya System 1** combines Gmail integration with a locally running AI system to automatically organize emails.

```text
Google Account
      ↓
    Gmail
      ↓
  Email Fetch
      ↓
Email Processing
      ↓
  Local Laya
      ↓
Classification
      ↓
Review Dashboard
```

The project demonstrates how a **local AI runtime can be integrated with a real-world application to automate email organization and reduce manual inbox processing.**
