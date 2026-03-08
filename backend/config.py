from services.utils import get_env

class Configuration:
    DATABASE_URL = get_env("DATABASE_URL", default=None)
    print("DATABASE_URL", DATABASE_URL)
    TEXTIE_API_KEY = get_env("TEXTIE_API_KEY", default=None)
    CRYPT_SECRET_KEY = get_env("CRYPT_SECRET_KEY", default=None)

BASE_URL = get_env("BASE_URL", default=None)