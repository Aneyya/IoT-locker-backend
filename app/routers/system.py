import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.database_model import *
from app.schemas import *
from app.security import *

router = APIRouter()
logger = logging.getLogger(__name__)

# System
@router.get("/api/machines/{machine_id}/lockers", tags=["Maszyna IoT"], response_model=MachineStatusResponse)
def get_machine_lockers(
    machine_id: str,
    api_key: str = Depends(verify_rasp_api_key),
    db: Session = Depends(get_db)):

    logger.info(f"Pobieranie stanu skrytek dla maszyny {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        logger.warning(f"Nie znaleziono maszyny {machine_id} podczas pobierania skrytek")
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

# Admin
@router.post("/api/auth/technician-verify", tags=["Admin"], response_model=TechnicianVerifyResponse)
def verify_technician(
    payload: TechnicianVerifyRequest,
    api_key: str = Depends(verify_admin_api_key),
    db: Session = Depends(get_db)):

    logger.info(f"Proba weryfikacji technika {payload.full_name} na maszynie {payload.machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == payload.machine_id).first()
    if not machine:
        logger.warning(f"Przerwana weryfikacja technika: maszyna {payload.machine_id} nie istnieje")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Maszyna {payload.machine_id} nie istnieje w bazie"
        )

    print(f"Weryfikacja technika: {payload.full_name} na maszynie {payload.machine_id}")

    technician = db.query(Technician).filter(Technician.full_name == payload.full_name).first()
    if not technician:
        logger.warning(f"Nieudana weryfikacja technika {payload.full_name} na maszynie {payload.machine_id}")
        try: 
            fail_log = ServiceLog(
                machine_id=payload.machine_id,
                tech_id=None,
                action="REMOTE_VERIFY_FAILED"
            )
            db.add(fail_log)
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error("Blad bazy danych podczas zapisu logu nieudanej weryfikacji technika", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Krytyczny blad bazy danych podczas zapisu"
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Bledne dane technika"
        )

    try:
        succes_log = ServiceLog(
            machine_id=payload.machine_id,
            tech_id=technician.tech_id,
            action="REMOTE_VERIFY_SUCCESS"
        )
        db.add(succes_log)
        machine.is_service_open = True

        db.commit()
        logger.info(f"Odblokowano tryb serwisowy na maszynie {payload.machine_id} dla technika {technician.tech_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Blad bazy danych podczas odblokowywania trybu serwisowego na maszynie {payload.machine_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )

    return {
        "access_granted": True, 
        "message": "Tryb serwisowy odblokowany",
        "machine_id": payload.machine_id, 
        "service_locker": machine.service_locker_id
    }

#Endpoint czysto prototypowy przez brak czujników na skrytkach
@router.post("/api/machines/{machine_id}/service-close", tags=["Admin"], response_model=SuccessResponse)
def close_service_locker(
    machine_id: str,
    api_key: str = Depends(verify_admin_api_key),
    db: Session = Depends(get_db)):
    
    logger.info(f"Zamykanie skrytki serwisowej na maszynie {machine_id}")

    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        logger.warning(f"Nie znaleziono maszyny {machine_id} podczas zamykania skrytki serwisowej")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Maszyna {machine_id} nie istnieje w bazie"
        )
    try:
        success_close_log = ServiceLog(
            machine_id=machine_id,
            tech_id=None,
            action = "SERVICE_CLOSE_SUCCESS"
        )
        db.add(success_close_log)
        machine.is_service_open = False

        db.commit()
        logger.info(f"Skrytka serwisowa na maszynie {machine_id} zostala zamknieta")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Blad bazy danych podczas zamykania skrytki serwisowej na maszynie {machine_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Krytyczny blad bazy danych podczas zapisu"
        )
    
    return {"success": True, "message": "Zamykam skrytke"}
