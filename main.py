from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from services.sheets import get_parent_number
from services.caller import trigger_call

import requests
import os
from faster_whisper import WhisperModel
from difflib import get_close_matches
from services.sheets import update_reason

app = FastAPI()
model = WhisperModel("base", compute_type="int8")
call_map = {}


# ---------- INTENT DETECTION ----------
def detect_reason(text):

    text = text.lower().split()

    sick_words = [
        "sick","fever","ill","hospital","doctor",
        "health","cold","cough","vomit"
    ]

    travel_words = [
        "travel","village","native","trip",
        "journey","bus","train","flight"
    ]

    function_words = [
        "function","marriage","wedding","ceremony",
        "festival","pooja"
    ]

    # flatten text words for fuzzy matching
    for word in text:

        # check sick
        if word in sick_words:
            return "SICK"

        if get_close_matches(word, sick_words, cutoff=0.6):
            return "SICK"

        # check travel
        if word in travel_words:
            return "TRAVEL"

        if get_close_matches(word, travel_words, cutoff=0.6):
            return "TRAVEL"

        # check function
        if word in function_words:
            return "FUNCTION"

        if get_close_matches(word, function_words, cutoff=0.6):
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

    response = trigger_call(phone, roll)
    call_sid = response.get("sid")
    call_map[call_sid] = roll
    print("🧠 MAPPING:", call_sid, "->", roll)
    return {
        "roll": roll,
        "phone": phone,
        "call_status": response
    }


# ---------- RECORDING WEBHOOK (WHISPER) ----------

@app.post("/recording")
async def recording(request: Request):

    form = await request.form()
    call_sid = form.get("CallSid")
    roll = request.query_params.get("roll")

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
    update_reason(roll, reason, text)

    print("📌 CALL SID:", call_sid)
    print("📌 ROLL FOUND:", roll)

    return {"status": "done"}



@app.api_route("/twiml", methods=["GET", "POST"])
def twiml(request: Request):

    roll = request.query_params.get("roll")

    xml = f"""
<Response>
    <Play>https://untakable-dylan-jazziest.ngrok-free.dev/question-audio</Play>

    <Record
        timeout="6"
        maxLength="60"
        playBeep="true"
        recordingStatusCallback="https://untakable-dylan-jazziest.ngrok-free.dev/recording?roll={roll}"
    />
</Response>
"""

    return Response(content=xml, media_type="application/xml")