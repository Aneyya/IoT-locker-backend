import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_model import Technician, ServiceLog

def list_technicians(db: Session):
    techs = db.query(Technician).all()
    print("\n--- Lista serwisantow ---")
    if not techs:
        print("Brak serwisantów w bazie")
        return
    for t in techs:
        print(f"ID: {t.tech_id} | Imie i nazwisko: {t.full_name} | Tel: {t.phone_number}")
    print("-" * 35)

def add_technician(db: Session):
    print("\n--- Dodawanie serwisanta ---")
    full_name = input("Podaj imie i nazwisko serwisanta: ").strip()
    if not full_name:
        print("Blad: Imie i nazwisko nie moze byc puste!")
        return

    phone = input("Podaj 9-cyfrowy numer telefonu: ").strip()
    if not phone.isdigit() or len(phone) != 9:
        print("Blad: Numer telefonu musi skladac sie dokladnie z 9 cyfr!")
        return

    existing = db.query(Technician).filter(Technician.full_name == full_name, Technician.phone_number == phone).first()
    if existing:
        print("Blad: Serwisant z tym numerem tel oraz o takim imieniu i nazwisku juz istnieje!")
        return

    new_tech = Technician(
        full_name=full_name,
        phone_number=phone
    )
    
    try:
        db.add(new_tech)
        db.commit()
        print(f"Sukces! Dodano serwisanta: {full_name}")
    except Exception as e:
        db.rollback()
        print(f"Blad bazy danych: {e}")

def delete_technician(db: Session):
    print("\n--- Usuwanie serwisanta ---")
    try:
        tech_id = int(input("Podaj ID serwisanta do usuniecia: ").strip())
    except ValueError:
        print("Blad: ID musi byc liczba naturalna!")
        return

    tech = db.query(Technician).filter(Technician.tech_id == tech_id).first()
    if not tech:
        print("Blad: Taki serwisant nie istnieje!")
        return

    logs_count = db.query(ServiceLog).filter(ServiceLog.tech_id == tech_id).count()
    if logs_count > 0:
        print(f"OSTRZEZENIE: Ten serwisant ma powiazane wpisy w historii logów serwisowych ({logs_count} logów).")
        print("Usuniecie go moze naruszyc spojnosc historycznych logow")
        print("Anulowano")
        return

    confirm = input(f"Czy na pewno chcesz usunac serwisanta {tech.full_name}? (t/n): ")
    if confirm.lower() == 't':
        try:
            db.delete(tech)
            db.commit()
            print(f"Usunieto serwisanta: {tech.full_name}")
        except Exception as e:
            db.rollback()
            print(f"Blad podczas usuwania: {e}")
    else:
        print("Anulowano")

def main_menu():
    db = SessionLocal()
    while True:
        print("\n---- Panel administartora (serwisanci) ----")
        print("1. Wywietl serwisantow")
        print("2. Dodaj serwisanta")
        print("3. Usun serwisanta")
        print("4. Wyjcie")
        
        choice = input("Wybierz opcje (1-4): ").strip()
        
        if choice == '1':
            list_technicians(db)
        elif choice == '2':
            add_technician(db)
        elif choice == '3':
            delete_technician(db)
        elif choice == '4':
            print("Zamykanie skryptu")
            db.close()
            break
        else:
            print("Nieprawidlowy wybór. Spróbuj ponownie.")

if __name__ == "__main__":
    main_menu()