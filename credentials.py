import os
import json
from google.oauth2.credentials import Credentials

def get_credentials_map() -> dict[str, Credentials]:
    credentials_map = {}
    for filename in os.listdir():
        if filename.startswith("token_") and filename.endswith(".json"):
            gmail_address = filename[len("token_"):-len(".json")]
            with open(filename, "r") as token_file:
                token_data = json.load(token_file)
                credentials = Credentials.from_authorized_user_info(token_data)
                credentials_map[gmail_address] = credentials
    return credentials_map
