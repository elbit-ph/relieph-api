from dotenv import load_dotenv
import requests, json, os
from .email_handler import EmailHandler

load_dotenv()

class ReliefEmailHandler(EmailHandler):
    def __init__(self):
        super().__init__()
    
    async def send_rejection(self, email:str, name:str, title: str):
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
        "subject" : "Relief Effort Rejection",
        "htmlContent" : f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Unfortunately, your relief effort, <b>{title}</b>, was <b style='color:red'>REJECTED</b>. This may be due to the following reasons, but not limited to:</p>\
                                <ul>\
                                    <li>Irrelevant Relief Effort</li>\
                                    <li>Too many similar initiatives</li>\
                                    <li>Insufficient details</li>\
                                </ul>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        }

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_approval(self, email:str, name:str, title: str):
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
        "subject" : "Relief Effort Approval",
        "htmlContent" : f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>We are delighted to inform you that your relief effort, <b>{title}</b>, has been approved and is now public.</p>\
                                <p>We wish you the best of luck on your initiative.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        }

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }
    
    async def send_deletion_notice(self, email:str, name:str, title: str):
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
        "subject" : "Relief Effort Deletion",
        "htmlContent" : f"<html><head></head><body>\
                                <p>Greetings, {name.split(' ')[0]}</p>\
                                <p>Your relief effort, titled <b>{title}</b>, has been marked as deleted and would no longer be able to accept donations and volunteers. This is due to a breach of rules and terms of the platform.</p>\
                                <p>If you think that this was an error, kindly send us an email.</p>\
                                <p>Regards,<br /><b>Elbit Development Team</b></p>\
                            </body>\
                            </html>"
        }

        res = requests.request('POST', f'{self.base_URL}/email', headers=self.headers, data=json.dumps(body, indent=4))
        return {
            "status": res.status_code,
            "body" : res.json()
        }