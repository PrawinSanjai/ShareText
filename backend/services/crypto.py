from cryptography.fernet import Fernet

from config import Configuration

config = Configuration()

def encrypt_text_string(text: str):
    f = Fernet(key=config.CRYPT_SECRET_KEY)
    encrypted_text = f.encrypt(text.encode())
    return encrypted_text.decode()

def decode_text_string(text: str):
    f = Fernet(key=config.CRYPT_SECRET_KEY)
    decrypted_text = f.decrypt(text.encode())
    return decrypted_text.decode()