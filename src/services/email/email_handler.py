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
    async def send_code(self, email: str, name: str, code: str):
        body = {
            "sender":{
            "name":"Elbit",
            "email":"jccastillo1105@gmail.com"
        },
        "to":[
            {
                "name": name,
                "email" : email
            }
        ],
        "subject" : "Password Reset",
        "htmlContent" : f"<html><head></head><body>\
                                <p>Good day, {name.split(' ')[0]}</p>\
                                <p>We received a request to reset the password for your account. Below is the code for resetting the password.</p>\
                                <center><h2>{code}</h2></center>\
                                <p>If you did not send a request to change your password, kindly disregard this code and secure your account.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        }

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }