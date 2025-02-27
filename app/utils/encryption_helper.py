from cryptography.fernet import Fernet

fernet = Fernet(b"OdrLmcLmg1DS3hPWj9RBCjcG9SqY2wL3k01EUBaATbk=")

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()
