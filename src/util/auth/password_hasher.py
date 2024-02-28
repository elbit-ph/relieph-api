import bcrypt

def hashPassword(password: str):
    # converted password to byte string
    password = password.encode("utf-8")
    # hashed using built-in salt from bcrypt
    hashed = bcrypt.hashpw(password, bytes(bcrypt.gensalt()))
    
    # returned hashed password string
    return hashed.decode('utf-8')

def isPasswordMatch(password:str, passwordHash:str):
    # compared password attempt with stored hashed password; returns true
    return bcrypt.checkpw(password.encode('utf-8'), passwordHash)