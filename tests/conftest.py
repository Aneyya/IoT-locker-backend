import os, pytest, httpx, keyring
from dotenv import load_dotenv

tests_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(tests_dir, ".env"))

NGROK_URL = os.getenv("NGROK_URL")
RASP_API_KEY = os.getenv("RASP_API_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

if not all ([NGROK_URL, RASP_API_KEY, ADMIN_API_KEY]):
    raise RuntimeError("Brak wymaganych zmiennych w .env")

KEYRING_SERVICE = 'locker_e2e_tests'

@pytest.fixture(scope="session")
def http_client():
# Klient komunikuje sie przez tunel Ngrok
    headers = {
        "ngrok-skip-browser-warning": "true",
        "Content-Type": "application/json",
    }
    with httpx.Client(base_url=NGROK_URL, headers=headers, timeout=10.0) as client:
        yield client

@pytest.fixture(scope="session")
def rasp_headers():
    return {"x-api-key": RASP_API_KEY}

@pytest.fixture(scope="session")
def admin_headers():
    return {"x-api-key": ADMIN_API_KEY}

@pytest.fixture(scope="session")
def seed_data():
# Dane testowe zgodne ze skryptem w seed.py 
    return{
        "machine_id": "KR001",
        "technician_name": "Jan Nowak",
        "courier_login": "test",
        "courier_pass": "test!test!123",
        "pickup_phone": "600111222",
        "pickup_pin": "123456",
        "courier_pkg": 222222222,
        "new_pkg_phone": "500777888",
    }

@pytest.fixture
def secure_state():
# Bezpieczne przechowywanie tokenu sesji w systemowym sejfie (keyring)
    class SecureStateStore:
        def set(self, key: str, value: str) -> None:
            keyring.set_password(KEYRING_SERVICE, key, value)

        def get(self, key: str) -> str | None:
            return keyring.get_password(KEYRING_SERVICE, key)

        def delete(self, key: str) -> None:
            try:
                keyring.delete_password(KEYRING_SERVICE, key)
            except keyring.errors.PasswordDeleteError:
                pass

    return SecureStateStore()
