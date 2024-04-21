
class AuthDetails():
    user_id: str
    username: str
    level: str

    def __init__(self, user_id:str, username:str, level:str):
        self.user_id = user_id
        self.username = username
        self.level = level