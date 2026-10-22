from fastapi import FastAPI

app = FastAPI(
    title="Iot Locker Backend",
    description="Backend do zarzadzania skrytkami pocztowymi"
)

@app.get("/")
def read_root():
    return{"message":"Witaj! Serwer FastAPI dziala poprawnie"}
