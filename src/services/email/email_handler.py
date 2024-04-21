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
        self.sender_email = os.environ.get("EMAIL")
    
    def craft_email_body(self, name:str, email:str, subject:str, htmlContent:str):
        body = {
            "sender":{
            "name":"Elbit",
            "email":self.sender_email
        },
        "to":[
            {
                "name": name,
                "email" : email
            }
        ],
        "subject" : subject,
        "htmlContent" : htmlContent
        }

        return body