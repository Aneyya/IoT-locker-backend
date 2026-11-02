import random
from fastapi import FastAPI, Depends, Header, HTTPException, status
from app.database import engine, Base, SessionLocal
from app.database_model import *
from sqlalchemy.orm import Session
from app.schemas import *
from security import *

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
# ENDPOINTY
#
@app.get("/", tags=["System"], response_model=RootResponse)
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}

@app.get("/api/machines/{machine_id}/lockers", tags=["Maszyna IoT"], response_model=MachineStatusResponse)
def get_machine_lockers(machine_id: str, db: Session = Depends(get_db), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Pobieranie skrytek dla maszyny {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Maszyna {machine_id} nie istnieje w bazie"
        )

    lockers = db.query(Locker).filter(Locker.machine_id == machine_id).all()

    return {
        "machine_id": machine_id,
        "service_locker_id": machine.service_locker_id,
        "is_service_open": machine.is_service_open,
        "lockers": [{"locker_id": l.locker_id, "status": l.status} for l in lockers]
    }

@app.post("/api/auth/technician-verify", tags=["Admin"], response_model=TechnicianVerifyResponse)
def verify_technician(payload: TechnicianVerifyRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_admin_api_key)):
    print(f"Weryfikacja technika: {payload.full_name} na maszynie {payload.machine_id}")

    technician = db.query(Technician).filter(Technician.full_name == payload.full_name).first()
    if not technician:
        fail_log = ServiceLog(
            machine_id=payload.machine_id,
            tech_id=payload.tech_id,
            action="REMOTE_VERIFY_FAILED"
        )
        db.add(fail_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Bledne dane technika"
        )

    machine = db.query(Machine).filter(Machine.machine_id == payload.machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Maszyna {payload.machine_id} nie istnieje w bazie"
        )

    succes_log = ServiceLog(
        machine_id=payload.machine_id,
        tech_id=technician.tech_id,
        action="REMOTE_VERIFY_SUCCESS"
    )
    db.add(succes_log)
    machine.is_service_open = True

    db.commit()

    return {"access_granted": True, "message": "Tryb serwisowy odblokowany"}

#Endpoint czysto prototypowy przez brak czujników na skrytkach :)
@app.get("/api/machines/{machine_id}/service-close", tags=["Admin"], response_model=SuccessResponse)
def close_service_locker(machine_id: str, db: Session = Depends(get_db), api_key: str = Depends(verify_admin_api_key)):
    print(f"Zamykanie skrytki serwisowej na maszynie {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Maszyna {machine_id} nie istnieje w bazie"
        )

    success_close_log = ServiceLog(
        machine_id=machine_id,
        tech_id=None,
        action = "SERVICE_CLOSE_SUCCESS"
    )
    db.add(success_close_log)
    machine.is_service_open = False

    db.commit()
    
    return {"success": True, "message": "Zamykam skrytke"}

# Klienci
@app.post("/api/machines/{machine_id}/recipient/pickup", tags=["Klienci"], response_model=SuccessResponse)
def recipient_pickup(machine_id: str, payload: RecipientPickupRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Odbior paczki na maszynie {machine_id} telefon: {payload.recipient_phone}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
        )

    occupied_lockers = db.query(Locker).filter(
        Locker.machine_id == machine_id,
        Locker.status == "OCCUPIED",
        Locker.package_number != None,
        Locker.pin_code != None,
    ).all()

    matched_locker = None
    matched_package = None

    for locker in occupied_lockers:
        package = db.query(Package).filter(
            Package.package_number == locker.package_number,
            Package.recipient_phone == payload.recipient_phone,
            Package.status == "AWAITING_RECIPIENT"
        ).first()

        if package and locker.pin_code == payload.pin_code:
            matched_locker = locker
            matched_package = package
            break

    if not matched_locker or not matched_package:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST, 
            detail="ERROR: Bledny numer telefon, zly Pin lub brak oczekujacej paczki"
        )

    try:
        matched_locker.status = "AVAILABLE"
        matched_locker.package_number = None
        matched_locker.pin_code = None

        matched_package.status = "RECEIVED"

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ERROR: Blad bazy danych podczas aktualizacji statusow"
        )

    print(f"Sukces! Otwieram skrytke {matched_locker.locker_id}")

    return {
        "success": True, 
        "message": "Otwieram skrytke",
        "locker_id": matched_locker.locker_id
        }
            
