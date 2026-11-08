from datetime import datetime
from app.database import *
from app.database_model import *
from app.security import *

def seed_database():
    print("Resetowanie tabel w bazie danych")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("Uzupełnienie bazy danymi testowymi")

        machine = Machine(
            machine_id="KR001",
            address="Krakow, ul. Warszawska 24",
            service_locker_id="SRV001",
            is_service_open=False
        )
        db.add(machine)

        tech = Technician(
            full_name="Jan Nowak",
            phone_number="500600700"
        )
        db.add(tech)

        secure_pass = hash_password("test!test")
        courier = Courier(
            courier_login="test",
            password_hash=secure_pass,
            token_session=None
        )
        db.add(courier)

        pkg1 = Package(
            package_number=111111111,
            recipient_phone="600111222",
            status="AWAITING_RECIPIENT",
            courier_login="test",
            created_at=datetime.now()
        )
        pkg2 = Package(
            package_number=222222222,
            recipient_phone="600333444",
            status="AWAITING_COURIER",
            courier_login=None,
            created_at=datetime.now()
        )
        db.add_all([pkg1, pkg2])

        lockers = [
            Locker(locker_id="POX001", machine_id="KR001", status="AVAILABLE", package_number=None, pin_code=None),
            Locker(locker_id="POX002", machine_id="KR001", status="OCCUPIED", package_number=111111, pin_code=hash_secret("123456")),
            Locker(locker_id="POX003", machine_id="KR001", status="AVAILABLE", package_number=None, pin_code=None),
            Locker(locker_id="POX004", machine_id="KR001", status="OCCUPIED", package_number=222222, pin_code=None),
            Locker(locker_id="POX005", machine_id="KR001", status="AVAILABLE", package_number=None, pin_code=None),
        ]
        db.add_all(lockers)

        db.commit()

        print("\nBaza danych została pomyślnie zasilona!")

    except Exception as e:
        db.rollback()
        print(f"Blad podczas tworzenia danych {e}")

    finally:
        db.close()

if __name__=='__main__':
    seed_database()
