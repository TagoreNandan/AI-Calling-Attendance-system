import requests
import os

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")

def trigger_call(to):

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Calls.json"

    data = {
        "To": to,
        "From": TWILIO_FROM,
        "Url": "http://demo.twilio.com/docs/voice.xml"
    }

    response = requests.post(
        url,
        data=data,
        auth=(TWILIO_SID, TWILIO_TOKEN)
    )

    print("TWILIO RESPONSE:", response.text)

    return response.status_code