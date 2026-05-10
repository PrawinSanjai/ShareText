from services.utils import get_env
from cryptography.fernet import Fernet


def get_csv_env(env_var: str, default: str = ""):
    raw_value = get_env(env_var, default=default) or ""
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def get_int_env(env_var: str, default: int):
    raw_value = get_env(env_var, default=None)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        raise ValueError(f"{env_var} must be an integer.")


class Configuration:
    DATABASE_URL = get_env("DATABASE_URL", default=None)
    TEXTIE_API_KEY = get_env("TEXTIE_API_KEY", default=None)
    CRYPT_SECRET_KEY = get_env("CRYPT_SECRET_KEY", default=None)
    CORS_ALLOW_ORIGINS = get_csv_env(
        "CORS_ALLOW_ORIGINS",
        default="http://localhost:5173,http://127.0.0.1:5173",
    )
    RATE_LIMIT_WINDOW_SECONDS = get_int_env("RATE_LIMIT_WINDOW_SECONDS", default=60)
    RATE_LIMIT_MAX_REQUESTS = get_int_env("RATE_LIMIT_MAX_REQUESTS", default=120)
    MAX_REQUEST_BODY_BYTES = get_int_env("MAX_REQUEST_BODY_BYTES", default=25000)

    def validate(self):
        missing = []
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.CRYPT_SECRET_KEY:
            missing.append("CRYPT_SECRET_KEY")

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        try:
            Fernet(self.CRYPT_SECRET_KEY.encode())
        except Exception as exc:
            raise RuntimeError("CRYPT_SECRET_KEY must be a valid Fernet key.") from exc

        if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
            raise RuntimeError("RATE_LIMIT_WINDOW_SECONDS must be greater than 0.")

        if self.RATE_LIMIT_MAX_REQUESTS <= 0:
            raise RuntimeError("RATE_LIMIT_MAX_REQUESTS must be greater than 0.")

        if self.MAX_REQUEST_BODY_BYTES <= 0:
            raise RuntimeError("MAX_REQUEST_BODY_BYTES must be greater than 0.")

BASE_URL = get_env("BASE_URL", default=None)
