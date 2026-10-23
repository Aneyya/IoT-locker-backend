from fastapi import FastAPI
from app.database import engine, Base
from app.database_model import *

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iot Locker Backend",
    description="Backend do zarzadzania skrytkami pocztowymi"
)

@app.get("/")
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}