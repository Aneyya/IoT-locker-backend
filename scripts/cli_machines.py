import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_model import Machine, Locker, Package, ServiceLog

def list_machines(db: Session):
    machines = db.query(Machine).all()
    print("\n---- Lista maszyn ----")
    if not machines:
        print("Brak maszyn w bazie")
        return
    for m in machines:
        lockers_count = db.query(Locker).filter(Locker.machine_id == m.machine_id).count()
        print(f"ID: {m.machine_id} | Adres: {m.address} | Skrytka serwisowa: {m.service_locker_id} | Liczba skrytek: {lockers_count}")
    print("-" * 50)

def add_machine_with_lockers(db: Session):
    print("\n---- Dodawanie nowej maszyny i skrytek ----")
    machine_id = input("Podaj ID maszyny (np. KR002): ").strip()
    if not machine_id:
        print("Blad: ID maszyny nie moze byc puste!")
        return

    existing = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if existing:
        print("Blad: Maszyna o takim ID juz istnieje!")
        return

    address = input("Podaj adres maszyny: ").strip()
    service_locker_id = input("Podaj ID skrytki serwisowej (np. S1): ").strip()

    try:
        lockers_count = int(input("Ile skrytek ma posiadac ta maszyna? (np. 10): ").strip())
        if lockers_count <= 0:
            raise ValueError()
    except ValueError:
        print("Blad: Liczba skrytek musi byc dodatnia liczba calkowita!")
        return

    try:
        new_machine = Machine(
            machine_id=machine_id,
            address=address,
            service_locker_id=service_locker_id,
            is_service_open=False
        )
        db.add(new_machine)

        for i in range(1, lockers_count + 1):
            locker = Locker(
                locker_id=f"{machine_id}_POX{i}",
                machine_id=machine_id,
                status="AVAILABLE",
                package_number=None,
                pin_code=None
            )
            db.add(locker)

        db.commit()
        print(f"Sukces! Dodano maszyne {machine_id} wraz z {lockers_count} skrytkami.")
    except Exception as e:
        db.rollback()
        print(f"Blad bazy danych podczas dodawania maszyny: {e}")

def delete_machine(db: Session):
    print("\n---- Usuwanie maszyny ----")
    machine_id = input("Podaj ID maszyny do usuniecia: ").strip()
    
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        print("Blad: Taka maszyna nie istnieje.")
        return

    active_packages_in_machine = db.query(Package).join(
        Locker, Locker.package_number == Package.package_number
    ).filter(
        Locker.machine_id == machine_id,
        Package.status.in_(["AWAITING_RECIPIENT", "AWAITING_COURIER"])
    ).count()

    if active_packages_in_machine > 0:
        print(f"Blad: Nie mozna usunac maszyny {machine_id}!")
        print(f"W jej skrytkach znajduje sie {active_packages_in_machine} aktywnych paczek.")
        return

    confirm = input(f"Usuniecie maszyny usunie rowniez powiazane z nia skrytki i logi. Czy na pewno chcesz usunac maszyne? (t/n): ")
    if confirm.lower() == 't':
        try:
            db.query(ServiceLog).filter(ServiceLog.machine_id == machine_id).delete()
            db.query(Locker).filter(Locker.machine_id == machine_id).delete()
            db.delete(machine)
            db.commit()
            print(f"Usunieto maszyne {machine_id}, jej skrytki oraz powiazane logi")
        except Exception as e:
            db.rollback()
            print(f"Blad podczas usuwania: {e}")
    else:
        print("Anulowano.")

def main_menu():
    db = SessionLocal()
    while True:
        print("\n---- Panel administratora (maszyny i skrytki) ----")
        print("1. Wyswietl maszyny i liczbe skrytek")
        print("2. Dodaj nowa maszyne")
        print("3. Usun maszyne")
        print("4. Wyjscie")
        
        choice = input("Wybierz opcje (1-4): ").strip()
        
        if choice == '1':
            list_machines(db)
        elif choice == '2':
            add_machine_with_lockers(db)
        elif choice == '3':
            delete_machine(db)
        elif choice == '4':
            print("Zamykanie skryptu.")
            db.close()
            break
        else:
            print("Nieprawidlowy wybor. Sprobuj ponownie.")

if __name__ == "__main__":
    main_menu()