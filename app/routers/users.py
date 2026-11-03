import random
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.database_model import *
from app.schemas import *
from app.security import *

router = APIRouter()

# Klient
@router.post("/api/machines/{machine_id}/recipient/pickup", tags=["Klienci"], response_model=ClientPickupResponse)
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
            
@router.post("/api/machines/{machine_id}/sender/create-package", tags=["Klienci"], response_model=ClientSenderResponse)
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
@router.post("/api/auth/courier-login", tags=["Kurier"], response_model=CourierLoginResponse)
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

@router.post("/api/auth/courier-logout", tags=["Kurier"], response_model=SuccessResponse)
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

@router.get("/api/machines/{machine_id}/courier/pickups", tags=["Kurier"], response_model=CourierPickupsResponse)
def get_courier_pickups(machine_id: str, db: Session = Depends(get_db), x_auth_tocken: str = Header(None, alias="x-auth-tocken"), api_key: str = Depends(verify_rasp_api_key)):
    courier = db.query(Courier).filter(Courier.tocken_session == x_auth_tocken).first()
    if not courier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak aktywnej sesji kuriera. Zaloguj sie ponownie"
        )

    packages_to_pickup = db.query(Package).join(Locker).filter(
        Locker.machine_id == machine_id,
        Package.status == "AWAITING_COURIER"
    ).all()

    if not packages_to_pickup:
        return{
            "success": True,
            "message": "Brak paczek do odebrania w tej maszynie",
            "lockers_to_open": [],
        }
    
    lockers_to_open = []

    for package in packages_to_pickup:
        package.status = "ON_THE_WAY"
        package.courier_login = courier.courier_login

        locker = db.query(Locker).filter(
            Locker.machine_id == machine_id,
            Locker.package_number == package.package_number
        ).first()

        if locker:
            lockers_to_open.append(str(locker.locker_id))
            locker.status = "AVAILABLE"
            locker.package_number = None

    db.commit()
    
    return {
        "success": True,  
        "message":"Otwieram skrytki",
        "lockers_to_open": lockers_to_open
    }

@router.post("/api/machines/{machine_id}/courier/deliver", tags=["Kurier"], response_model=CourierDeliveryResponse)
def courier_deliver(machine_id: str, payload: CourierDeliverRequest, db: Session = Depends(get_db), x_auth_tocken: str = Header(None), api_key: str = Depends(verify_rasp_api_key)):
    courier = db.query(Courier).filter(Courier.tocken_session == x_auth_tocken).first()
    if not courier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak aktywnej sesji kuriera. Zaloguj sie ponownie"
        )

    package = db.query(Package).filter(
        Package.package_number == payload.package_number,
        Package.courier_login == courier.courier_login
    ).first()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paczka nie istnieje lub jest przypisana do innego kuriera"
        )

    free_locker = db.query(Locker).filter(
        Locker.machine_id == machine_id,
        Locker.status == "AVAILABLE"
    ).first()

    if not free_locker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak wolnych skrytek w tej maszynie"
        )

    pin_code = str(random.randint(100000, 999999))

    print(f"\n [PROJEKT - POWIADOMIENIE SMS]")
    print(f"Do: {package.recipient_phone} | Paczka nr: {package.package_number}")
    print(f"Wygenerowany kod PIN do odbioru: {pin_code}\n")

    # KOMENTARZ DO PROJEKTU 
    # W KOMERCYJNEJ WERSJI SYSTEMU W TYM MIEJSCU NASTAPILOBY WYWOLANIE API ZEWNETRZNEGO OPERATORA BRAMKI SMS

    package.status = "AWAITING_RECIPIENT"
    package.courier_login = None

    free_locker.status = "OCCUPIED"
    free_locker.package_number = package.package_number
    free_locker.pin_code = pin_code

    db.commit()

    return {
        "success": True, 
        "message": "Paczka zarejestrowana, otwieram skrytke", 
        "locker_id": free_locker.locker_id
    }