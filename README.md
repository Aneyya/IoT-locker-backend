# IoT Locker System - Backend API

Serwerowy moduł backendowy prototypu skrytek pocztowych. Aplikacja udostępnia interfejs REST API zbudowany w oparciu o framework FastAPI, odpowiedzialny za zarządzanie stanem skrytek, autoryzację kurierów i serwisantów oraz obsługę procesu wydawania i nadawania paczek. System współpracuje z klientem fizycznym, Raspberry Pi z kontrolerem diod RGB, a całość ruchu jest zabezpieczona i pośredniczona przez serwer Nginx oraz tunel Ngrok.

---

## Stos technologiczny

- **Język:** Python 3.14.4
- **Framework API:** FastAPI
- **Serwer ASGI:** Uvicorn
- **Reverse Proxy / Serwer WWW:** Nginx (wer. 1.28.3)
- **Bezpieczeństwo / Kryptografia:** Passlib (Argon2), wbudowane biblioteki `hashlib` (SHA-256) i `secrets`
- **ORM:** SQLAlchemy
- **Baza danych:** SQLite
- **Walidacja danych:** Pydantic
- **Dokumentacja API:** Swagger UI (wbudowane w FastAPI)

---

## Struktura projektu

```text
IoT-Locker-backend/
├── app/
│   ├── routers/                  
│   │   ├── clients.py            
│   │   ├── couriers.py           
│   │   └── system.py             
│   ├── database.py               
│   ├── database_model.py         
│   ├── main.py                   
│   ├── schemas.py                
│   └── security.py               
├── diagrams/
│   └── database_schema.png       
├── nginx/
│   └── lockers.conf              
├── scripts/
│   ├── cli_couriers.py           
│   ├── cli_machines.py           
│   ├── cli_technicians.py        
│   ├── cli_veryfi_tech.py        
│   └── seed.py                   
├── .gitignore                    
├── README.md                     
└── requirements.txt              
```

### Opis plików i katalogów:

- **app/** – Główny katalog logiki aplikacji serwerowej:
  - **routers/** – Katalog zawierający podzielone moduły endpointów API (`clients.py`, `couriers.py`, `system.py`).
  - **main.py** – Punkt startowy aplikacji FastAPI integrujący routery.
  - **database.py** – Konfiguracja połączenia z bazą danych SQLite oraz zarządzanie sesjami SQLAlchemy.
  - **database_model.py** – Definicje struktur tabel i relacji bazodanowych (modele ORM).
  - **schemas.py** – Schematy Pydantic służące do ścisłej walidacji danych wejściowych (np. weryfikacja regex dla numerów telefonów) i struktury odpowiedzi JSON.
  - **security.py** – Moduł obsługujący autoryzację (`x-api-key`), weryfikację tokenów oraz kryptografię (haszowanie Argon2 dla haseł, SHA-256 dla PIN-ów).
- **nginx/** – Konfiguracja infrastruktury:
  - **lockers.conf** – Plik konfiguracyjny serwera Nginx pełniącego rolę reverse proxy, zawierający mechanizmy bezpieczeństwa np. Rate Limiting oraz rygorystyczne nagłówki bezpieczeństwa.
- **scripts/** – Skrypty administracyjne i pomocnicze CLI:
  - **cli_couriers.py**, **cli_machines.py**, **cli_technicians.py**, **cli_veryfi_tech.py** – Narzędzia dla administratora do zarządzania bazą danych bezpośrednio z poziomu wiersza poleceń.
  - **seed.py** – Skrypt automatycznie czyszczący i zasilający bazę danych wstępnymi danymi testowymi.
- **requirements.txt** – Lista wszystkich zależności i pakietów Pythona wymaganych do uruchomienia aplikacji.

---

## Model bazy danych

![Schemat bazy danych](diagrams/database_schema.png)

---

## Uruchomienie projektu lokalnie

### 1. Wymagania wstępne
Upewnij się, że masz zainstalowanego Pythona oraz serwer Nginx.

### 2. Klonowanie repozytorium i konfiguracja środowiska
```bash
# Utworzenie i aktywacja wirtualnego środowiska
python3 -m venv venv
source venv/bin/activate  # Dla systemu Linux
```

### 3. Instalacja wymaganych pakietów
Dzięki plikowi `requirements.txt` instalacja jest zautomatyzowana:
```bash
pip install -r requirements.txt
```

### 4. Konfiguracja zmiennych środowiskowych (.env)
W głównym katalogu aplikacji utwórz plik `.env` i zdefiniuj w nim klucze zabezpieczające API:
```env
ADMIN_API_KEY=twoj_tajny_klucz_administratora
RASP_API_KEY=twoj_tajny_klucz_malinki
```

### 5. Zasilenie bazy danych danymi testowymi (seed)
Przed pierwszym uruchomieniem serwera wygeneruj schemat i testowe dane dla maszyny KR001:
```bash
python -m scripts.seed
```
Skrypt utworzy maszynę KR001, 5 skrytek klienckich (KR001_POX1–POX5), skrytkę serwisową KR001_SRV1 oraz testowe paczki i dostępy.

### 6. Uruchomienie serwera API (Uvicorn)
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Serwer backendu wystartuje pod adresem `http://127.0.0.1:8000`.

### 7. Konfiguracja Nginx (Reverse Proxy)
Aby włączyć zabezpieczenia (limitowanie zapytań, ukrycie dokumentacji API), skopiuj plik konfiguracyjny do katalogu Nginx i zrestartuj usługę:
```bash
sudo cp nginx/lockers.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/lockers.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
Od tego momentu cały ruch powinien być kierowany na port `80` (Nginx), który przekazuje zweryfikowane zapytania do portu `8000` (Uvicorn). Zewnętrzny dostęp (np. z Raspberry Pi lub PowerShell) realizowany jest za pomocą bezpiecznego tunelu Ngrok podpiętego pod Nginxa.