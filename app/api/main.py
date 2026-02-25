from fastapi import FastAPI
from app.db.init_db import init_db

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()
    return {"message": "Database initialized"}

@app.get("/users")
def users():
    return {"message": "hello world"}