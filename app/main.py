import uuid
from fastapi import FastAPI, Depends, Header
from app.database import engine, Base, SessionLocal
from app.database_model import *
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Inicjalizacja bazy
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iot Locker Backend",
    description="Backend do zarzadzania skrytkami pocztowymi"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Model danych (PYDANTIC)
class TechnicianVerifyRequest(BaseModel):
    machine_id: str
    full_name: str

class RecipientPickupRequest(BaseModel):
    recipient_phone: str
    pin_code: str

class SenderCreateRequest(BaseModel):
    recipient_phone: str

class CourierLoginRequest(BaseModel):
    courier_login: str
    password: str

class CourierDeliverRequest(BaseModel):
    package_number: int

#
# Szkielet endpointów (TESTOWE)
#
@app.get("/", tags=["System"])
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}

@app.get("/api/machines/{machine_id}/lockers", tags=["Maszyna IoT"])
def get_machine_lockers(machine_id: str, db: Session = Depends(get_db)):
    print(f"Pobieranie skrytek dla maszyny {machine_id}")
    return [
        {"locker_id": "POX001", "status": "AVAILABLE"}, 
        {"locker_id": "POX002",  "status": "AVAILABLE"}
        ]

@app.post("/api/auth/technician-verify", tags=["Maszyna IoT"])
def verify_technician(payload: TechnicianVerifyRequest):
    print(f"Weryfikacja technika: {payload.full_name} na maszynie {payload.machine_id}")
    return {"access_granted": True, "message": "Tryb serwisowy odblokowany"}

# Klienci
@app.post("/api/recipient/pickup", tags=["Klienci"])
def recipient_pickup(payload: RecipientPickupRequest):
    print(f"Odbior paczki telefon {payload.recipient_phone}")
    return {"success": True, "message": "Otwieram skrytke"}
            
@app.post("/api/sender/create-package", tags=["Klienci"])
def seander_create_package(payload: SenderCreateRequest):
    print(f"Nadanie paczki do {payload.recipient_phone}")
    return {"success": True, "message": "Paczka zarejestrowana, otwieram skrytke"}

# Kurier
@app.post("/api/auth/courier-login", tags=["Kurier"])
def courier_login(payload: CourierLoginRequest):
    print(f"Logowanie kuriera {payload.courier_login}")
    fake_tocken= str(uuid.uuid4())
    return {"authenticated": True, "tocken_session":fake_tocken}

@app.post("/api/auth/courier-logout", tags=["Kurier"])
def courier_logout(x_auth_tocken: str = Header(None)):
    print(f"Wylogowanie kuriera. Tocken {x_auth_tocken}")
    return {"success": True, "message":"Wylogowano"}

@app.get("/api/courier/pickups", tags=["Kurier"])
def get_courier_pickups(x_auth_tocken: str = Header(None)):
    print(f"Kurier pobiera liste paczek do wyjecia Token: {x_auth_tocken}")
    return {"success": True, "lockers_to_open":["POX001", "POX002"], "message":"Otwieram skrytki"}

@app.post("/api/courier/deliver", tags=["Kurier"])
def courier_deliver(payload: CourierDeliverRequest, x_auth_tocken: str = Header(None)):
    print(f"Kurier dorecza paczke nr: {payload.package_number}. Tocken: {x_auth_tocken}")
    return {"success": True, "message": "Paczka zarejestrowana, otwieram skrytke"}