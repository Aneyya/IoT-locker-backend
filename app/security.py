import hashlib, secrets, os, logging
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
RASP_API_KEY = os.getenv("RASP_API_KEY")
if not ADMIN_API_KEY or not RASP_API_KEY:
    logger.critical("BRAK KLUCZY API w zmiennych srodowiskowych!")
    raise RuntimeError("BRAK KLUCZY API w zmiennych srodowiskowych!")

PIN_PEPPER = os.getenv("PIN_PEPPER")
if not PIN_PEPPER:
    logger.critical("Brak zmiennej PIN_PEPPER w zmiennych srodowiskowych!")
    raise RuntimeError("Brak zmiennej PIN_PEPPER w zmiennych srodowiskowych!")

ph = PasswordHasher()

def verify_admin_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or not secrets.compare_digest(x_api_key.encode('utf-8'), ADMIN_API_KEY.encode('utf-8'),):
        reason = "brak naglowka x-api-key" if not x_api_key else "nieprawidlowy klucz API"
        logger.warning(f"Odrzucono probe dostepu do zasobow ADMIN ({reason})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak uprawnien administratora"
        )
    return x_api_key

def verify_rasp_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or not secrets.compare_digest(x_api_key.encode('utf-8'), RASP_API_KEY.encode('utf-8')):
        reason = "brak naglowka x-api-key" if not x_api_key else "nieprawidlowy klucz API"
        logger.warning(f"Odrzucono probe dostepu urzadzenia IoT ({reason})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak autoryzacji urzadzenia IoT (nieprawidlowy API KEY)"
        )
    return x_api_key

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password,)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_secret(secret_data: str) -> str:
    salted = f"{PIN_PEPPER}:{secret_data}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

def generate_pin_code() -> tuple[str, str]:
    pin = "".join(str(secrets.randbelow(10)) for _ in range(6))
    return pin, hash_secret(pin)

def generate_session_token() -> tuple[str, str]:
    token = secrets.token_hex(32)
    return token, hash_secret(token)

