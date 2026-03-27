import requests
import os

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")

def trigger_call(to, roll, subject, section):

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Calls.json"

    BASE_URL = "https://untakable-dylan-jazziest.ngrok-free.dev"
    data = {
        "To": to,
        "From": TWILIO_FROM,
        "Url": f"{BASE_URL}/twiml?roll={roll}"
    }

    response = requests.post(
        url,
        data=data,
        auth=(TWILIO_SID, TWILIO_TOKEN)
    )

    print("TWILIO RESPONSE:", response.text)

    return response.json()