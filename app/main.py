from fastapi import FastAPI
from app.routers import clients, system, couriers
from app.database import engine, Base

# Inicjalizacja bazy
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iot Locker Backend",
    description="Backend do zarzadzania skrytkami pocztowymi"
)

#
# ENDPOINTY
#
@app.get("/", tags=["System"])
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}

app.include_router(system.router)
app.include_router(clients.router)
app.include_router(couriers.router)