@app.post("/api/machines/{machine_id}/sender/create-package", tags=["Klienci"], response_model=SuccessResponse)
def seander_create_package(machine_id: str, payload: SenderCreateRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Nadanie paczki na maszynie {machine_id} do odbiorcy: {payload.recipient_phone}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
        )

    free_locker = db.query(Locker).filter(
        Locker.machine_id == machine_id,
        Locker.status == "AVAILABLE"
    ).first()

    if not free_locker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERROR: Brak wolnych skrytek w tej maszynie"
        )

    try:
        for _ in range(5):
            package_number = random.randint(10000000, 999999999)
            existing_package = db.query(Package).filter(Package.package_number == package_number).first()
            if not existing_package:
                break
        else:
            package_number = random.randint(10000000, 999999999)

        new_package = Package(
            package_number = package_number,
            recipient_phone = payload.recipient_phone,
            status = "AWAITING_COURIER"
        )
        db.add(new_package)

        free_locker.status = "OCCUPIED"
        free_locker.package_number = package_number

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ERROR: Blad bazy danych podczas aktualizacji statusow"
        )

    print(f"Sukces! Paczka {package_number} przypisana do skrytki {free_locker.locker_id}. Otwieram skrytke")

    return {
        "success": True, 
        "message": "Paczka zarejestrowana, otwieram skrytke",
        "package_number": package_number,
        "locker_id": free_locker.locker_id
        }

# Kurier
@app.post("/api/auth/courier-login", tags=["Kurier"], response_model=CourierLoginResponse)
def courier_login(payload: CourierLoginRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Proba logowania kuriera {payload.courier_login}")

    courier = db.query(Courier).filter(Courier.courier_login == payload.courier_login).first()

    if not courier or not verify_password(payload.password, courier.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ERROR: Bledny login lub haslo"
        )

    session_tocken = generate_session_tocken()
    courier.tocken_session = session_tocken
    db.commit()

    return {
        "authenticated": True, 
        "tocken_session": session_tocken,
        "message": "Zalogowano pomyslnie"
        }

@app.post("/api/auth/courier-logout", tags=["Kurier"], response_model=SuccessResponse)
def courier_logout(x_auth_tocken: str = Header(None, alias="x-auth-tocken"), db: Session = Depends(get_db), api_key: str = Depends(verify_rasp_api_key)):
    if not x_auth_tocken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RROR: Brak naglowka autoryzacyjnego"
        )

    courier = db.query(Courier).filter(Courier.tocken_session == x_auth_tocken).first()

    if not courier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ERROR: Nieprawidlowy lub wygasly tocken sesji"
        )

    courier.tocken_session = None
    db.commit()
    
    print(f"Wylogowanie kuriera: {courier.courier_login}")
    return {"success": True, "message":"Wylogowano"}

@app.get("/api/courier/pickups", tags=["Kurier"], response_model=CourierPickupsResponse)
def get_courier_pickups(x_auth_tocken: str = Header(None), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Kurier pobiera liste paczek do wyjecia Token: {x_auth_tocken}")
    return {"success": True, "lockers_to_open":["POX001", "POX002"], "message":"Otwieram skrytki"}

@app.post("/api/courier/deliver", tags=["Kurier"], response_model=SuccessResponse)
def courier_deliver(payload: CourierDeliverRequest, x_auth_tocken: str = Header(None), api_key: str = Depends(verify_rasp_api_key)):
    print(f"Kurier dorecza paczke nr: {payload.package_number}. Tocken: {x_auth_tocken}")
    return {"success": True, "message": "Paczka zarejestrowana, otwieram skrytke"}