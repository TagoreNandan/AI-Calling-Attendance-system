from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from services.sheets import get_parent_number
from services.caller import trigger_call

import requests
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from faster_whisper import WhisperModel
from difflib import get_close_matches
from fastapi.responses import HTMLResponse
from services.sheets import sheet
from datetime import datetime
from services.sheets import create_daily_sheet

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

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

    subject = "AIML"
    section = "A"
    response = trigger_call(phone, roll, subject, section)
    
    call_sid = response.get("sid")
    call_map[call_sid] = {
        "roll": roll,
        "subject": subject,
        "section": section,
        "date": datetime.now().strftime("%Y-%m-%d")
        }
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

    data = call_map.get(call_sid)
    
    if isinstance(data, str):
        roll = data
        subject = "UNKNOWN"
        section = "UNKNOWN"
        date = "UNKNOWN"
    else:
        roll = data.get("roll")
        subject = data.get("subject")
        section = data.get("section")
        date = data.get("date")

    sheet_name = f"{date}_{subject}_{section}"

    recording_url = form.get("RecordingUrl")

    print("📊 WRITING TO SHEET:", sheet_name)

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

    # 🔥 DAILY SHEET LOGIC (CLEAN)
    try:
        sheet = create_daily_sheet(sheet_name)
    except:
        sheet = client.create(sheet_name).sheet1
        sheet.append_row(["roll", "reason", "transcript"])

    sheet.append_row([roll, reason, text])

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





@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():

    records = sheet.get_all_records()

    total = len(records)
    sick = 0
    travel = 0
    other = 0

    rows_html = ""

    for row in records:

        reason = str(row.get("Reason", "")).upper()

        if reason == "SICK":
            sick += 1
        elif reason == "TRAVEL":
            travel += 1
        else:
            other += 1

        rows_html += f"""
        <tr>
            <td>{row.get('roll')}</td>
            <td>{row.get('phone')}</td>
            <td>{row.get('Reason')}</td>
            <td>{row.get('Transcript')}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <title>AI Attendance Dashboard</title>
        <style>
            body {{
                font-family: Arial;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #333;
            }}
            .stats {{
                margin-bottom: 20px;
            }}
            .box {{
                display: inline-block;
                padding: 10px 20px;
                margin-right: 10px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                padding: 10px;
                border: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background: #333;
                color: white;
            }}
        </style>
    </head>

    <body>
        <h1>📊 AI Attendance Dashboard</h1>

        <div class="stats">
            <div class="box">Total Calls: {total}</div>
            <div class="box">SICK: {sick}</div>
            <div class="box">TRAVEL: {travel}</div>
            <div class="box">OTHER: {other}</div>
        </div>

        <table>
            <tr>
                <th>Roll</th>
                <th>Phone</th>
                <th>Reason</th>
                <th>Transcript</th>
            </tr>
            {rows_html}
        </table>

    </body>
    </html>
    """

    return html




@app.post("/start-calls")
async def start_calls(data: dict):

    rolls = data.get("rolls")
    subject = data.get("subject")
    section = data.get("section")

    date = datetime.now().strftime("%Y-%m-%d")

    results = []

    for roll in rolls:

        roll = roll.strip()  # clean input
        phone = get_parent_number(roll)

        if phone:
            response = trigger_call(phone, roll)

            call_sid = response.get("sid")

            # 🔥 STORE EVERYTHING
            call_map[call_sid] = {
                "roll": roll,
                "subject": subject,
                "section": section,
                "date": date
            }

            results.append({"roll": roll, "status": "called"})
        else:
            results.append({"roll": roll, "status": "not found"})

    return {
        "message": "Calls initiated",
        "results": results
    }



@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <body style="font-family: Arial; padding: 40px">

    <h2>📞 AI Attendance Calling System</h2>

    <label>Subject:</label>
    <input id="subject"><br><br>

    <label>Section:</label>
    <input id="section"><br><br>

    <label>Absentees (comma separated):</label><br>
    <textarea id="rolls" rows="5" cols="40"></textarea><br><br>

    <button onclick="startCalls()">Start Calling</button>

    <p id="result"></p>

    <script>
    async function startCalls() {

        let rolls = document.getElementById("rolls").value.split(",");

        let res = await fetch("/start-calls", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                subject: document.getElementById("subject").value,
                section: document.getElementById("section").value,
                rolls: rolls
            })
        });

        let data = await res.json();

        document.getElementById("result").innerText =
            JSON.stringify(data, null, 2);
    }
    </script>

    </body>
    </html>
    """