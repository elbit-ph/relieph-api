from dotenv import load_dotenv
import requests, json, os
from .email_handler import EmailHandler

load_dotenv()

class UserEmailHandler(EmailHandler):
    def __init__(self):
        super().__init__()
    
    async def send_upgrade_approval_notice(self, name:str, email:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p><b>Congratulations</b></p>\
                                <p>Your user has been upgraded to tier level 2. You may now create your own relief effort as a <b>User</b></p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, 'Account Upgraded', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_upgrade_rejection_notice(self, name:str, email:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Unfortunately, your upgrade application was rejected. This may be due to insufficient funds. You may always opt to apply again. </p> \
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, 'Account Upgrade Request Rejected', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }