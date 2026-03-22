from fastapi import FastAPI
from services.sheets import get_parent_number
from services.caller import trigger_call

app = FastAPI()


@app.get("/")
def home():
    return {"status": "running"}


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