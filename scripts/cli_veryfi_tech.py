import os
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

API_URL = "http://127.0.0.1:8000"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

def main():
    print("\n" + "-"*50)
    print("Zdalna weryfikacja serwisanta")
    print("-"*50)
    
    if not ADMIN_API_KEY:
        print("Blad: Brak ADMIN_API_KEY w pliku .env!")
        return

    headers = {"x-api-key": ADMIN_API_KEY}

    machine_id = input("Podaj ID maszyny (zglaszane przez technika): ").strip()
    full_name = input("Podaj imie i nazwisko technika: ").strip()

    print("\n[Trwa weryfikacja w systemie...]")
    verify_url = f"{API_URL}/api/auth/technician-verify"
    payload = {
        "machine_id": machine_id,
        "full_name": full_name
    }
    
    try:
        response = requests.post(verify_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\nSUKCES! Dane zautoryzowane.")
            print(f"Komunikat z serwera: {data.get('message')}")
            print(f"Skrytka serwisowa ({data.get('service_locker')}) zostala otwarta")
            
            print("\n[Prace serwisowe trwaja. Technik wykonuje zadanie...]")
            while True:
                command = input("Wpisz 'exit' aby zakonczyc prace i zamknac skrytke: ").strip().lower()
                if command == 'exit':
                    break
                else:
                    print("Nieznana komenda. Wpisz 'exit' kiedy technik zakonczy prace.")
            
            print("\n[Wysylanie sygnalu zamykania skrytki...]")
            close_url = f"{API_URL}/api/machines/{machine_id}/service-close"
            close_resp = requests.post(close_url, headers=headers)
            
            if close_resp.status_code == 200:
                print("Sukces! Skrytka zostala bezpiecznie zamknieta w bazie danych.")
                print("Zakonczenie procedury serwisowej.")
            else:
                print(f"Blad przy zamykaniu: kod {close_resp.status_code}")
                print(close_resp.text)

        elif response.status_code == 404:
            print("\nBlad weryfikacji! Zgloszone dane sa niepoprawne.")
            print(f"Szczegoly: {response.json().get('detail')}")
        elif response.status_code == 403:
            print("\nBlad: Odmowa dostepu. Sprawdz swoj ADMIN_API_KEY!")
        else:
            print(f"\nNieoczekiwany blad serwera: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nNie mozna polaczyc sie z API!")
        print("Upewnij sie, ze serwer uvicorn (FastAPI) jest uruchomiony")

if __name__ == "__main__":
    main()