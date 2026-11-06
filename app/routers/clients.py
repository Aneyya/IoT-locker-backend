import random
from fastapi import APIRouter, Depends, HTTPException, status
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
    hashed_pin_code = hash_secret(str(payload.pin_code))

    for locker in occupied_lockers:
        package = db.query(Package).filter(
            Package.package_number == locker.package_number,
            Package.recipient_phone == payload.recipient_phone,
            Package.status == "AWAITING_RECIPIENT"
        ).first()

        if package and secrets.compare_digest(locker.pin_code, hashed_pin_code):
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

