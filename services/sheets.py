import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

# your sheet
sheet = client.open_by_key("1ZT7rcsAARUTgYsPHivEU8T_RjFkghajvu7bIb9hL9D0").sheet1


# ---------- GET PHONE ----------
def get_parent_number(roll):

    records = sheet.get_all_records()

    for row in records:
        if row["roll"] == roll:
            return row["phone"]

    return None


# ---------- UPDATE REASON ----------
def update_reason(roll, reason, transcript):

    records = sheet.get_all_records()

    for i, row in enumerate(records):
        if row["roll"] == roll:

            row_index = i + 2  # header offset

            # Column 4 = Reason
            # Column 5 = Transcript
            sheet.update_cell(row_index, 4, reason)
            sheet.update_cell(row_index, 5, transcript)

            return True

    return False