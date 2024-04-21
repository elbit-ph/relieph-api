from dotenv import load_dotenv
import requests, json, os
from .email_handler import EmailHandler

load_dotenv()

class OrganizationEmailHandler(EmailHandler):
    def __init__(self):
        super().__init__()

    async def send_deletion_notice(self, email:str, name:str, organization_name: str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>This email is to inform you that your organization, {organization_name}, has been deleted.</p>\
                                <p>If you believe that this was an error, kindly send us an email</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = await self.craft_email_body(name, email, 'Organization Deletion', email_content)

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_organization_creation_notice(self, email:str, name:str, organization_name: str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Thank you for taking interest with us in providing relief to people in need. Your organization, {organization_name}, has been created and is now for approval. Kindly stay tune for any updates we'll send.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, 'Organization Creation', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_organization_tier_notice(self, email:str, name:str, organization_name: str, level: int):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p><b>Congratulations</b></p>\
                                <p>Your organization, {organization_name}, has now been promoted to level {level}. Thank you for taking interest in helping those in need. We always wish you luck in your endeavours.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        
        body = self.craft_email_body(name, email, 'Organization Promotion', email_content)
        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_approved_notification(self, email:str, name:str, organization_name:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p><b>Congratulations</b></p>\
                                <p>Your organization, {organization_name}, has been approved and can now create relief efforts. Thank you for taking interest in helping those in need. We always wish you luck in your endeavours.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, "Organization Application Acceptance", email_content)

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_rejected_notification(self, email:str, name:str, organization_name:str):
        email_content = f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Your organization, {organization_name}, has been rejected due to insufficient backing documents. You are always welcome to try again. Thank you for taking interest in helping those in need. We always wish you luck in your endeavours.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        body = self.craft_email_body(name, email, "Organization Application Acceptance", email_content)

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }