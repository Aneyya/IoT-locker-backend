import sys, os
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app.database_model import Courier, Package
from app.security import hash_password

def list_couriers(db: Session):
    couriers = db.query(Courier).all()
    print("\n---- Lista kurierow ----")
    if not couriers:
        print("Brak kurierow w bazie")
        return
    for c in couriers:
        print(f"Nazwa kuriera: {c.courier_login}, sesja wygasa (None -> brak aktywnej sesji): {c.token_expires_at}")
    print ("-" * 20)

def add_courier(db: Session):
    print("\n---- Dodawanie kuriera ----")
    login = input("Podaj login dla kuriera: ").strip()
    if not login:
        print("Login nie moze byc pusty")
        return

    existing = db.query(Courier).filter(Courier.courier_login == login).first()
    if existing:
        print("Blad: Kurier o takim loginie juz istnieje!")
        return

    password = input("Podaj haslo dla kuriera: ").strip()
    if len(password) < 12:
        print("Blad: Haslo musi miec co najmniej 12 znakow!")
        return

    password_hash = hash_password(password)
    new_courier = Courier(courier_login = login, password_hash = password_hash)

    try:
        db.add(new_courier)
        db.commit
        print(f"Sukces! Dodano kuriera: {login}")

    except Exception as e:
        db.rollback()
        print(f"Blad bazy danych: {e}")

def delete_courier(db: Session):
    print("\n---- Usuwanie kuriera ----")
    login = input("Podaj login kuriera do usuniecia: ").strip()

    courier = db.query(Courier).filter(Courier.courier_login == login)
    if not courier:
        print("Blad: Taki kurier nie istnieje")
        return

    active_packages = db.query(Package).filter(
        Package.courier_login == login,
    ).all()
    if active_packages:
        print(f"Blad: Nie mozna usunac kuriera {login}, poniewaz ma przypisane paczki w bazie!")
        return

    confirm = input(f"Czy na pewno chcesz usunac tego kuriera {login}? (t/n): ")
    if confirm.lower() == 't':
        try:
            db.delete(courier)
            db.commit
            print(f"Usunieto kuriera: {login}")

        except Exception as e:
            db.rollback()
            print(f"Blad podczas usuwania: {e}")

    else:
        print("Anulowano")

def main_menu():
    db = SessionLocal()

    while True:
        print ("\n---- Panel administratora (kurierzy) ----")
        print ("1. Wyswietl kurierow")
        print ("2. Dodaj kuriera")
        print ("3. Usun kuriera")
        print ("4. Zakoncz")

        choice = input("wybierz opcje (1-4): ").strip()
        if choice == "1":
            list_couriers(db)
        elif choice == "2":
            add_courier(db)
        elif choice == "3":
            delete_courier(db)
        elif choice == "4":
            print("Zamykam skrypt")
            db.close()
            break
        else:
            print("Nieprawidlowy wybor! Sprobuj ponownie")

if __name__ == "__main__":
    main_menu()
