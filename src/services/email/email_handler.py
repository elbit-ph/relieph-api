from dotenv import load_dotenv
import requests, json, os

load_dotenv()

class EmailHandler():
    def __init__(self):
        self.base_URL = base_URL = 'https://api.brevo.com/v3/smtp'
        self.key = os.environ.get("EMAIL_KEY")
        self.headers = {
            "api-key" : self.key,
            "Content-Type" : "application/json",
            "Accept": "application/json",
            "X-Sib-Sandbox" : "drop"
        }