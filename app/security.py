import hashlib, secrets, os
from passlib.context import CryptContext
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
RASP_API_KEY = os.getenv("RASP_API_KEY")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_admin_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or not secrets.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak uprawnien administartora"
        )
    return x_api_key

def verify_rasp_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or not secrets.compare_digest(x_api_key, RASP_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak autoryzacji urzadzenia IoT (nieprawidlowy API KEY)"
        )
    return x_api_key

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_secret(secret_data: str) -> str:
    return hashlib.sha256(secret_data.encode('utf-8')).hexdigest()

def generate_pin_code() -> str:
    pin = "".join(str(secrets.randbelow(10)) for _ in range(6))
    return hash_secret(pin)

def generate_session_token() -> str:
    return hash_secret(secrets.token_hex(32))

