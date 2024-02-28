import secrets

def generate_code():
    return secrets.token_hex(3).upper()