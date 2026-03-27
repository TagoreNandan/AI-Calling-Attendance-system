from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.sheets import get_parent_number, create_daily_sheet
from services.caller import trigger_call

import requests
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from faster_whisper import WhisperModel
from difflib import get_close_matches
from datetime import datetime

# -------------------- INIT --------------------

app = FastAPI()

# ✅ FIX: static should NOT override "/"
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")

# -------------------- GOOGLE SHEETS --------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

# -------------------- MODEL --------------------

model = WhisperModel("base", compute_type="int8")

# -------------------- MEMORY --------------------

call_map = {}

# -------------------- REQUEST MODEL --------------------

class CallRequest(BaseModel):
    subject: str
    section: str
    rolls: list[str]

# -------------------- INTENT DETECTION --------------------

def detect_reason(text):
    text = text.lower().split()

    sick_words = ["sick","fever","ill","hospital","doctor","health","cold","cough","vomit"]
    travel_words = ["travel","village","native","trip","journey","bus","train","flight"]
    function_words = ["function","marriage","wedding","ceremony","festival","pooja"]

    for word in text:
        if word in sick_words or get_close_matches(word, sick_words, cutoff=0.6):
            return "SICK"
        if word in travel_words or get_close_matches(word, travel_words, cutoff=0.6):
            return "TRAVEL"
        if word in function_words or get_close_matches(word, function_words, cutoff=0.6):
            return "FUNCTION"

    return "OTHER"

# -------------------- START CALLS --------------------

@app.post("/start-calls")
def start_calls(data: CallRequest):

    subject = data.subject
    section = data.section
    rolls = data.rolls
    date = datetime.now().strftime("%Y-%m-%d")

    results = []

    for roll in rolls:
        roll = roll.strip()
        phone = get_parent_number(roll)

        if phone:
            response = trigger_call(phone, roll, subject, section)
            call_sid = response.get("sid")

            call_map[call_sid] = {
                "roll": roll,
                "subject": subject,
                "section": section,
                "date": date
            }

            results.append({"roll": roll, "status": "called"})
        else:
            results.append({"roll": roll, "status": "not found"})

    return {"message": "Calls initiated", "results": results}

# -------------------- AUDIO --------------------

@app.get("/question-audio")
def question_audio():
    return FileResponse("question.mp3", media_type="audio/mpeg")

# -------------------- RECORDING --------------------

@app.post("/recording")
async def recording(request: Request):

    form = await request.form()
    call_sid = form.get("CallSid")

    data = call_map.get(call_sid, {})

    roll = data.get("roll", "UNKNOWN")
    subject = data.get("subject", "UNKNOWN")
    section = data.get("section", "UNKNOWN")
    date = data.get("date", "UNKNOWN")

    sheet_name = f"{date}_{subject}_{section}"

    print("📊 WRITING TO SHEET:", sheet_name)

    recording_url = form.get("RecordingUrl")

    audio = requests.get(
        recording_url + ".wav",
        auth=(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
    )

    with open("temp.wav", "wb") as f:
        f.write(audio.content)

    segments, _ = model.transcribe("temp.wav")

    text = ""
    for segment in segments:
        text += segment.text

    print("🔥 TRANSCRIPT:", text)

    reason = detect_reason(text)

    print("✅ REASON:", reason)

    # ✅ CLEAN SHEET HANDLING
    sheet = create_daily_sheet(sheet_name)
    sheet.append_row([roll, reason, text])

    return {"status": "done"}

# -------------------- TWIML --------------------

@app.api_route("/twiml", methods=["GET", "POST"])
def twiml(request: Request):

    roll = request.query_params.get("roll")

    BASE_URL = "https://untakable-dylan-jazziest.ngrok-free.dev"

    xml = f"""
<Response>
    <Play>{BASE_URL}/question-audio</Play>

    <Record
        timeout="6"
        maxLength="60"
        playBeep="true"
        recordingStatusCallback="{BASE_URL}/recording?roll={roll}"
    />
</Response>
"""

    return Response(content=xml, media_type="application/xml")