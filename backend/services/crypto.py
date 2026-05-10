from cryptography.fernet import Fernet

from config import Configuration

config = Configuration()
config.validate()
fernet = Fernet(key=config.CRYPT_SECRET_KEY.encode())

def encrypt_text_string(text: str):
    encrypted_text = fernet.encrypt(text.encode())
    return encrypted_text.decode()

def decode_text_string(text: str):
    decrypted_text = fernet.decrypt(text.encode())
    return decrypted_text.decode()
