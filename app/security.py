import uuid, os
from passlib.context import CryptContext
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
IOT_RASP_API_KEY = os.getenv("IOT_RASP_API_KEY")

def verify_admin_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak uprawnien administartora"
        )
    return x_api_key

def verify_rasp_api_key(x_api_key: str = Header(None, alias="x-api-key")) -> str:
    if not x_api_key or x_api_key != IOT_RASP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ERROR: Brak autoryzacji urzadzenia IoT (nieprawidlowy API KEY)"
        )
    return x_api_key

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_session_tocken() -> str:
    return str(uuid.uuid4())

