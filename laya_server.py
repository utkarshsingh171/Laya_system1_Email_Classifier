import subprocess
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Laya System 1 API")

@app.post("/v1/systemone")
async def system_one(request: Request):
    payload = await request.json()
    
    documents = payload.get("state", {}).get("documents", "")
    questions = payload.get("questions", {})
    
    # Process Laya classification
    # If using Laya CLI directly via subprocess:
    try:
        # Run laya command using the documents text
        cmd = ["laya", "--json", documents]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse output or mock schema structured for systemone endpoint
        return JSONResponse({
            "routing": {"model": "laya-system-1"},
            "answers": {
                "email_category": {
                    "choice": "action_required" if "reply" in documents.lower() or "urgent" in documents.lower() else "informational"
                },
                "draft_reply": {
                    "text": "Thank you for reaching out. I have received your message and will update you shortly."
                }
            }
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)