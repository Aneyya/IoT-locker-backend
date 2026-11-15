import logging
from fastapi import FastAPI
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from app.routers import clients, system, couriers
from app.database import engine, Base

# Inicjalizacja bazy
Base.metadata.create_all(bind=engine)
logger.info("Zainicjalizowano polaczenie z baza danych oraz tabele")

app = FastAPI(
    title="Iot Locker Backend",
    description="Backend do zarzadzania skrytkami pocztowymi"
)

#
# ENDPOINTY
#
@app.get("/", tags=["System"])
def read_root():
    logger.info("Sprawdzanie statusu serwera (healthcheck /)")
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}

app.include_router(system.router)
app.include_router(clients.router)
app.include_router(couriers.router)
