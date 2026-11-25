import secrets, logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.database_model import *
from app.schemas import *
from app.security import *

router = APIRouter()
logger = logging.getLogger(__name__)

# Klient
@router.post("/api/machines/{machine_id}/recipient/pickup", tags=["Klienci"], response_model=ClientPickupResponse)
def recipient_pickup(
    machine_id: str, 
    payload: RecipientPickupRequest,
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db)):

    logger.info(f"Proba odbioru paczki na maszynie {machine_id} telefon: {payload.recipient_phone}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        logger.warning(f"Odbior paczki odrzucony: maszyna {machine_id} nie istnieje")
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
        logger.warning(f"Nieudany odbior paczki na maszynie {machine_id}")
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST, 
            detail="ERROR: Bledny numer telefon, zly Pin lub brak oczekujacej paczki"
        )

    try:
        matched_locker.status = "AVAILABLE"
        matched_locker.package_number = None
        matched_locker.pin_code = None

        matched_package.status = "RECEIVED"
        matched_package.courier_login = None

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Blad bazy danych podczas odbioru paczki {matched_package.package_number} na maszynie {machine_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ERROR: Blad bazy danych podczas aktualizacji statusow"
        )

    logger.info(f"Odebrano paczke {matched_package.package_number}. Otwarto skrytke {matched_locker.locker_id} na maszynie {machine_id}")

    return {
        "success": True, 
        "message": "Otwieram skrytke",
        "locker_id": matched_locker.locker_id
    }
            
@router.post("/api/machines/{machine_id}/sender/create-package", tags=["Klienci"], response_model=ClientSenderResponse)
def sender_create_package(
    machine_id: str, 
    payload: SenderCreateRequest,
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db)):

    logger.info(f"Rozpoczecie nadania paczki na maszynie {machine_id} do maszyny docelowej {payload.target_machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        logger.warning(f"Nadanie odrzucone: maszyna nadawcza {machine_id} nie istnieje")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="ERROR: Maszyna o podanym ID nie istnieje"
        )

    target_machine = db.query(Machine).filter(
        Machine.machine_id == payload.target_machine_id
    ).first()

    if not target_machine:
        logger.warning(f"Nadanie odrzucone: maszyna docelowa {payload.target_machine_id} nie istnieje")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maszyna docelowa {payload.target_machine_id} nie istnieje"
        )

    free_locker = db.query(Locker).filter(
        Locker.machine_id == machine_id,
        Locker.status == "AVAILABLE"
    ).with_for_update().first()

    if not free_locker:
        logger.warning(f"Brak wolnych skrytek w maszynie {machine_id} podczas nadania paczki")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERROR: Brak wolnych skrytek w tej maszynie"
        )

    try:
        for _ in range(5):
            package_number = secrets.randbelow(900000000) + 100000000
            existing_package = db.query(Package).filter(Package.package_number == package_number).first()
            if not existing_package:
                break
        else:
            logger.error(f"Nie udalo sie wygenerowac unikalnego numeru paczki")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Nie udalo sie wygenerowac unikalnego numeru paczki"
            )

        new_package = Package(
            package_number = package_number,
            recipient_phone = payload.recipient_phone,
            target_machine_id = payload.target_machine_id,
            status = "AWAITING_COURIER"
        )
        db.add(new_package)

        free_locker.status = "OCCUPIED"
        free_locker.package_number = package_number

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Blad bazy danych podczas rejestracji paczki na maszynie {machine_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ERROR: Blad bazy danych podczas aktualizacji statusow"
        )

    logger.info(f"Nadano paczke {package_number} na maszynie {machine_id}, skrytka {free_locker.locker_id} przypisana do skrytki {free_locker.locker_id}."
                f" -> cel: {payload.target_machine_id}, odbiorca:{payload.recipient_phone}")

    return {
        "success": True, 
        "message": "Paczka zarejestrowana, otwieram skrytke",
        "package_number": package_number,
        "locker_id": free_locker.locker_id
        }

