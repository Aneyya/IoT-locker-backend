import uuid
from fastapi import FastAPI, Depends, Header, HTTPException
from app.database import engine, Base, SessionLocal
from app.database_model import *
from sqlalchemy.orm import Session
from app.schemas import *

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

#
# Szkielet endpointów (TESTOWE)
#
@app.get("/", tags=["System"], response_model=RootResponse)
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}

@app.get("/api/machines/{machine_id}/lockers", tags=["Maszyna IoT"], response_model=MachineStatusResponse)
def get_machine_lockers(machine_id: str, db: Session = Depends(get_db)):
    print(f"Pobieranie skrytek dla maszyny {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()

    if not machine:
        raise HTTPException(status_code=404, detail=f"Maszyna {machine_id} nie istnieje w bazie")

    lockers = db.query(Locker).filter(Locker.machine_id == machine_id).all()

    return {
        "machine_id": machine_id,
        "service_locker_id": machine.service_locker_id,
        "is_service_open": machine.is_service_open,
        "lockers": [{"locker_id": l.locker_id, "status": l.status} for l in lockers]
    }

@app.post("/api/auth/technician-verify", tags=["Maszyna IoT"], response_model=TechnicianVerifyResponse)
def verify_technician(payload: TechnicianVerifyRequest, db: Session = Depends(get_db)):
    print(f"Weryfikacja technika: {payload.full_name} na maszynie {payload.machine_id}")

    technician = db.query(Technician).filter(Technician.full_name == payload.full_name).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Bledne dane technika")

    machine = db.query(Machine).filter(Machine.machine_id == payload.machine_id).first()

    machine.is_service_open = True
    db.commit()

    return {
        "access_granted": True, 
        "message": "Tryb serwisowy odblokowany",
        "machine_id": machine.machine_id,
        "service_locker": machine.service_locker_id,
        "action": "OPENED"
        }

#Endpoint czysto prototypowy przez brak czujników na skrytkach :)
@app.get("/api/machines/{machine_id}/service-close", tags=["Maszyna IoT"], response_model=SuccessResponse)
def close_service_locker(machine_id: str, db: Session = Depends(get_db)):
    print(f"Zamykanie skrytki serwisowej na maszynie {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()

    machine.is_service_open = False
    db.commit()
    
    return {"success": True, "message": "Zamykam skrytke"}

# Klienci
@app.post("/api/recipient/pickup", tags=["Klienci"], response_model=SuccessResponse)
def recipient_pickup(payload: RecipientPickupRequest):
    print(f"Odbior paczki telefon {payload.recipient_phone}")
    return {"success": True, "message": "Otwieram skrytke"}
            
@app.post("/api/sender/create-package", tags=["Klienci"], response_model=SuccessResponse)
def seander_create_package(payload: SenderCreateRequest):
    print(f"Nadanie paczki do {payload.recipient_phone}")
    return {"success": True, "message": "Paczka zarejestrowana, otwieram skrytke"}

# Kurier
@app.post("/api/auth/courier-login", tags=["Kurier"], response_model=CourierLoginResponse)
def courier_login(payload: CourierLoginRequest):
    print(f"Logowanie kuriera {payload.courier_login}")
    fake_tocken= str(uuid.uuid4())
    return {"authenticated": True, "tocken_session":fake_tocken}

@app.post("/api/auth/courier-logout", tags=["Kurier"], response_model=SuccessResponse)
def courier_logout(x_auth_tocken: str = Header(None)):
    print(f"Wylogowanie kuriera. Tocken {x_auth_tocken}")
    return {"success": True, "message":"Wylogowano"}

@app.get("/api/courier/pickups", tags=["Kurier"], response_model=CourierPickupsResponse)
def get_courier_pickups(x_auth_tocken: str = Header(None)):
    print(f"Kurier pobiera liste paczek do wyjecia Token: {x_auth_tocken}")
    return {"success": True, "lockers_to_open":["POX001", "POX002"], "message":"Otwieram skrytki"}

@app.post("/api/courier/deliver", tags=["Kurier"], response_model=SuccessResponse)
def courier_deliver(payload: CourierDeliverRequest, x_auth_tocken: str = Header(None)):
    print(f"Kurier dorecza paczke nr: {payload.package_number}. Tocken: {x_auth_tocken}")
    return {"success": True, "message": "Paczka zarejestrowana, otwieram skrytke"}