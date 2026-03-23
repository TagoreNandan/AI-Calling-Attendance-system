from fastapi import FastAPI
from services.sheets import get_parent_number
from services.caller import trigger_call
from fastapi.responses import FileResponse, Response
from fastapi import Request
from fastapi import FastAPI

import requests
import os
from openai import OpenAI
from fastapi import Request

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.get("/")
def home():
    return {"status": "running"}

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


@app.post("/voice")
def voice():
    return "ok"


@app.post("/twiml")
def twiml():

    xml = """
<Response>
    <Play>https://untakable-dylan-jazziest.ngrok-free.dev/question-audio</Play>

    <Record 
        timeout="6"
        maxLength="30"
        playBeep="true"
        transcribe="true"
        transcribeCallback="https://untakable-dylan-jazziest.ngrok-free.dev/transcript"
    />
</Response>
"""
    return Response(content=xml, media_type="application/xml")


@app.post("/transcript")
async def transcript(request: Request):

    form = await request.form()

    text = form.get("TranscriptionText")
    call_sid = form.get("CallSid")

    print("🔥 TRANSCRIPT:", text)

    with open("transcripts.txt", "a") as f:
        f.write(f"{call_sid} :: {text}\n")

    return {"status": "saved"}

@app.post("/recording")
async def recording(request: Request):

    form = await request.form()

    recording_url = form.get("RecordingUrl")

    print("🎙 Recording URL:", recording_url)

    audio = requests.get(recording_url + ".wav")

    with open("temp.wav", "wb") as f:
        f.write(audio.content)

    with open("temp.wav", "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f
        )

    text = transcript.text

    print("🔥 WHISPER TRANSCRIPT:", text)

    with open("transcripts.txt", "a") as f:
        f.write(text + "\n")

    return {"status": "done"}