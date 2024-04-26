from dotenv import load_dotenv
import requests, json, os
from .email_handler import EmailHandler

load_dotenv()

class VolunteerEmailHandler(EmailHandler):
    def __init__(self):
        super().__init__()
    
    async def send_volunteer_acceptance_notice(self, name:str, email:str, relief_name:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>You have been accepted as volunteer for {relief_name}. Kindly stay tuned for further updates from the relief organizer.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, 'Volunteer Acceptance', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_volunteer_rejection_notice(self, name:str, email:str, relief_name:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Unfortunately, our application as volunteer for {relief_name} was rejected. We still thank you for your interests in helping make a change. </p> \
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, 'Volunteer Rejection', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }