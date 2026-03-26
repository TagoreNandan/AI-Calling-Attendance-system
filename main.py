from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from services.sheets import get_parent_number
from services.caller import trigger_call

import requests
import os
from faster_whisper import WhisperModel

app = FastAPI()
model = WhisperModel("base", compute_type="int8")


# ---------- INTENT DETECTION ----------
def detect_reason(text):

    text = text.lower()

    sick_words = [
        "sick","fever","ill","hospital","doctor",
        "not well","health","cold","cough","vomit"
    ]

    travel_words = [
        "travel","village","native","trip",
        "journey","bus","train","flight"
    ]

    function_words = [
        "function","marriage","wedding","ceremony",
        "festival","pooja"
    ]

    for w in sick_words:
        if w in text:
            return "SICK"

    for w in travel_words:
        if w in text:
            return "TRAVEL"

    for w in function_words:
        if w in text:
            return "FUNCTION"

    return "OTHER"


# ---------- ROUTES ----------

@app.get("/")
def home():
    return {"status": "AI Calling Backend Running"}


@app.get("/question-audio")
def question_audio():
    return FileResponse("question.mp3", media_type="audio/mpeg")


@app.post("/call/{roll}")
def call_parent(roll: str):

    phone = get_parent_number(roll)

    if not phone:
        return {"error": "Roll not found"}

    response = trigger_call(phone)

    return {
        "roll": roll,
        "phone": phone,
        "call_status": response
    }


# ---------- RECORDING WEBHOOK (WHISPER) ----------

@app.post("/recording")
async def recording(request: Request):

    form = await request.form()

    recording_url = form.get("RecordingUrl")

    print("🎙 Recording URL:", recording_url)

    audio = requests.get(
    recording_url + ".wav",
    auth=(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
    )

    with open("temp.wav", "wb") as f:
        f.write(audio.content)

    segments, info = model.transcribe("temp.wav")

    text = ""
    for segment in segments:
        text += segment.text

    print("🔥 LOCAL WHISPER TRANSCRIPT:", text)

    reason = detect_reason(text)

    print("✅ DETECTED REASON:", reason)

    with open("transcripts.txt", "a") as f:
        f.write(f"{reason} :: {text}\n")

    return {"status": "done"}