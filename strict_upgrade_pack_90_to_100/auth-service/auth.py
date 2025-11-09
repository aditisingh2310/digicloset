from fastapi import FastAPI, HTTPException
import jwt, time

SECRET = "CHANGE_ME"
app = FastAPI()

@app.post("/login")
def login(user: str):
    return {"token": jwt.encode({"user": user, "exp": time.time()+3600}, SECRET, algorithm="HS256")}
