from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.database_model import *
from app.schemas import *
from app.security import *

router = APIRouter()
sec_auth_token = HTTPBearer()

def get_current_courier(
    credentials: HTTPAuthorizationCredentials = Depends(sec_auth_token), 
    db: Session = Depends(get_db)):

    x_auth_token = credentials.credentials
            
    hashed_auth_token = hash_secret(x_auth_token)
    courier = db.query(Courier).filter(Courier.token_session == hashed_auth_token).first()
    
    if not courier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak aktywnej sesji kuriera. Zaloguj sie ponownie"
        )

    if not courier.token_expires_at or courier.token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        try:
            courier.token_session = None
            courier.token_expires_at = None
            db.commit()

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Krytyczny blad bazy danych podczas zapisu"
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak aktywnej sesji kuriera. Zaloguj sie ponownie"
        )

    return courier

# Kurier
@router.post("/api/auth/courier-login", tags=["Kurier"], response_model=CourierLoginResponse)
def courier_login(
    payload: CourierLoginRequest, 
    db: Session = Depends(get_db), 
    api_key: str = Depends(verify_rasp_api_key)):

    print(f"Proba logowania kuriera {payload.courier_login}")

    courier = db.query(Courier).filter(Courier.courier_login == payload.courier_login).first()

    if not courier or not verify_password(payload.password, courier.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ERROR: Bledny login lub haslo"
        )

    session_token, session_token_hash = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    try: 
        courier.token_session = session_token_hash
        courier.token_expires_at = expires_at
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )   

    return {
        "authenticated": True, 
        "token_session": session_token,
        "message": "Zalogowano pomyslnie"
        }

@router.post("/api/auth/courier-logout", tags=["Kurier"], response_model=SuccessResponse)
def courier_logout(
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db), 
    courier: Courier = Depends(get_current_courier)):

    try:
        courier.token_session = None
        courier.token_expires_at = None
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )   
    
    print(f"Wylogowanie kuriera: {courier.courier_login}")
    return {"success": True, "message":"Wylogowano"}

@router.get("/api/machines/{machine_id}/courier/pickups", tags=["Kurier"], response_model=CourierPickupsResponse)
def get_courier_pickups(
    machine_id: str,
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db), 
    courier: Courier = Depends(get_current_courier)):

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
        )

    packages_to_pickup = db.query(Package).join(
        Locker, Locker.package_number == Package.package_number
    ).filter(
        Locker.machine_id == machine_id,
        Package.status == "AWAITING_COURIER"
    ).all()

    if not packages_to_pickup:
        return{
            "success": True,
            "message": "Brak paczek do odebrania w tej maszynie",
            "lockers_to_open": [],
        }

    package_numbers = [p.package_number for p in packages_to_pickup]
    lockers = db.query(Locker).filter(Locker.machine_id == machine_id, Locker.package_number.in_(package_numbers)).all()
    
    return {
        "success": True,  
        "message":"Lista skrytek do odbioru",
        "lockers_to_open": [str(l.locker_id) for l in lockers]
    }

@router.post("/api/machines/{machine_id}/courier/confirm-pickups", tags=["Kurier"], response_model=CourierPickupsResponse)
def confirm_courier_pickups(
    machine_id: str, 
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db), 
    courier: Courier = Depends(get_current_courier)):

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
        )

    packages_to_pickup = db.query(Package).join(
        Locker, Locker.package_number == Package.package_number
    ).filter(
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

    try:
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

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )

    return {
        "success": True,  
        "message":"Odbior zatwierdzony, otwieram skrytki",
        "lockers_to_open": lockers_to_open
    }

@router.post("/api/machines/{machine_id}/courier/deliver", tags=["Kurier"], response_model=CourierDeliveryResponse)
def courier_deliver(
    machine_id: str, 
    payload: CourierDeliverRequest,
    api_key: str = Depends(verify_rasp_api_key), 
    db: Session = Depends(get_db), 
    courier: Courier = Depends(get_current_courier)):

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
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
    
    if package.status != "ON_THE_WAY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ta paczka nie ma statusu 'W drodze'. Nie mozna jej dostarczyc"
        )

    free_locker = db.query(Locker).filter(
        Locker.machine_id == machine_id,
        Locker.status == "AVAILABLE"
    ).with_for_update().first()

    if not free_locker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak wolnych skrytek w tej maszynie"
        )

    pin_code, pin_code_hash = generate_pin_code()

    try:
        package.status = "AWAITING_RECIPIENT"
        package.courier_login = None

        free_locker.status = "OCCUPIED"
        free_locker.package_number = package.package_number
        free_locker.pin_code = pin_code_hash

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )

    print(f"\n [PROJEKT - POWIADOMIENIE SMS]")
    print(f"Do: {package.recipient_phone} | Paczka nr: {package.package_number}")
    print(f"Wygenerowany kod PIN do odbioru: {pin_code}\n")
    print(f"Adres skrytki pocztowej: {machine.address}\n")

    # KOMENTARZ DO PROJEKTU 
    # W KOMERCYJNEJ WERSJI SYSTEMU W TYM MIEJSCU NASTAPILOBY WYWOLANIE API ZEWNETRZNEGO OPERATORA BRAMKI SMS

    return {
        "success": True, 
        "message": "Paczka zarejestrowana, otwieram skrytke", 
        "locker_id": free_locker.locker_id
    }

